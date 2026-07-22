# printer_export Phase 3 ex1 実装計画 — RGBA(32-bit) PNG出力への切り替え

親ロードマップ: `.devdocs/vision/printer_export/roadmap.md`（Phase 3 ex1）。
前フェーズ: `.devdocs/vision/printer_export/p3/todo.md`（実機検証で齟齬発見、
未完了）。Phase 1 (`../p1/plan.md`) / Phase 2 (`../p2/plan.md`) は完了済み。

## この計画の位置づけ

Phase 3 の実機検証（GrabCAD Voxel Print Utility）で、現行出力（インデックス
パレットPNG、`write_indexed_png()`、PNG color type 3）が「32ビット画像である
必要がある」という理由でGrabCAD側に拒否された。GrabCADが要求する「32ビット」は
PNG color type 6（トゥルーカラー+アルファ = RGBA、1ピクセル32ビット）を指すと
解される。GrabCAD側はcolor typeそのものを見ており、実際の色数（今回の
フィクスチャは赤緑2色のみ）は判定に関与しない。

Phase 3 todo の方針「齟齬が見つかった場合、修正はPhase 1実装へのfixとして
扱う」に従い、本計画はそのfixを単独のsub-phaseとして実装する。**Phase 3の
実機確認手順（色検出数・背景の扱い・寸法表示・命名規則）そのものはやり直さない
— 本計画の完了後、RGBA版スライスをGrabCADへ再投入して「32ビット」エラーが
解消したことだけを確認する**（それ以外の確認ポイントの再検証は、必要になった
時点でPhase 3 todoの再実行として別途行う）。

## 前提調査（確認済み事実）

### 現行実装（変更対象）

- `image/png.py::write_indexed_png()`（`vdbmat-utils/src/vdbmat_utils/image/png.py:88-123`）
  — mode `"P"` で書く。index 0 = 背景色、以降 `palette_rgb` 昇順。
- `printer/exporter.py::export_print_slices()`
  （`vdbmat-utils/src/vdbmat_utils/printer/exporter.py:104-121`）
  — zループ内で `sample_slice()` → `lookup[material_2d]`（material_id →
  palette index の `uint8` 配列、行90-92）→ `write_indexed_png()`。
  `_recheck_actual_colors()`（行157-166）が書き出し直後に
  `read_indexed_png()` でデコードし、出現index集合が宣言集合の部分集合か
  再検査する。
- `image/png.py::read_png_rgb()`（行49-85）— `convert-image-stack` の
  rgb levels 入力（Phase 2で追加）が使う色PNG reader。mode `"P"` と
  `"RGB"` を受理し、mode `"RGBA"` は**明示的に拒否**している（行82-85）。
  この拒否が、RGBA出力への切り替え後に往復契約（`convert-image-stack`
  での読み戻し）を壊す直接の原因になる。
- `image/png.py::read_indexed_png()`（行126-160）— デコード検証・往復
  テスト専用ヘルパ。mode `"P"` 以外を拒否する。exporter の
  `_recheck_actual_colors()` と契約テスト（後述）がこれに依存している。
- `image/stack.py`（行220-225）は `read_png_rgb()` を通じて色PNGを読む
  （rgb levels の入力経路）。exporter の出力形式が変わっても、この関数が
  RGBA を受理しさえすれば `image/stack.py` 自体の変更は不要。

### 影響が波及するテスト

- `tests/contract/test_print_slices_contract.py` — `read_indexed_png()`
  でデコードしたピクセル配列に対する golden digest pin
  （`GOLDEN_ANISOTROPIC_PIXEL_DIGEST` 等、行56-59）を持つ。出力が
  indexed から RGBA へ変わるため、**この digest は作り直しが必要**
  （エンコード方式の変更であり値の変更ではないが、pin 対象の配列形状が
  変わるため digest 自体は変わる）。
- `tests/contract/test_print_slices_roundtrip.py`（Phase 2）— manifest から
  導出した levels config で `convert_image_stack()` を呼び、`read_png_rgb()`
  経由で exporter 出力を読み戻す。現状は mode `"P"` を読むが、exporter が
  RGBA を書くようになった時点で `read_png_rgb()` が RGBA を拒否し失敗する。
  **RGBA 受理化とセットで初めて成立する**。
