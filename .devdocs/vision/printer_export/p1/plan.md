# printer_export Phase 1 実装計画 — export-print-slices CLI本体

親ロードマップ: `.devdocs/vision/printer_export/roadmap.md`（Phase 1）。

## この計画の位置づけ

本計画は Phase 1 の実装だけを対象とする。`convert-image-stack` との往復契約
テストと README_QUICK の Use Case 統合は Phase 2、GrabCAD Voxel Print Utility
での実機ソフト検証は Phase 3 で扱う。

Phase 1 の成果物は、`vdbmat-utils` の新しいエクスポータ・サブコマンド1つである。
material-label ボクセル（`.voxels.json` + `.material_id.npy`）から、GrabCAD
Print voxel printing の PNG メソッドに適合するスライス PNG 群とサイドカー
マニフェストを、config JSON 1枚から決定論的に生成する。

```text
<name>.voxels.json + <name>.material_id.npy
      ↓
export-print-slices（--config printslices.json）
      ↓
<out>/<name>/slice_0000.png … slice_NNNN.png
<out>/<name>/<name>.printslices.json
```

## 前提調査（確認済み事実）

### 既存規約

- config は `GeneratorConfig` を継承した frozen dataclass
  （`src/vdbmat_utils/core/config.py`）。canonical JSON（sorted keys、余白なし、
  NaN/Inf 拒否）が configuration digest の入力であり、`from_json()` は
  未知フィールドを明示的に拒否する。`seed` は基底クラスのフィールド
  （本方式は乱数を使わない。予約）。
- CLI は `src/vdbmat_utils/cli/main.py` に argparse サブコマンドを追加し
  `_cmd_*()` へ dispatch する形式。既存の実行形は
  `<subcommand> [入力] --config C --out DIR --name NAME`。
- `.voxels.json` の読込は `preview-slices` / `material-counts` が使う既存経路
  （manifest 検証 + payload sha256 照合込み）を再利用する。
- Pillow は optional extra `image`（`pillow>=10`）として既に宣言済み。
  `image/png.py` は lazy import で「extra 未導入なら actionable エラー」の
  規約を確立している。**ただし既存 PNG コードは読込専用かつグレースケール
  （mode "L"）専用**。PNG 書き出しは本フェーズで新設する。
- 契約テストの水準は `tests/contract/` の既存ファイル（digest pin、
  double-run byte equality、パラメータ感度）に合わせる（`docs/determinism.md`）。

### 往復契約（Phase 2）に効く制約

`convert-image-stack`（`image/stack.py`）の `levels` は **gray 値（0..255）→
material** の対応であり、reader は 8-bit グレースケールしか受理しない。
GrabCAD 向け出力は色 PNG（インデックスパレット RGB）なので、**Phase 2 の
往復契約は convert-image-stack の RGB / パレット対応（破壊的変更方針の範囲で
levels スキーマを拡張）か、往復専用のグレースケール読み戻しのどちらかを
Phase 2 plan で決める必要がある**。Phase 1 では、この決定に依存しない
「Pillow で読み戻し → パレット逆引き → サンプリング済み配列と一致」の
デコード検証を契約テストに含め、往復可能性を先に担保する。

### GrabCAD PNG メソッドの制約（roadmapに記載の根拠の再掲）

- 1レイヤー = 1 PNG、共通プレフィックス + 連番。
- X = 600 dpi（25.4/600 mm）、Y = 300 dpi（25.4/300 mm）、
  レイヤー厚 14 µm（High Quality）/ 27 µm（High Speed / High Mix）。
- 背景を除き 1 画像あたり最大 6 色（High Speed は 3 色）。中間色は不可。
- 最低 30 スライス。

### 破壊的変更方針との関係

Phase 1 は純追加であり、既存の config・CLI・出力契約に変更はない。
`image/` パッケージへ writer を足すが、既存 reader の契約は変えない。

## 規模判定

単一フェーズの実装計画として扱える。新規モジュール1つ（+ `image/` への
writer 追加）、CLI 1 サブコマンド、docs 1 ファイル、unit / contract テストの
追加のみで、既存契約の変更を含まない。

## ゴール

1. `vdbmat-utils export-print-slices` が `.voxels.json` と config JSON 1枚から
   決定論的にスライス PNG 群 + マニフェストを出力する。
2. 出力格子は物理バウンドとプリンタピッチから導出され、材料 ID は最近傍
   サンプリングのみで補間されない。
3. プリンタ制約違反（色数、スライス数、パレット欠落）が出力前の明示エラーになる。
4. 出力は atomic に発行され、失敗時に部分成果物が残らない。
5. 契約テストが既存ジェネレータと同水準で揃い、デコード検証で往復可能性が
   担保されている。

