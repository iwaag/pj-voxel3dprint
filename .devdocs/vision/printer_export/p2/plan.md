# printer_export Phase 2 実装計画 — 往復契約テストとドキュメント統合

親ロードマップ: `.devdocs/vision/printer_export/roadmap.md`（Phase 2）。
前フェーズ: `.devdocs/vision/printer_export/p1/plan.md`（完了、report1〜6）。

## この計画の位置づけ

Phase 1 で `export-print-slices`（material-label ボクセル → GrabCAD 向け
スライス PNG 群 + サイドカーマニフェスト）は完成し、デコード検証
（Pillow 読み戻し → パレット逆引き → sampler 出力配列と一致）までは
契約テストで固定済みである。

Phase 2 は roadmap 設計原則4「往復契約を正しさの基準にする」を実装する。

```text
export-print-slices → slices/ PNG
      ↓
convert-image-stack（levels はパレットから機械的に導出）
      ↓
プリンタ格子上の material-label ボクセル
      ＝ sampler が返すプリンタ格子配列と完全一致（契約テストで固定）
```

あわせて README_QUICK へ Use Case を追加し、`preview-slices` での目視確認
手順を方式ドキュメントへ記載して、このルートをユースケースとして公開する。

GrabCAD 実機ソフトでの受理確認は Phase 3 の責務であり、本フェーズには
含めない。往復で欠陥が見つかった場合、その修正は roadmap の方針どおり
**Phase 1 への fix** として扱う（本フェーズの report に記録する）。

## 前提調査（確認済み事実）

### Phase 1 の成果物と公開点

- `printer/sampler.py` の `build_sampling_plan()` / `sample_slice()` は
  PNG・IO 非依存の純関数で、往復契約の期待値（プリンタ格子配列）の
  共通参照点として設計済み（p1 plan「実施順序」節の狙いどおり）。
- exporter は書き出す palette index 配列を sampler 出力から直接引くため、
  「全スライスの sampler 出力を z に積んだ配列」がそのまま出力 PNG 群の
  意味内容である。flip / 軸交換は sampler 側で index 配列に織り込み済み。
- サイドカーマニフェスト（`<name>.printslices.json`）の `palette` は
  **背景（material_id 0）を含む** 全出現材料について
  `{ name, role, rgb }` を記録し、`printer` に `dpi_x` / `dpi_y` /
  `layer_thickness_m` を生値で記録する（`exporter.py::_build_manifest`）。
  → levels config の機械導出に必要な情報はマニフェストだけで揃う。
- 出力ディレクトリは PNG 群 + `<name>.printslices.json` のみ。
  `convert-image-stack` の入力 glob は `*.<format>` なので JSON サイドカーは
  干渉しない。連番は `index_start` からギャップなしで振られ、
  `_check_sequence_gaps()` を常に通過する。

### `.voxels.json` 契約の背景材料

`MaterialPalette` は「material_id 0 が唯一の `role: "background"` 材料」を
契約として強制する（`vdbmat/src/vdbmat/core/materials.py`）。exporter の
背景 = id 0 前提はこの契約に裏付けられており、往復側でも
「`background_rgb` → material_id 0」の逆引きは常に一意である。
また Phase 1 config は palette RGB の重複と背景色との衝突を拒否するため、
**RGB → material_id の逆写像は常に単射**である。

### `convert-image-stack` の現状（往復のギャップ）

- `ImageStackConfig.levels` は **gray 値（0..255）→ material** のみ
  （`image/stack.py::_parse_levels`）。
- PNG reader `read_png()` は 8-bit グレースケール（mode "L"）専用で、
  Phase 1 の出力（mode "P" インデックスパレット）を拒否する。
- 軸対応は rows=+Y、columns=+X 固定（provenance notes にも記録）。
  export の既定（`printer_x_axis="x"`）では columns = printer X なので
  そのまま整合する。
- `read_indexed_png()`（Phase 1 で追加）はテスト/デコード検証用ヘルパで、
  `MaterialLabelVolume` も provenance も作らない。往復契約の読み戻し側と
  しては契約が不足している。

### 破壊的変更方針との関係

levels スキーマへの `rgb` エントリ追加は**純追加**である。既存の gray
config・PGM 経路・既存契約テストは無変更で通る。roadmap の破壊的変更方針
（旧スキーマ読み込みを残さない等）を発動する変更は本フェーズに無い。

## 規模判定