- `tests/unit/test_printer_png.py` — `write_indexed_png`/`read_indexed_png`/
  `read_png_rgb` の unit test 一式。RGBA 受理・書き出しのケースを追加する。
- `tests/unit/test_image_stack.py`（行302-308）・
  `tests/contract/test_image_stack_contract.py`（行183-188）— これらは
  `write_indexed_png()` / `read_png_rgb()` を**exporterと無関係に**
  「外部で塗られた色ラベルPNGの入力」という独立ユースケースの検証に
  使っている（roadmap の「色ラベルスタックの入力対応は独立のユースケース」
  という位置づけどおり）。**この経路は変更しない** — インデックスパレット
  PNG (mode "P") の読込能力自体は `convert-image-stack` の入力形式として
  引き続き有効であり、削除しない。

### 破壊的変更方針との関係

- `PrintSlicesConfig` に「出力PNGモードを選ぶ」トグルは追加しない
  （roadmap の破壊的変更方針: 後方互換のためだけのシムを残さない）。
  `export-print-slices` の出力は常にRGBAになる。
- `write_indexed_png()` / `read_indexed_png()` はモジュールから**削除しない**。
  これらは「convert-image-stack が受理する色PNG入力形式の一つ
  （インデックスパレット）」という exporter とは独立の契約であり、
  前提調査のとおり別のテスト群がこれを直接検証している。削除すると
  無関係な機能を壊す。exporter 側の呼び出しだけを新しい RGBA writer へ
  差し替える。
- `read_png_rgb()` の RGBA 拒否を受理へ変える変更は、既存の「グレースケール
  ・16-bit等は拒否」という契約を狭める方向（受理を広げる）の純追加であり、
  既存の "P"/"RGB" 経路には影響しない。

## 規模判定

単一フェーズの実装計画として扱える。変更は `image/png.py`（writer 1関数
追加 + reader 1関数の受理拡張）、`printer/exporter.py`（呼び出し差し替え +
再検査ロジック）、契約テストの digest 再固定、docs 1ファイルのみ。新規
モジュールは無い。

## ゴール

1. `export-print-slices` が RGBA（PNG color type 6、32-bit/pixel）PNGを
   出力する。
2. 「材料IDは補間・平均しない」契約（サンプリングは最近傍のみ）が変更前と
   同じ強度で保たれる — 本変更はエンコード方式のみの変更であり、
   `printer/sampler.py` は無変更。
3. Phase 2 で確立した往復契約（`export-print-slices` →
   `convert-image-stack` → 完全一致）が RGBA 出力に対して再度通る。
4. 実色数再検査（書き出し直後のデコード → 宣言色集合の部分集合か確認）が
   RGBA配列に対して機能し続ける。
5. RGBA版の出力を実機（GrabCAD Voxel Print Utility）へ再投入し、「32ビット」
   エラーが解消したことが確認され report に記録される。

## 決定事項

### RGBA writer は既存の index→RGB展開を書き出し直前に行うだけに留める

`exporter.py` の `lookup[material_2d]`（material_id → palette index の
`uint8` 2D配列を作る既存ロジック、行90-92, 106）は変更しない。書き出し
直前に

```python
palette_array = np.asarray(palette_rgb, dtype=np.uint8)   # shape (N, 3)
rgb_2d = palette_array[indices_2d]                         # (H, W, 3)
alpha_2d = np.full((*indices_2d.shape, 1), 255, dtype=np.uint8)
rgba_2d = np.concatenate([rgb_2d, alpha_2d], axis=-1)       # (H, W, 4)
write_rgba_png(slice_path, rgba_2d)
```

という展開を挟む。サンプリング・lookup・index配列は完全に既存のままであり、
変更点は「indexへ着色したPNGを書く」から「RGBへ展開してから書く」への
最終段だけに閉じ込める。alphaは常に255（全ピクセル不透明）——
本パイプラインは透過を一切表現しないため、透過値を持つ入力を想定した
分岐は作らない。

### `write_rgba_png()`（新規、`image/png.py`）

- `Image.fromarray(rgba, mode="RGBA")` で書く。既存 `write_indexed_png()`
  と同じく、アンチエイリアス・リサイズ・ICCを一切通さない
  （中間色が構造的に発生しない性質を維持）。