## 決定事項

### コマンド名とモジュール配置

- サブコマンド: `export-print-slices`
- モジュール: `src/vdbmat_utils/printer/`
  - `types.py` — `PrintSlicesConfig` とプロファイル/パレットの validation
  - `sampler.py` — 出力格子導出と最近傍サンプリング（純関数、PNG 非依存）
  - `exporter.py` — スライス書き出し・マニフェスト・atomic 発行
- PNG 書き出し: `src/vdbmat_utils/image/png.py` へ `write_indexed_png()` を
  追加する（lazy import 規約は既存 `read_png()` と同一）。

### config スキーマ（`PrintSlicesConfig`）

```text
PrintSlicesConfig(GeneratorConfig)
├── dpi_x: float = 600.0                        > 0
├── dpi_y: float = 300.0                        > 0
├── layer_thickness_m: float                    必須、> 0（14e-6 / 27e-6 を想定）
├── max_materials: int = 6                      1..6（High Speed 時は 3 を指定）
├── palette: dict[str, [int, int, int]]         必須
│      material_id（10進文字列）→ RGB（各 0..255）。非背景材料のみ。
├── background_rgb: [int, int, int] = [0, 0, 0]
├── printer_x_axis: "x" | "y" = "x"             面内軸対応（printer X = 600dpi 側）
├── printer_y_axis: "x" | "y" = "y"             printer_x_axis と相異必須
├── flip_x: bool = false                        printer X 方向の反転
├── flip_y: bool = false
├── flip_z: bool = false                        スライス順（build 方向）の反転
├── name_prefix: str = "slice_"
├── index_start: int = 0                        >= 0
├── min_slices: int = 30                        >= 1（緩和はテスト用途のみ）
├── max_total_pixels: int = 4_000_000_000       出力総ピクセル数ガード
└── seed: int = 0（継承。payload へ影響しない。予約）
```

- スライス軸は **z 固定**（`shape_zyx` の z がレイヤー方向）。z 以外を
  レイヤー方向にしたい場合は既存 `apply-pipeline` の `orient` で入力側を
  回す。エクスポータに回転責務を持たせない。
- `palette` のキーは canonical JSON 制約（dict キーは文字列）のため
  material_id の10進文字列とする。重複 RGB、背景色との衝突、`role:
  "background"` 材料のエントリはすべて明示エラー。
- 入力に存在する非背景 material_id が palette に無ければエラー。palette に
  余分な id があってもエラー（config と入力の対応を厳密に保つ）。
- 色数制約は「palette エントリ数 <= max_materials」で fail-fast し、さらに
  出力 PNG ごとの実使用色再検査（後述）で二重化する。
- プリンタプロファイルの名前付きプリセット化は Phase 4。本フェーズは生数値。

### 出力格子導出とサンプリング規則（`sampler.py`）

物理ピッチを

```text
pitch_x = 0.0254 / dpi_x   （既定 42.333… µm）
pitch_y = 0.0254 / dpi_y   （既定 84.666… µm）
pitch_z = layer_thickness_m
```

とし、ソースの物理 extent（`shape * voxel_size`、軸対応適用後）から
出力セル数を `ceil(extent / pitch - 1e-6)` で導出する
（voxelize-mesh / primitive array と同じ 1e-6 epsilon 規則）。

サンプリングは **出力ピクセル中心の物理座標 → 最近傍ソースボクセル**:

- 出力 index i の中心座標 `(i + 0.5) * pitch` に対し、ソース index は
  `clip(floor(center / src_voxel_size), 0, src_cells - 1)`。
- 軸ごとに index 配列を事前計算し、`np.take` の3段適用で全体を引く。
  Python ループはスライス方向（z）に限る（スライス単位のストリーミング
  書き出しと一体化し、全出力を同時にメモリへ持たない）。
- 補間・平均・多数決は行わない。境界 tie（中心がソースセル境界に一致）は
  `floor` により低位側で、全軸一貫。
- `flip_*` はソース index 配列の反転として適用する（ピクセル中心規則は不変）。

### PNG エンコード（`write_indexed_png()`）

- Pillow の mode "P"（インデックスパレット）で書く。パレットテーブルは
  index 0 = `background_rgb`、以降 config `palette` の material_id 昇順。
  ピクセル値は palette index（uint8）。
- アンチエイリアス・リサイズ・ICC プロファイル等を一切通さないため、
  中間色は構造的に発生しない。
