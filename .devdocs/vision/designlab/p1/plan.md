# designlab Phase 1 実装計画 — primitive array ジェネレータ（CLIのみ）

親ロードマップ: `.devdocs/vision/designlab/roadmap.md`（Phase 1）。

## この計画の位置づけ

本計画は Phase 1 の実装だけを対象とする。designlab GUI、方式レジストリ、
実行パイプラインの自動化（`import-voxels` / `run` の呼び出し）は Phase 2 で扱う。

Phase 1 の成果物は、`vdbmat-utils` の新しいジェネレータ・サブコマンド1つである。
透明母材のブロック内に、不透明な第二材料の cube / sphere を A×B×C 個リピート配置
した material-label volume を、フラットな config JSON 1枚から決定論的に生成する。

```text
config JSON（完全フラット）
      ↓
generate-primitive-array
      ↓
<name>.voxels.json + <name>.material_id.npy
      ↓（手動CLI: Phase 1 の確認手順）
vdbmat import-voxels → vdbmat run → 既存viewerで目視確認
```

## 前提調査（確認済み事実）

### 設定・provenance・出力の既存規約

- config は `GeneratorConfig` を継承した frozen dataclass
  （`src/vdbmat_utils/core/config.py`）。canonical JSON（sorted keys、
  余白なし、NaN/Inf拒否）が configuration digest の入力であり、
  `from_json()` は未知フィールドを明示的に拒否する。`seed` は基底クラスの
  フィールドで、config digest に含まれる。
- volume の組み立ては `build_material_label_volume()`
  （`src/vdbmat_utils/core/builder.py`）が正規経路。uint16・z,y,x 順・
  palette / provenance 検証込み。
- 出力ファイルの書き出しは `src/vdbmat_utils/io/writer.py` の `write_asset()`。
  既存ジェネレータと同じ `<name>.voxels.json` + `<name>.material_id.npy` 対。
- CLI は `src/vdbmat_utils/cli/main.py` に argparse サブコマンドを追加し、
  `_cmd_*()` 関数へ dispatch する形式（`voxelize-mesh` 等と同じ）。
- 既存の実行形は `<subcommand> --config C --out DIR --name NAME`。

### 材料（vdbmat built-in）

`vdbmat.optics.config.phase0_provisional_mapping()` と
`vdbmat/src/vdbmat/fixtures/synthetic.py` で確認した built-in 材料:

| id | name | role |
|----|------|------|
| 0 | `air` | background |
| 1 | `transparent-resin` | material |
| 2 | `white-resin` | material |
| 3 | `black-opaque-resin` | material |

- `nested_material_cube` fixture は全セルが樹脂で埋まった volume でも
  palette に `air`（background）を宣言している。全埋めグリッド + air宣言の
  組み合わせが下流（`import-voxels` → `run` → mitsuba export → viewer）で
  動作することは既存デモで実証済み。
- したがって既定材料は 母材 = `transparent-resin`(1)、
  包含材 = `black-opaque-resin`(3) とし、チェックイン済み
  `phase0-provisional-materials-v1` mapping でそのまま `vdbmat run` が通る。

### サイズガードと決定論

- `voxelize-mesh` は `max_axis_cells`（既定128）と `max_total_cells`
  （既定2,000,000）でグリッド超過を拒否する。同じ形のガードを踏襲する。
- 契約テストの水準は `tests/contract/` の既存ファイル
  （payload digest 固定、double-run byte equality、seed/パラメータ感度、
  ASCII preview 固定）に合わせる（`docs/determinism.md`）。

### 破壊的変更方針との関係

Phase 1 は純追加であり、既存の config・CLI・出力契約に変更はない。
互換アーティファクトの発生余地はない。実装中に既存共通部（builder / writer /
CLI dispatch 等）の変更が必要になった場合は、roadmap の方針どおり互換shimを
作らず、呼び出し側・テストを同一フェーズ内で更新する。

## 規模判定

単一フェーズの実装計画として扱える。新規モジュール1つ、CLI 1サブコマンド、
docs 1ファイル、unit / contract テストの追加のみで、既存契約の変更を含まない。

## ゴール

1. `vdbmat-utils generate-primitive-array` が config JSON 1枚から
   決定論的に voxels 対を出力する。