単一フェーズの実装計画として扱える。変更は `image/`（color reader +
levels 拡張）、`printer/`（levels 導出ヘルパ1関数）、契約テスト1ファイル、
docs 3ファイル + README 2ファイルのみで、既存契約の変更を含まない。

## ゴール

1. `export-print-slices` の出力を `convert-image-stack` へ読み戻し、
   プリンタ格子上の材料配列と**完全一致**することが契約テストで固定される。
2. levels config はサイドカーマニフェストから機械的に導出される
   （手書きの対応表に依存しない）。
3. 異方性が効くケース（等方 100 µm ソース → 42.33×84.67×27 µm 格子）を
   含むリサンプリング感度が往復越しに検証される。
4. README_QUICK に新 Use Case「プリンタ向けスライス出力」が追加され、
   記載どおりに手動 CLI で primitive array → スライス PNG 群 → 読み戻し →
   `preview-slices` 目視まで通る。
5. `convert-image-stack` が色ラベルスタック（インデックスパレット /
   RGB PNG）を入力ルートとして正式に受理する（往復の副産物として
   独立に有用な入力拡張）。

## 決定事項

### 往復の読み戻しは `convert-image-stack` の色対応拡張で行う

p1 plan リスク節で保留した「levels の RGB 拡張 vs 往復専用グレースケール
読み戻し」の決定。**RGB 拡張を採る**。理由:

1. roadmap 設計原則4は「既存コマンドだけで組める最強の検証手段」を
   往復契約の価値としている。往復専用の読込ヘルパでは
   `convert-image-stack` の実経路（provenance、palette 構築、undeclared
   検出）を通らず、契約が「テスト専用コード同士の一致」に弱まる。
2. GrabCAD 向け出力は色 PNG であることが確定しており、グレースケール
   読み戻しは「出力とは別のエンコードを検証する」ことになり、往復の
   対称性（roadmap 図式の逆変換）が崩れる。
3. 色ラベルスタックの入力対応は、外部ツールで塗られたラベル画像の取り込み
   という独立のユースケースを持つ（純追加で既存契約を壊さない）。

### levels スキーマ拡張（`ImageStackConfig`）

- 各 levels エントリは `gray` **または** `rgb` のどちらか一方を持つ
  （両方・どちらも無しはエラー）。`rgb` は `[r, g, b]`（各 0..255 の整数）。
- **1つの config 内で gray エントリと rgb エントリの混在は禁止**
  （スタックはグレースケールか色かのどちらかであり、混在を許すと
  reader のモード判定が画素依存になる）。
- `rgb` の重複は gray の重複と同様にエラー。
- rgb モードは `format: "png"` のみ許可（PGM はグレースケール形式のため
  明示エラー）。
- `material_id` / `name` / `role` の検証・palette 構築・undeclared 検出の
  枠組みは既存のまま共通化する（エラー文言は gray/rgb で対称に）。

### 色 PNG reader（`image/png.py`）

- `read_png_rgb(path) -> NDArray[uint8]`（shape `(H, W, 3)`）を追加する。
- 受理モード: `"P"`（パレットテーブルを直接引いて RGB へ展開。
  `read_indexed_png()` と同じ getpalette 経由とし、Pillow の
  `convert("RGB")` には依存しない）と `"RGB"`。
- `"L"` / `"RGBA"` / 16-bit 等は明示エラー（silent 変換をしない。
  透過付き入力の受理は必要が確認されてから）。
- lazy import と actionable エラー（`image` extra 未導入時）は既存規約と
  同一。既存 `read_png()`（grayscale 専用）の契約は変えない。

### stack 側の色マッピング（`image/stack.py`）

- rgb モードでは `_read_slice` が `read_png_rgb()` を使い、
  `(H, W, 3)` を `r<<16 | g<<8 | b` の uint32 へパックして
  宣言済み色集合と照合・material_id へ変換する（lookup は
  `np.searchsorted` またはソート済みキー配列で決定論的に）。
- 未宣言色は gray と同様に「最初の出現位置（ファイル名・行・列・RGB 値）」
  つきの明示エラー。
- provenance の `notes` は色モードであることが分かる記述にする
  （rows=+Y, columns=+X の軸規約は共通）。config digest は canonical JSON
  機構にそのまま乗る（rgb フィールドが digest に効く）。

### levels 導出ヘルパ（`printer/roundtrip.py`）