- 決定論: 圧縮パラメータを固定して書く。ただし PNG の byte 表現は Pillow
  実装に依存しうるため、**契約テストの digest pin はデコード後のピクセル
  配列に対して行い、ファイル byte の equality は同一環境 double-run のみに
  要求する**（リスク節参照）。

### 出力レイアウトと atomic 発行

```text
<out>/<name>/                       ← 発行単位（既存があれば明示エラー）
├── slice_0000.png … slice_NNNN.png
└── <name>.printslices.json
```

- `<out>/.<name>.tmp-*` で組み立て、全 PNG + マニフェスト書き出しと
  実色数再検査の成功後に `<out>/<name>/` へ atomic rename する。
  失敗時は tmp を削除し、`<out>` へ何も残さない。
- 連番の桁数はスライス総数から導出（最低4桁、ゼロ埋め）。

### サイドカーマニフェスト（`<name>.printslices.json`）

```text
format: "vdbmat.print-slices" / format_version: "1.0.0"
source: 入力 .voxels.json の識別（manifest sha256 + payload sha256）
config_digest: PrintSlicesConfig の canonical JSON digest
printer: dpi_x / dpi_y / layer_thickness_m / pitch（導出値、mm）
grid: スライス数、ピクセル数（X, Y）、物理寸法（mm、3軸）
palette: material_id → { name, role, rgb }（材料名は入力 manifest から転記）
background_rgb
slices: name_prefix / index_start / 桁数 / 各ファイルの sha256
```

- 相対パス・ファイル名のみを記録し、絶対パス・タイムスタンプ・ホスト名を
  含めない（既存 determinism 規約）。
- `grid` の物理寸法（mm）は軸取り違え検算の一次資料（roadmap 設計原則3）。
- GrabCAD GUI での色→材料対応付けの手順書を兼ねるため、palette には
  材料名を必ず転記する。

### バリデーション（すべて明示エラー、発行前）

1. 入力 manifest / payload の整合（既存読込経路の検証に乗る）。
2. palette と入力材料集合の完全一致（背景を除く）。
3. 非背景材料数 > `max_materials`。
4. RGB 重複・背景色衝突・値域外。
5. 導出スライス数 < `min_slices`。
6. 出力総ピクセル数 > `max_total_pixels`（voxel size を粗くする/入力を
   縮める提案つき）。
7. 書き出し後の実使用色再検査: 各 PNG のデコード結果に現れる palette index
   の集合が宣言集合の部分集合であること（違反は内部バグとして発行中止）。

### CLI

```bash
uv run vdbmat-utils export-print-slices input/model.voxels.json \
  --config printslices.json --out out/ --name model
```

- CLI フィールド上書きは設けない。config ファイルが唯一の入力
  （designlab Phase 1 と同じ方針。将来の GUI=CLI 再現契約を保つ）。
- 成功時サマリ: 発行パス、スライス数、ピクセル数、物理寸法（mm）、
  材料別ピクセル数。
- `image` extra 未導入時は既存 `read_png()` と同型の actionable エラー。

## 対象ファイル

### 新規

- `vdbmat-utils/src/vdbmat_utils/printer/__init__.py`
- `vdbmat-utils/src/vdbmat_utils/printer/types.py`
- `vdbmat-utils/src/vdbmat_utils/printer/sampler.py`
- `vdbmat-utils/src/vdbmat_utils/printer/exporter.py`
- `vdbmat-utils/tests/unit/test_printer_types.py`
- `vdbmat-utils/tests/unit/test_printer_sampler.py`
- `vdbmat-utils/tests/unit/test_printer_exporter.py`
- `vdbmat-utils/tests/contract/test_print_slices_contract.py`
- `vdbmat-utils/docs/print-slices.md`

### 変更

- `vdbmat-utils/src/vdbmat_utils/image/png.py` — `write_indexed_png()` 追加
- `vdbmat-utils/src/vdbmat_utils/cli/main.py` — サブコマンド追加
- `vdbmat-utils/tests/unit/test_cli.py` — CLI 経路のテスト追加
- `vdbmat-utils/README.md` — コマンド一覧へ1行追加

README_QUICK の Use Case 追記は Phase 2（往復契約と同時に手順を確定させる）。

## 実装ステップ

### Step 1 — config 契約（`types.py`）

1. `PrintSlicesConfig` を frozen dataclass として定義し、`__post_init__` で
   全 validation（正値、軸対応の相異、palette 構造、RGB 値域・重複・背景衝突、
   ガード値）を行う。
2. 未知フィールド拒否・round-trip・digest は基底クラスの既存機構に乗せる。
3. Pillow 不要の unit test で契約を固定する（受理・拒否の境界値、
   canonical JSON round-trip、digest 安定性）。