2. グリッド形状は counts・size・gap・margin から導出され、手入力させない。
3. 既定材料が built-in 名に固定され、`import-voxels` → `run` が
   チェックイン済み mapping で通る。
4. 契約テストが既存ジェネレータと同水準で揃う。
5. `preview-slices` で A×B 個のプリミティブ断面が数えられる。

## 決定事項

### コマンド名とモジュール配置

- サブコマンド: `generate-primitive-array`
- モジュール: `src/vdbmat_utils/primitives/`
  - `types.py` — `PrimitiveArrayConfig`
  - `generator.py` — 生成本体 `generate_primitive_array()`
- 既存の per-generator パッケージ構成（`mesh/`、`image/`、`morph/`）に合わせる。

### config スキーマ（`PrimitiveArrayConfig`）

```text
PrimitiveArrayConfig(GeneratorConfig)
├── voxel_size_xyz_m: [float, float, float]     必須、各成分 > 0
├── primitive: "cube" | "sphere"                必須
├── counts_xyz: [int, int, int]                 必須、各成分 >= 1
├── primitive_size_m: float                     必須、> 0
│      cube: 一辺長 / sphere: 直径
├── gap_m: float = primitive_size_m と同値必須指定  >= 0
│      プリミティブ表面間の間隔（軸方向）
├── margin_m: float                             必須、>= 0
│      配列の外接箱と母材ブロック外面の間隔
├── base_material_name: str = "transparent-resin"
├── inclusion_material_name: str = "black-opaque-resin"
├── max_axis_cells: int = 256
├── max_total_cells: int = 8_000_000
└── seed: int = 0（継承。本方式は乱数を使わず、payloadへ影響しない。予約）
```

- `gap_m` は既定値を持たない必須フィールドとする（「密着(0)が既定」も
  「size と同値が既定」も自明でないため、明示させる）。`margin_m` も同様に必須。
- 材料名は `air` を除く built-in 名（`transparent-resin`、`white-resin`、
  `black-opaque-resin`）のみ受理し、base と inclusion の同名は拒否する。
  material_id は名前から built-in の既定 id（上表）を引く。GUI は Phase 2 で
  この2フィールドをドロップダウンにする。
- 任意 `local_to_world` は Phase 1 では設けない（identity 固定）。
  必要になった時点で追加する。

### グリッド導出とサンプリング規則

軸ごとの物理 extent を

```text
extent = 2 * margin_m + counts * primitive_size_m + (counts - 1) * gap_m
```

とし、セル数は `ceil(extent / voxel_size - 1e-6)`（voxelize-mesh と同じ
1e-6セルepsilon で float 丸めの余剰セルを防ぐ）。導出後に
`max_axis_cells` / `max_total_cells` ガードを適用し、超過時は voxel size を
粗くする提案つきの明示エラーとする。

セル分類は voxelizer と同じ **cell-centre サンプリング**とする。

- セル中心 `origin + (i + 0.5) * voxel_size`（origin はブロック最小角、
  local 原点 = ブロック最小角）。
- プリミティブ k（k = 0..counts-1 の3軸直積）の中心は
  `margin + size/2 + k * (size + gap)`。
- cube: `max(|p - c|_x, |p - c|_y, |p - c|_z) <= size/2`
- sphere: `‖p - c‖ <= size/2`
- 境界上（`<=`）は inside。voxelizer の closed-solid tie 規則に合わせる。
- inside ならそのセルは inclusion 材、そうでなければ base 材。air セルは
  作らない（全セルが樹脂。`nested_material_cube` と同型）。
- `gap_m = 0` で cube が密着する場合も、分類は純粋な per-cell 述語なので
  順序依存・重複塗りの問題は生じない。

実装は座標グリッドに対する numpy のベクトル化述語で行い、Python ループを
プリミティブ格子（counts）方向に限る。

### palette と provenance

- palette: `air`(0, background) + base + inclusion の3エントリ。
  air voxel は存在しないが、`nested_material_cube` と同じく宣言する。
- provenance: generator id `vdbmat-utils.primitives.array` v0.1.0。
  入力ファイルがないため sources は空。asset identity は config digest から
  導出する（詳細は既存ジェネレータの規約に合わせ実装時に確定）。
- 出力が同一入力で byte 単位に変わる変更を入れる場合は version を上げる
  （`docs/determinism.md` の既存規約）。