`image_stack_config_from_print_manifest(manifest: Mapping, ...) ->
ImageStackConfig` を追加する。

- `palette`（背景 id 0 を含む）から levels（`rgb` / `material_id` /
  `name` / `role`）を機械導出する。
- `voxel_size_xyz_m` は **manifest の `dpi_x` / `dpi_y` /
  `layer_thickness_m` から sampler と同じ式（`0.0254 / dpi`）で再計算**
  する。`pitch_*_mm` の mm 値から戻さない（mm 変換の float 往復誤差で
  sampler のピッチと不一致になるのを避ける）。
- `format="png"` 固定。manifest の `format` / `format_version` 検証つき。
- 位置づけはライブラリ関数 + 契約テストの土台。CLI サブコマンド化は
  必要が確認されてから（Phase 4 候補）。docs には導出規則そのものを
  記載し、手書きでも同じ config が書けるようにする。

### 往復契約テストの一致基準

`convert_image_stack()` が返す `MaterialLabelVolume` について:

- `material_id` 配列 ＝ 全 z の `sample_slice()` 出力を積んだ配列
  （export が書いた内容の定義そのものなので、flip / 軸交換の全変種で
  この等式のまま成立する。変種側の期待値変換は不要）。
- `voxel_size_xyz_m` ＝ プリンタピッチ（`pitch_x, pitch_y, pitch_z`）。
- palette の material_id / name / role がソース入力の出現材料集合
  （+ 背景）と一致。

## 対象ファイル

### 新規

- `vdbmat-utils/src/vdbmat_utils/printer/roundtrip.py`
- `vdbmat-utils/tests/unit/test_printer_roundtrip.py`
- `vdbmat-utils/tests/contract/test_print_slices_roundtrip.py`

### 変更

- `vdbmat-utils/src/vdbmat_utils/image/png.py` — `read_png_rgb()` 追加
- `vdbmat-utils/src/vdbmat_utils/image/stack.py` — levels の `rgb`
  エントリ対応（parse / 読込 / マッピング / エラー文言）
- `vdbmat-utils/tests/unit/test_image_png.py`（相当ファイル）— reader 追加分
- `vdbmat-utils/tests/unit/test_image_stack.py`（相当ファイル）— rgb levels
  の受理/拒否境界
- `vdbmat-utils/tests/contract/test_image_stack_contract.py` — rgb config の
  digest / double-run を既存水準で追加
- `vdbmat-utils/docs/image-stacks.md` — levels スキーマ拡張の記載
- `vdbmat-utils/docs/print-slices.md` — 往復手順・levels 導出規則・
  `preview-slices` 目視手順・claims 更新（往復契約が実装済みである旨）
- `vdbmat-utils/README.md` — convert-image-stack の色対応に1行
- `README_QUICK.md` — 新 Use Case + コマンド一覧表へ `export-print-slices`
  追加（Phase 1 で未追加のため本フェーズで行う）

## 実装ステップ

### Step 1 — 色 PNG reader（`image/png.py`）

1. `read_png_rgb()` を実装する（mode "P" はパレットテーブル直引き、
   mode "RGB" はそのまま、その他は明示エラー）。
2. unit test: mode "P"（Phase 1 の `write_indexed_png()` で書いたもの）と
   mode "RGB" の読込一致、"L"/"RGBA" の拒否、extra 未導入エラーの型。
   `write_indexed_png()` → `read_png_rgb()` の恒等性（パレット展開込み）を
   ここで固定する。

### Step 2 — levels の rgb 対応（`image/stack.py`）

1. `_parse_levels` を gray/rgb 両対応に拡張する（エントリ単位の
   排他検証、config 単位の混在禁止、rgb 重複、値域、format 制約）。
2. rgb モードの読込・パック・lookup・undeclared 検出を実装する。
3. unit test: 受理/拒否の境界（混在、両指定、欠落、重複 rgb、
   PGM + rgb、値域外）、小さな手書き色スタックの変換一致、
   undeclared 色のエラー位置報告。
4. contract test（`test_image_stack_contract.py` へ追加）: rgb config の
   canonical JSON round-trip・config digest 安定・double-run byte
   equality を既存 gray ケースと同水準で固定する。既存 gray の契約
   テストが無変更で通ることを確認する（純追加の証明）。

### Step 3 — levels 導出ヘルパ（`printer/roundtrip.py`）

1. `image_stack_config_from_print_manifest()` を実装する
   （manifest 検証、palette → levels、dpi → voxel_size 再計算）。