- 圧縮パラメータは `write_indexed_png()` と同じ規約（固定
  `compress_level`、決定論的 double-run。file byte 一致は同一環境のみ、
  digest pin はデコード後ピクセル配列に対して行う——既存規約を踏襲）。
- `write_indexed_png()` は削除しない（前提調査のとおり独立契約）。

### `read_png_rgb()` の RGBA 受理（`image/png.py`）

- mode `"RGBA"` を追加受理する。アルファチャンネルは以下のルールで扱う:
  - 全ピクセルの alpha が 255（完全不透明）であることを検証し、
    RGBチャンネルのみを `(H, W, 3)` として返す（既存の戻り値型を変えない
    — `convert-image-stack` の rgb levels 側は変更不要になる）。
  - alpha に255以外の値が1ピクセルでもあれば明示エラー（本パイプラインが
    書く画像は常に不透明であるという契約を裏付け、透過つき外部PNGの
    サイレント誤読を防ぐ）。
- mode `"L"` / `"I"` / `"I;16"` 等、既存の拒否対象はそのまま拒否する。

### 実色数再検査（`printer/exporter.py::_recheck_actual_colors`）

- index集合ではなく **RGB値集合**（`palette_rgb` の一意な `(r,g,b)`
  タプル集合）で判定するよう書き換える。書き出し直後に `read_png_rgb()`
  （更新後、RGBAをRGBへ展開して返す）でデコードし、出現RGB集合が
  `set(palette_rgb)` の部分集合であることを確認する。
  `palette_rgb` の重複禁止は Phase 1 で既に validation 済み
  （`PrintSlicesConfig`）なので、index集合とRGB集合の判定は等価。
- `read_indexed_png()` への依存はこの関数から外れる（削除はしない —
  上記のとおり別契約として残る）。

### 契約テストの golden digest 再固定

- `tests/contract/test_print_slices_contract.py` の
  `GOLDEN_ANISOTROPIC_PIXEL_DIGEST` / `GOLDEN_MULTIMATERIAL_PIXEL_DIGEST`
  はデコード対象配列の形状・意味が変わる（indexedの `(H,W)` uint8配列から
  RGBAの `(H,W,4)` uint8配列へ）ため作り直す。値そのものの意味的な変更
  ではない（同じサンプリング結果を別のバイト表現でエンコードしている
  だけ）ことを report に明記する。
- digest 計算対象を `read_indexed_png()` から `read_png_rgb()`
  ベースのRGBAデコード（もしくは新設する薄いRGBA専用デコードヘルパ）へ
  差し替える。

## 対象ファイル

### 変更

- `vdbmat-utils/src/vdbmat_utils/image/png.py` — `write_rgba_png()` 追加、
  `read_png_rgb()` の RGBA 受理（alpha検証込み）
- `vdbmat-utils/src/vdbmat_utils/printer/exporter.py` — writer 呼び出しを
  `write_rgba_png()` へ差し替え、`_recheck_actual_colors()` を RGB集合判定へ
- `vdbmat-utils/tests/unit/test_printer_png.py` — RGBA書き出し/読込の
  unit test 追加、alpha非255拒否のテスト追加
- `vdbmat-utils/tests/unit/test_printer_exporter.py` — 実色数再検査の
  作動確認ケースをRGBA前提に更新
- `vdbmat-utils/tests/contract/test_print_slices_contract.py` — golden
  digest 再生成、デコード手段を `read_png_rgb()` ベースへ変更
- `vdbmat-utils/tests/contract/test_print_slices_roundtrip.py` — RGBA
  出力に対して Phase 2 の一致基準（完全一致・軸/flip変種・異方性感度・
  等倍恒等・double-run）が変更なしで通ることを確認（テストコード自体は
  `read_png_rgb()` の受理範囲拡大で自動的に通る想定、既存テストの
  digest等固定値があれば併せて更新）
- `vdbmat-utils/docs/print-slices.md` — 「PNG encoding」節を RGBA前提へ
  書き換え、claims節に「GrabCAD実機確認済み: RGBA(32-bit)出力が必須、
  インデックスパレットPNGはVoxel Print Utilityに拒否される」を追記

### 変更しない

- `vdbmat-utils/src/vdbmat_utils/printer/sampler.py`
  （サンプリングロジックは無変更）
- `vdbmat-utils/src/vdbmat_utils/image/png.py` 内の `write_indexed_png()` /
  `read_indexed_png()`（独立契約として残す）