### CLI

```bash
uv run vdbmat-utils generate-primitive-array \
  --config primarray.json --out out/ --name demo
```

- Phase 1 では **CLI フィールド上書き（`--counts` 等）を設けない**。
  config ファイルが唯一の入力であり、GUI=CLI 再現契約（Phase 2）が
  「configファイルの受け渡し」だけで成立する状態を保つ。
- 成功時は既存ジェネレータ同様、manifest パスと材料別 voxel 数サマリを表示する。

## 対象ファイル

### 新規

- `vdbmat-utils/src/vdbmat_utils/primitives/__init__.py`
- `vdbmat-utils/src/vdbmat_utils/primitives/types.py`
- `vdbmat-utils/src/vdbmat_utils/primitives/generator.py`
- `vdbmat-utils/tests/unit/test_primitives.py`
- `vdbmat-utils/tests/contract/test_primitive_array_contract.py`
- `vdbmat-utils/docs/primitive-arrays.md`

### 変更

- `vdbmat-utils/src/vdbmat_utils/cli/main.py` — サブコマンド追加
- `vdbmat-utils/tests/unit/test_cli.py` — CLI 経路のテスト追加
- `vdbmat-utils/README.md` — コマンド一覧へ1行追加
- `README_QUICK.md` — Use Case 追記（最小限。designlab 全体の記述は Phase 2）

既存モジュールのロジック変更は想定しない。

## 実装ステップ

### Step 1 — config 契約

1. `PrimitiveArrayConfig` を frozen dataclass として定義し、
   `__post_init__` で全 validation（正値、counts >= 1、材料名の built-in 制約、
   base/inclusion 相異、ガード値の正当性）を行う。
2. 未知フィールド拒否・round-trip は基底クラスの既存機構に乗せる。
3. Mitsuba / vdbmat run を要しない unit test で契約を固定する
   （受理・拒否の境界値、canonical JSON round-trip、digest 安定性）。

### Step 2 — 生成本体

1. グリッド導出（extent → ceil + epsilon → ガード）を純関数として実装する。
2. cell-centre 述語で material_id 配列を生成する。
3. `build_material_label_volume()` + provenance で volume を組み立てる。
4. unit test: 導出 shape、inclusion voxel 数の厳密値
   （size / gap / margin が voxel size の整数倍のとき、cube は
   `A*B*C*(size/voxel)^3` に一致）、sphere の対称性（3軸の flip で payload
   不変）、境界 tie、`counts=[1,1,1]` / `gap=0` / `margin=0` の縮退ケース、
   ガード超過エラー。

### Step 3 — CLI 接続

1. `generate-primitive-array` サブコマンドと `_cmd_generate_primitive_array()`
   を追加し、`write_asset()` で出力する。
2. 成功サマリ表示・エラーの exit code を既存コマンドと揃える。
3. `test_cli.py` へ正常系・config エラー系を追加する。

### Step 4 — 契約テスト

`tests/contract/test_primitive_array_contract.py` に既存水準で固定する。

1. 代表 config（cube 3×2×1、sphere 2×2×2 の2種）の payload digest pin。
2. double-run byte equality（manifest・payload とも）。
3. ASCII preview pin: 中央 z-slice で A×B 個の断面が並ぶことを
   `preview-slices` 相当の出力で固定する。
4. パラメータ感度: `counts` / `primitive` / `primitive_size_m` の変更で
   payload digest が変わる。
5. seed 非依存: `seed` を変えても **payload digest が不変**（config digest は
   変わる）。乱数を使わない契約の明文化。

### Step 5 — docs と end-to-end 手動確認

1. `docs/primitive-arrays.md`: config 形、導出規則、サンプリング規則、
   claims / non-claims（光学テストパターンであり、印刷プロセスや材料物性の
   シミュレーションではない）を既存 docs の体裁で書く。
2. README（utils / QUICK）へ追記する。
3. 手動 walkthrough を実施し report に記録する:
   `generate-primitive-array` → `preview-slices`（個数の目視カウント）→
   `import-voxels` → `run`（phase0 mapping）→ 既存viewerで Load/Rebuild →
   A×B×C 個の不透明プリミティブが透明ブロック内に見えることの確認。
   成果物は `.local/designlab/p1/` に置き、git 管理しない。

## テスト計画