### Step 2 — サンプリング純関数（`sampler.py`）

1. ピッチ導出・出力形状導出（ceil + epsilon）・ガードを純関数で実装する。
2. 軸対応 + flip を適用した最近傍 index 配列の事前計算と、z スライス1枚分の
   palette-index 配列を返す関数を実装する（PNG・ファイル IO 非依存）。
3. unit test:
   - 整数比ケースの厳密 shape（例: ソース 84.666…µm = pitch_y ちょうど）。
   - 非整数比（等方 100 µm → 600/300 dpi + 27 µm）で、既知の小さい入力に
     対する index 配列の全数一致。
   - 境界 tie の `floor` 一貫性、clip による端の張り出し防止。
   - `printer_x_axis`/`printer_y_axis` 交換と `flip_*` の各組み合わせで
     期待配列一致（3×2×1 のような非対称最小入力で全数検証）。
   - 総ピクセルガード超過の提案つきエラー。

### Step 3 — PNG writer と exporter（`png.py` / `exporter.py`）

1. `write_indexed_png()`: mode "P" + 固定パレットテーブル + 固定圧縮
   パラメータ。読み戻し（`Image.open` → palette index 配列復元）ヘルパも
   テスト用に用意する。
2. `exporter.py`: 入力読込 → validation → tmp ディレクトリで z ループ
   （sampler → PNG 書き出し → sha256 集計）→ 実色数再検査 → マニフェスト
   書き出し → atomic rename。
3. unit test: 出力レイアウト、桁数導出、既存出力先での拒否、途中失敗
   （palette 欠落を仕込む）で `<out>` が汚れないこと、マニフェスト内容の
   物理寸法検算。

### Step 4 — CLI 接続

1. `export-print-slices` サブコマンドと `_cmd_export_print_slices()` を追加。
2. 成功サマリ・エラー exit code を既存コマンドと揃える。extra 未導入時の
   メッセージを確認する。
3. `test_cli.py` へ正常系・config エラー系・入力欠落系を追加する。

### Step 5 — 契約テスト

`tests/contract/test_print_slices_contract.py` に既存水準で固定する。

1. 代表入力2種（primitive array 小 config から生成した非対称ボクセル、
   `generate-fixture` 級の最小ボクセル）× 代表 config
   （HQ 14 µm / HS 27 µm + max_materials=3）の
   **デコード済みピクセル配列の digest pin**。
2. 同一環境 double-run byte equality（PNG ファイル・マニフェストとも）。
3. デコード検証（往復可能性の先行担保）: 全スライスを読み戻し、palette
   逆引きで material_id 配列へ復元し、sampler が返すプリンタ格子配列と
   完全一致。
4. パラメータ感度: `dpi_x`/`layer_thickness_m`/`flip_z`/palette RGB の変更で
   ピクセル digest（または palette テーブル）が変わる。
5. seed 非依存: `seed` 変更でピクセル digest 不変（config digest は変わる）。
6. 色数制約: 7材料入力 + max_materials=6 で発行前エラー、tmp 残留なし。

### Step 6 — docs と手動確認

1. `docs/print-slices.md`: config 形、格子導出・サンプリング規則、出力
   レイアウト、マニフェスト仕様、GrabCAD GUI での色→材料対応付け手順、
   claims / non-claims（GCVF 受理は Phase 3 まで未確認である旨を明記）。
2. `vdbmat-utils/README.md` のコマンド一覧へ追記。
3. 手動 walkthrough を実施し report に記録する:
   `generate-primitive-array`（数を数えられる 3×2×1）→
   `export-print-slices`（27 µm プロファイル）→ 出力 PNG を画像ビューアで
   目視（断面の個数・縦横比が dpi 異方性どおり X:Y = 2:1 のピクセル比に
   なること）→ マニフェストの物理寸法をソース extent と手計算で照合。
   成果物は `.local/printer_export/p1/` に置き、git 管理しない。

## テスト計画

### unit（Pillow 不要: Step 1–2 / Pillow 必要: Step 3–4）

- config: 必須欠落、値域外、軸対応重複、palette 不正（重複 RGB、背景衝突、
  背景材料エントリ、値域外）、未知フィールド、round-trip、digest 安定。
- sampler: 形状導出（整数比・非整数比・epsilon）、index 全数一致、tie、
  軸交換 + flip 全組み合わせ、ガード。
- exporter: レイアウト、atomic 性（失敗時の非発行）、既存出力先拒否、
  マニフェスト検算、実色数再検査の作動（人為的に汚した配列で発行中止）。