- `vdbmat-utils/src/vdbmat_utils/image/stack.py`
  （`read_png_rgb()` の戻り値型が変わらないため無変更）
- `vdbmat-utils/src/vdbmat_utils/printer/types.py`（`PrintSlicesConfig` に
  出力モードのトグルは追加しない）

## 実装ステップ

### Step 1 — RGBA reader/writer（`image/png.py`）

1. `write_rgba_png()` を実装する（mode "RGBA"、固定圧縮パラメータ、
   ICC/リサイズ非経由）。
2. `read_png_rgb()` に mode "RGBA" 受理を追加する（alpha==255全数検証、
   違反時は明示エラー、RGBのみ返す）。
3. unit test:
   - `write_rgba_png()` → `read_png_rgb()` の恒等性（RGB値のみ）。
   - alpha が255以外を含むRGBA PNGを直接構成し、`read_png_rgb()` が
     明示エラーで拒否することを確認する（`Image.fromarray` で手作り）。
   - 既存の "L"/16-bit拒否・"P"/"RGB"受理が無変更で通ることを確認する
     （回帰なしの証明）。

### Step 2 — exporter の差し替え（`printer/exporter.py`）

1. zループ内の書き出しを `write_indexed_png()` から、決定事項の
   index→RGBA展開 + `write_rgba_png()` へ差し替える。
2. `_recheck_actual_colors()` を RGB集合ベースの判定へ書き換える。
3. unit test: 実色数再検査が異常系（人為的に宣言外RGBを仕込む）で
   作動することを確認するケースを RGBA 前提に更新する。既存の
   「出力レイアウト・atomic性・マニフェスト検算」テストは無変更で
   通ることを確認する（サンプリング・マニフェスト内容は不変のため）。

### Step 3 — 契約テストの再固定

1. `test_print_slices_contract.py` のデコード手段を `read_png_rgb()`
   ベースへ差し替え、golden digest を新しい値で再生成する
   （`uv run pytest` を一度実行し新digestを確認・記録してから固定する
   規約は既存契約テストの流儀に合わせる）。
2. `test_print_slices_roundtrip.py`（Phase 2）を実行し、RGBA出力に対して
   Phase 2 の5基準（完全一致・軸/flip変種・異方性感度・等倍恒等・
   double-run）が無変更で通ることを確認する。通らない場合、原因が
   本フェーズの変更漏れかPhase 2契約の暗黙のindexed前提かを切り分けて
   report に記録する。

### Step 4 — docs 更新

1. `docs/print-slices.md` の「PNG encoding」節を RGBA 前提に書き換える
   （`write_rgba_png()` の説明、alpha=255固定、indexed版との違い）。
2. claims 節に実機確認済みの解釈として追記する（roadmap Phase 3ex1の
   完了条件どおり）。

### Step 5 — RGBA版の再生成と実機再投入（人間作業、AIは準備のみ）

1. `.local/printer_export/p3/` の既存 config（`primarray.json` /
   `pad.pipeline.json` / `printslices.json`）を再利用し、
   `export-print-slices` を再実行してRGBA版スライスを生成する
   （config自体の変更は不要、出力形式のみ変わる）。
2. 生成物をzip化し、GrabCADへ再投入して「32ビット」エラーが解消したかを
   確認する（人間作業）。
3. 結果を `.devdocs/vision/printer_export/p3ex1/report1.md` に記録する。

## テスト計画

### unit

- `read_png_rgb()` / `write_rgba_png()`: 恒等性、alpha非255拒否、既存
  "P"/"RGB"/拒否対象モードの無回帰。
- exporter: 実色数再検査のRGBA前提での作動、既存レイアウト/atomic性/
  マニフェスト検算テストの無回帰。

### contract

- print-slices: golden pixel digest（RGBAデコード基準で再固定）、
  同一環境double-run、パラメータ感度、seed非依存、色数制約 — Phase 1
  契約テストの構成をそのまま維持し、デコード手段のみ差し替える。
- roundtrip: Phase 2 の5基準がRGBA出力に対して無変更で通る。

### end-to-end（手動、report記録）

Step 5 のとおり。RGBA版の実機再投入は本フェーズの完了条件の一部
（Phase 3の全確認ポイントの再確認ではなく「32ビットエラーが解消したか」
のみを対象とする）。