2. unit test: Phase 1 の実 manifest 形からの導出値（levels の全フィールド、
   voxel_size がピッチ式と bit 一致）、format/version 不一致・palette
   欠落フィールドの拒否。

### Step 4 — 往復契約テスト（`tests/contract/test_print_slices_roundtrip.py`）

すべて「export 実行 → manifest から config 導出 → `convert_image_stack()`
→ 一致基準（決定事項参照）」の形で固定する。入力生成には既存
fixture/generator（primitive array 小 config、`generate-fixture` 級）を
使い、`min_slices` はテスト用途の緩和を用いる。

1. **既定軸の往復完全一致**: 非対称最小入力（3×2×1 primitive array 級）で
   material_id 配列・voxel_size・palette の一致。
2. **軸交換・flip 変種**: `printer_x_axis`/`printer_y_axis` 交換、
   `flip_x`/`flip_y`/`flip_z` の各ケースで同じ等式が成立する
   （非対称入力で全数一致）。
3. **異方性リサンプリング感度**: 等方 100 µm ソース → 既定 600/300 dpi +
   27 µm。往復結果に対し、テスト内で独立に計算した最近傍期待配列
   （`clip(floor(center/src_size))` を直接 numpy で書いたもの）との
   全数一致。1 ソースボクセルが X:Y = 2:1 のピクセル比へ展開される
   ことをこのケースの既知値で確認する。
4. **等倍ケース**: ソース voxel size をピッチと厳密一致させた入力で、
   往復結果がソース配列と恒等になること（リサンプリングの退化ケース）。
5. **double-run**: 往復全体（export → convert）の2回実行で、再構成
   manifest digest（`stack_identity`）が一致する。
6. 往復で不一致が出た場合は **Phase 1 fix**（sampler / exporter 側の修正）
   として扱い、修正と再テストを report に記録する。本フェーズで
   期待値側を出力へ合わせて曲げない。

### Step 5 — docs と README 統合

1. `docs/image-stacks.md`: levels の gray/rgb スキーマ、混在禁止、
   色モードの reader 受理条件を追記する。
2. `docs/print-slices.md`: claims 更新（往復契約が実装済み）、levels
   機械導出規則（手書き再現可能な形で）、往復検証手順、
   `preview-slices` による目視確認手順（往復で得た `.voxels.json` を
   `preview-slices --axis z` で確認する）を追記する。
3. `README_QUICK.md`: Use Case「Export Print Slices for GrabCAD Voxel
   Printing」を追加する（generate → export → 目視/寸法確認 → 往復検証
   （convert-image-stack + preview-slices）の順、既存 Use Case の文体・
   コマンド形式に合わせる）。コマンド一覧表へ `export-print-slices` の
   行を追加する。
4. `vdbmat-utils/README.md`: convert-image-stack の色対応を1行追記する。

### Step 6 — 手動 walkthrough と report

README_QUICK の新 Use Case の記載どおりに手動 CLI で通し、report に
記録する。成果物は `.local/printer_export/p2/` に置き、git 管理しない。

1. `generate-primitive-array`（Phase 1 walkthrough と同じ 3×2×1 config）→
   `export-print-slices`（27 µm / High Speed プロファイル）。
2. manifest から levels config を導出（ヘルパで生成した JSON を保存）し、
   `convert-image-stack` で読み戻す。
3. `material-counts` で往復後の材料別ボクセル数が export サマリの
   材料別ピクセル数と一致することを照合する。
4. `preview-slices --axis z` で往復後ボクセルを目視し、3×2 の断面配置と
   異方性（X:Y = 2:1 ピクセル比）を確認する。
5. README_QUICK の記載と実際のコマンド・出力にずれがあれば docs を直す。

## テスト計画

### unit

- `read_png_rgb()`: mode 受理/拒否、mode "P" のパレット展開一致、
  `write_indexed_png()` との恒等性、extra 未導入エラー。
- levels rgb: parse の受理/拒否境界（Step 2-3 のとおり）、色マッピングの
  一致、undeclared 色の位置つきエラー。
- roundtrip ヘルパ: 導出値の bit 一致、manifest 検証の拒否系。

### contract

- image-stack: rgb config の digest 安定・round-trip・double-run
  （既存 gray 契約は無変更で通ること自体を確認項目とする）。
- print-slices roundtrip: Step 4 の 1〜5（完全一致、軸/flip 変種、
  異方性感度、等倍恒等、double-run）。