### unit（Mitsuba / vdbmat run 不要）

- config: 必須欠落、非正値、counts 0、未知フィールド、非built-in材料名、
  `air` 指定、base=inclusion、round-trip、digest 安定。
- グリッド導出: 整数倍ケースの厳密 shape、epsilon による余剰セル抑止
  （float 丸めで extent がわずかに超えるケース）、ガード超過の提案つきエラー。
- 生成: inclusion voxel 厳密数（cube）、sphere flip 対称、tie 規則、縮退
  config、dtype / 軸順 / palette 参照の妥当性（builder 検証の通過）。
- CLI: 正常系出力ファイル、config エラーの exit code とメッセージ。

### contract

Step 4 のとおり（digest pin、double-run、ASCII preview、感度、seed非依存）。

### end-to-end（手動、report記録）

Step 5-3 のとおり。自動化された `run` / viewer までの統合回帰は Phase 2
（実行パイプライン実装時）で扱い、本フェーズでは要求しない。

### 静的検査

- 変更 Python への `ruff check`
- `uv run pytest tests/unit tests/contract`（vdbmat-utils）
- `git diff --check`

## 実施順序

```text
config 契約（Step 1）
    ↓
生成本体（Step 2）
    ↓
CLI 接続（Step 3）
    ↓
契約テスト（Step 4）
    ↓
docs・手動 end-to-end（Step 5）
```

config 契約を最初に固定し、生成本体を純関数として枯らしてから CLI へ接続する。
GUI（Phase 2）に必要な形はこの時点で全て確定している状態にする。

## 非ゴール

- designlab GUI、方式レジストリ、`import-voxels` / `run` の自動実行。
- 非built-in材料、palette のカスタム、optical-mapping 出力。
- 配置の乱択・ジッタ・サイズ勾配・複数包含材・格子以外の配置。
- `local_to_world` 指定、CLI フィールド上書き。
- cube / sphere 以外のプリミティブ（cylinder 等は必要が出た時に追加。
  述語1つの追加で済む構造にはしておく）。
- sweep 対応。

## 完了条件

- `generate-primitive-array` が config JSON 1枚で決定論的に voxels 対を出力する。
- 導出 shape・inclusion 数が unit test で厳密に固定されている。
- 契約テスト（digest pin、double-run、ASCII preview、感度、seed非依存）が通る。
- 既定 config の出力が `import-voxels` → `run`（チェックイン済み phase0
  mapping、mapping ファイル追加なし）を通り、既存viewerで A×B×C 個が
  目視確認できる（手動、report記録）。
- docs / README が更新され、既存契約・既存テストに変更がない。
- 検証成果物が `.local/designlab/p1/` に隔離されている。

## リスクと方針

### float 丸めでセル数や inclusion 数が環境によりずれる

グリッド導出は ceil + 1e-6 epsilon、セル分類は `<=` の閉境界に固定し、
digest pin を「整数倍で割り切れる」代表 config と「割り切れない」config の
両方に置く。ずれが出た場合は式を変えるのではなく、まず epsilon 規則の
適用漏れを疑う（voxelize-mesh の既実装と同じ定数・同じ位置に揃える）。

### 粗い解像度で sphere が非対称・段状に見える

cell-centre サンプリングの既知の見え方であり、`nested_material_cube` の
段状境界と同種。docs の non-claims に明記し、テストは対称性
（flip 不変）で担保する。滑らかさは合否条件にしない。

### built-in 材料名のハードコードが vdbmat 側と乖離する

材料名 → id の対応表は primitives モジュール内の1定数に閉じ、unit test で
`vdbmat` の palette 検証（builder 経由）を通すことで乖離を検出する。
vdbmat 側の built-in が変わった場合は、破壊的変更方針に従い本モジュールの
定数・テスト・docs を同時に更新する（互換テーブルを残さない）。

### 「数えられる」ASCII preview が大きい counts で崩れる

契約テストの preview pin は小さい counts（3×2×1 等）に限定する。
大きい counts の検証は voxel 数の厳密値テストが担う。

### Phase 2 で config へフィールド追加が必要になる

`from_json()` の未知フィールド拒否により、旧configの黙殺は起きない。
追加が必要になった場合は Phase 2 の plan で扱い、既定値つき追加でも
digest が変わることを contract の pin 更新として明示的に扱う。