- CLI: 正常系、config/入力エラーの exit code、extra 未導入メッセージ。

### contract

Step 5 のとおり（ピクセル digest pin、double-run、デコード検証、感度、
seed 非依存、色数制約）。

### end-to-end（手動、report 記録）

Step 6-3 のとおり。GrabCAD 実機ソフトでの受理確認は Phase 3 の責務であり、
本フェーズでは要求しない。

### 静的検査

- 変更 Python への `ruff check`
- `uv run pytest tests/unit tests/contract`（vdbmat-utils、`image` extra あり）
- `git diff --check`

## 実施順序

```text
config 契約（Step 1）
    ↓
サンプリング純関数（Step 2）
    ↓
PNG writer・exporter（Step 3）
    ↓
CLI 接続（Step 4）
    ↓
契約テスト（Step 5）
    ↓
docs・手動確認（Step 6）
```

sampler を PNG・IO 非依存の純関数として先に枯らす。Phase 2 の往復契約は
「sampler の出力配列」を共通参照点にするため、この分離が往復テストの
土台になる。

## 非ゴール

- `convert-image-stack` との往復契約テスト（Phase 2。ただしデコード検証で
  往復可能性は本フェーズで担保する）。
- README_QUICK への Use Case 追記（Phase 2）。
- GrabCAD 実機ソフトでの受理確認（Phase 3）。
- BMP レガシーメソッド、名前付きプリンタプリセット、High Speed の
  プロファイル自動切替（`max_materials=3` の手動指定で代替）。
- 30 スライス未満入力の自動背景パディング。
- ハーフトーン/ディザリング、連続材料混合。
- スライス軸の z 以外対応（`apply-pipeline` の `orient` に委譲）。
- GUI・designlab 統合。

## 完了条件

- `export-print-slices` が config JSON 1枚で決定論的にスライス PNG 群 +
  マニフェストを atomic に発行する。
- 出力格子導出・最近傍 index が unit test で全数固定されている。
- 契約テスト（ピクセル digest pin、double-run、デコード検証、感度、
  seed 非依存、色数制約）が通る。
- 制約違反（色数、スライス数、パレット欠落、ガード超過）が発行前の明示
  エラーになり、失敗時に `<out>` へ何も残らない。
- docs / README が更新され、既存契約・既存テストに変更がない。
- 手動 walkthrough（primitive array → export → 目視 + 寸法照合）が report に
  記録され、検証成果物が `.local/printer_export/p1/` に隔離されている。

## リスクと方針

### PNG byte 表現が Pillow バージョンに依存する

zlib / Pillow の圧縮実装差で、同一ピクセルでもファイル byte が環境間で
変わりうる。契約の digest pin は**デコード後のピクセル配列**に置き、
byte equality は同一環境 double-run のみに要求する。マニフェストの
per-file sha256 は「その発行物の完全性検証」用であり、環境間再現の
契約対象にしない（docs に明記する）。

### 非整数ピッチの float 丸めで index 配列が環境によりずれる

`center / src_voxel_size` の floor が境界すれすれで振れるリスク。sampler の
unit test に「境界に厳密一致する中心座標」を含む全数一致ケースを置き、
ずれが出た場合は式を変えず epsilon 規則の適用位置を voxelize-mesh の
既実装に揃える（primitive array plan と同じ方針）。

### 軸対応（600/300 dpi）の解釈違い

config 既定（voxel x → printer X = 600 dpi）が GrabCAD の実解釈と食い違う
可能性は Phase 3 まで残る。マニフェストの物理寸法記録と手動 walkthrough の
ピクセル比確認（X:Y = 2:1）で「本実装内部の一貫性」を固定し、外部解釈の
確定は Phase 3 の報告でドキュメントへ反映する。既定が誤りと判明した場合は
破壊的変更方針に従い既定値・テスト・docs を同時に更新する。

### 大出力でメモリ・時間が溢れる

スライス単位のストリーミング書き出しと `max_total_pixels` ガードで抑える。
sha256 計算・実色数再検査もスライス単位で行い、全体配列を保持しない。
上限緩和・並列化は必要が実測されてから（Phase 4 候補）。

### 往復契約（Phase 2)が convert-image-stack 側の変更を要求する

前提調査のとおり convert-image-stack はグレースケール専用。Phase 2 で
levels の RGB 拡張（破壊的変更）か往復専用読込のどちらを取るかは Phase 2
plan の決定事項とし、本フェーズは sampler 出力配列とデコード検証という
「往復の両端」を先に固定して、どちらの選択でも成立する状態を作る。