### end-to-end（手動、report 記録）

Step 6 のとおり。GrabCAD 実機ソフトでの受理確認は Phase 3 の責務。

### 静的検査

- 変更 Python への `ruff check`
- `uv run pytest tests/unit tests/contract`（vdbmat-utils、`image` extra
  あり。Phase 1 完了時点の 431 passed からの回帰なしを確認する）
- `git diff --check`

## 実施順序

```text
色 PNG reader（Step 1）
    ↓
levels rgb 対応（Step 2）
    ↓
levels 導出ヘルパ（Step 3）
    ↓
往復契約テスト（Step 4）
    ↓
docs・README 統合（Step 5）
    ↓
手動 walkthrough（Step 6）
```

読み戻し側（reader → stack）を先に単体で枯らし、往復契約テストは
「両端が既に固定された部品同士の接続」だけを検証する形にする。docs は
往復テストが通った事実を claims に書くため、テストの後に置く。

## 非ゴール

- 新機能の追加（roadmap どおり）。levels の rgb 対応と導出ヘルパは
  「往復契約の成立に必要な最小限」であり、これを超える入力拡張
  （RGBA、16-bit、色の近似マッチング等）はしない。
- 往復で発見された欠陥の「Phase 2 としての」修正（Phase 1 fix として
  扱い report に記録する）。
- GrabCAD 実機ソフトでの受理確認（Phase 3）。
- levels 導出の CLI サブコマンド化、名前付きプリンタプリセット、
  ディザリング、BMP、GUI / designlab 統合（Phase 4 候補）。
- `vdbmat` core / renderer exporters への変更。

## 完了条件

- 往復契約テスト（完全一致・軸/flip 変種・異方性感度・等倍恒等・
  double-run）が `uv run pytest tests/contract` で通る。
- levels config がサイドカーマニフェストから機械導出され、導出規則が
  docs に手書き再現可能な形で記載されている。
- `convert-image-stack` が色 PNG スタックを受理し、既存グレースケール
  契約（unit / contract）が無変更で通っている。
- README_QUICK の新 Use Case どおりに、primitive array →
  スライス PNG 群 → 読み戻し → `preview-slices` 目視まで手動 CLI で
  通ることが report に記録されている。
- 手動検証成果物が `.local/printer_export/p2/` に隔離され、git 管理
  ファイルにローカルパス・生成物が混入していない。

## リスクと方針

### 非整数ピッチの float が往復の voxel_size で不一致を起こす

manifest は `pitch_*_mm`（mm 換算値）も記録するが、mm → m の往復で
sampler のピッチと bit 一致しなくなりうる。導出ヘルパは **dpi /
layer_thickness_m の生値から sampler と同じ式で再計算**し、ヘルパの
unit test でピッチ式との bit 一致を固定する。

### mode "P" → RGB 展開の実装依存

Pillow の `convert("RGB")` はバージョンによって透過・パレット処理が
変わりうるため使わず、`getpalette()` のテーブル直引き（既存
`read_indexed_png()` と同じ経路）で展開する。`write_indexed_png()` →
`read_png_rgb()` の恒等性を unit test で固定し、Pillow 更新時の回帰を
機械的に検出する。

### 往復一致が「同じバグの両側」で偽装される

sampler にバグがあっても、export と期待値が同じ sampler を参照する限り
往復テストは通ってしまう。これを防ぐため、異方性感度ケース（Step 4-3）
の期待値は sampler を使わず**テスト内で独立に書いた最近傍計算**とし、
等倍ケース（Step 4-4）はソース配列そのものを期待値とする。この2系統が
sampler 非依存の外部基準になる。

### levels 拡張が既存 gray 経路を壊す

`_parse_levels` の共通化で既存のエラー文言・受理境界が変わると、既存
unit / contract テストが検出する。「既存テスト無変更で全通過」を Step 2
の完了条件に含め、文言変更が必要になった場合は report に明記する。

### 30 スライス制約と小フィクスチャの矛盾

契約テストの入力は小さくしたいが、既定 `min_slices=30` は小入力を
拒否する。Phase 1 config の「緩和はテスト用途のみ」の規約どおり、
テスト config で `min_slices` を緩和する。README_QUICK / 手動
walkthrough では緩和値を使う場合その旨を明記し、実機向け出力では
既定 30 のままにする（Phase 3 への申し送り事項）。