### 静的検査

- 変更 Python への `ruff check`
- `uv run pytest tests/unit tests/contract`（vdbmat-utils、`image` extra
  あり。Phase 2 完了時点からの回帰なしを確認する）
- `git diff --check`

## 実施順序

```text
RGBA reader/writer（Step 1）
    ↓
exporter 差し替え（Step 2）
    ↓
契約テスト再固定（Step 3）
    ↓
docs 更新（Step 4）
    ↓
RGBA版の再生成と実機再投入（Step 5、人間作業）
```

reader/writerをexporterと独立に先に固定し、exporter側の変更を「新しい
部品への差し替え」だけに縮小する。契約テストは差し替え後の実際の出力に
対して再固定するため、Step 2の後に置く。

## 非ゴール

- ハーフトーン/ディザリング、BMPレガシー、名前付きプリンタプリセット
  （roadmap Phase 4のまま、対象外）。
- インデックスパレットPNGを出力形式として選べる config トグルの追加
  （破壊的変更方針により作らない）。
- `write_indexed_png()` / `read_indexed_png()` の削除（convert-image-stack
  の独立した入力経路として維持する）。
- Phase 3の全確認ポイント（色検出数・背景の扱い・寸法表示・命名規則）の
  再実施。本フェーズは「32ビットエラーの解消」のみを実機再投入で確認する。
- `printer/sampler.py` の変更（サンプリングロジックは対象外）。

## 完了条件

- `export-print-slices` がRGBA（32-bit、color type 6）PNGを出力する。
- 実色数再検査がRGBA前提で機能し、既存の異常系検出テストが通る。
- 契約テスト（golden digest 再固定、double-run、パラメータ感度、
  色数制約）が新しいエンコード方式で通る。
- Phase 2 往復契約テストがRGBA出力に対して無変更の基準で通る。
- `docs/print-slices.md` に実機確認済みの解釈として記録されている。
- RGBA版の出力をGrabCAD Voxel Print Utilityへ再投入し、「32ビット」
  エラーが解消したことが `.devdocs/vision/printer_export/p3ex1/report1.md`
  に記録されている。

## リスクと方針

### golden digest 再固定が「値の意味的な変更」と誤解される

digest自体は変わるが、これは配列の**エンコード表現**が変わったためで
あり、サンプリング結果・マニフェストの物理寸法・材料対応は不変である。
report に「新旧digestの差分はエンコード方式変更によるものであり、
`sampler.py` 変更によるものではない」ことを明記し、`test_printer_sampler.py`
（Phase 1、無変更）が全数一致のまま通ることをもって裏付けとする。

### alpha=255固定の前提が将来の透過表現ニーズと衝突する

本パイプラインは材料IDのみを扱い、濃度・透過を表現しない
（roadmap 非ゴール、ディザリング/連続材料混合はPhase 4候補の独立vision）。
alpha=255固定はこの前提の直接の帰結であり、透過表現が必要になった場合は
本fixではなく独立したvisionとして扱う。

### 出力ファイルサイズの増加

インデックスPNG（1ピクセル最大8bit、パレット参照）からRGBA
（1ピクセル32bit）へのエンコード変更でファイルサイズは増える
（同じ色数でも保存効率が異なる）。今回の検証規模（数十スライス、
数十×数十px）では無視できるが、`max_total_pixels` ガードは総ピクセル数
基準のままであり、ファイルサイズそのものへのガードは無い。実運用規模
（数千スライス級）でのサイズ問題が確認された場合はPhase 4候補として
扱う。

### 「32ビット」の解釈が誤り、実際にはRGB(24-bit)で足りる可能性

GrabCADのエラーメッセージ文言から「RGBA(32bit)」と推定しているが、
「RGB(24bit、アルファなし)」でも解消する可能性はゼロではない
（"P"モードのインデックス表現が真の問題で、トゥルーカラー化自体が
本質という可能性）。Step 5の実機再投入で「32ビットエラーが解消したか」
を確認し、もし解消しない場合はRGB(24bit)モードでの追加検証を
report に記録し、必要であれば本plan自体をfixする
（`write_rgba_png()`と並べて`write_rgb_png()`相当を用意する変更は
本plan完了条件に影響しない範囲の追加作業として扱う）。
