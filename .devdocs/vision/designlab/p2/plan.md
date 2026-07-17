# designlab Phase 2 実装計画 — designlab GUI最小成立（primitive array 1方式）

親ロードマップ: `.devdocs/vision/designlab/roadmap.md`（Phase 2）。

## この計画の位置づけ

本計画は Phase 2 の実装だけを対象とする。フォーム → config save/load →
一括実行 → 既存viewerでの確認、という動線全体を primitive array 1方式で
端から端まで成立させ、方式レジストリの骨格を確立する。2方式目以降、
入力アセットを取る方式、viewerとの自動連携、designlab内レンダリングは
Phase 3 以降の対象である。

```text
方式選択（当面 primitive array のみ）
      ↓
フォーム穴埋め（PrimitiveArrayConfig の全フィールド）
      ↓                     ↕ save / load（--config-root 配下の *.primarray.json）
Generate（background job 1本）
      validate → generate → map → verify → publish
      ↓
--output-root/<method>-<name>-<digest12>/  … canonical run bundle
      ↓（疎結合: rootを共有するだけ）
既存viewer（--input-root = --output-root）で Refresh + Load/Rebuild
```

## 前提調査（確認済み事実）

### 実行環境とパッケージ境界

- `vdbmat-utils` の venv には vdbmat が editable path 依存として入っている
  （`vdbmat-utils/pyproject.toml` の `tool.uv.sources`）。`vdbmat-utils` と
  `vdbmat` 両方の CLI が同一 venv で使えるため、サブプロセスは
  `sys.executable -m vdbmat_utils.cli.main ...` / `sys.executable -m
  vdbmat.cli.main ...` の形で PATH 非依存に呼べる。
- viser 依存 group の前例は vdbmat 側の `mitsuba-viewer`（`viser>=0.2`）。
  vdbmat-utils には GUI 系 group がまだ無い。
- vdbmat の viewer 回帰テスト
  （`tests/integration/test_mitsuba_stage_viewer_regression.py`）は
  `sys.path.insert` で examples ディレクトリを import し、ブラウザなしで
  core 層を直接駆動する。examples 配下アプリのテスト手法として前例がある。
- vdbmat-utils の `tests/integration/` には「pinned vdbmat CLI を end-to-end
  で呼ぶ」marker と前例（`test_vdbmat_cli.py`、`test_import_voxels.py` 等）
  がある。

### canonical bundle 生成経路

- `vdbmat.pipeline-config` 2.0.0 の入力は direct-voxel（`.voxels.json`）のみ
  （ADR-009 D1）。`vdbmat run` は load / validate-material /
  **persist-material** / map-optics / validate-optical / persist-optical /
  summarize を1回の実行で行い、bundle（`run.json` / `source/` /
  `material.zarr` / `optical.zarr`）を出力する。
  **単独の `import-voxels` 実行は bundle 生成に寄与しない**（p1 report5 の
  手順3は動作確認であって、その出力 zarr を run が参照することはない）。
- mapping は builtin 名 `phase0-provisional-materials-v1` を `mapping.name`
  で参照すれば I/O なしで resolve され、digest は `PipelineConfig` が自動
  計算する（`vdbmat/src/vdbmat/pipeline/config.py`）。run.json に digest を
  ハードコードする必要はない。
- `run_pipeline()` は出力先の sibling `.{name}.tmp-{run_id}` で組み立てて
  atomic rename で発行する（ADR-007 D7/D8）。失敗時は tmp ディレクトリが
  残るだけで、最終パスに部分成果物は現れない。
- run config 内の相対パス（`input.path` / `output.path`）は config ファイル
  の位置を基準に解決される。

### viewer 側公開契約（designlab が依存してよい範囲）

- Input カタログは「`run.json` と `optical.zarr` を持つディレクトリ」を
  run bundle として検出し、root を `os.walk` で走査する。
  **dot-directory を除外しない**ため、output root 配下に作業ディレクトリを
  置くと途中成果物がカタログに出うる。作業領域は output root の外に置く
  必要がある。resolved path が root を離脱する候補（symlink）は除外される。
- containment 規約: `path.resolve()` が root と一致するか
  `is_relative_to(root)`。
- STAGE 表示: status 行の段階語と、stdout の
  `STAGE <transaction> <stage> <elapsed_s>` 行。

### Phase 1 の成果（GUI 前提）

- `PrimitiveArrayConfig` は完全フラット、CLI フィールド上書きなし、config
  ファイルが唯一の入力（`vdbmat-utils/docs/primitive-arrays.md`）。GUI=CLI
  再現契約は「同じ config ファイルを CLI へ渡す」に還元される。
- 材料候補は `vdbmat_utils.primitives.types.BUILTIN_MATERIAL_IDS`
  （`transparent-resin` / `white-resin` / `black-opaque-resin`）。p1 plan で
  「Phase 2 でドロップダウン化する」と予告済み。
- config 契約 API は `GeneratorConfig.to_json()`（canonical JSON）、
  `from_json()`（未知フィールド拒否）、`config_digest()`（`sha256:...`）。
- 既定 config の出力が `vdbmat run`（builtin mapping、mapping ファイル追加
  なし）を通ることは p1 手動 walkthrough で実証済み。

### 開発環境の制約

- 本開発環境はブラウザを操作できない（p1 / mitsubagui p5 と同じ制約）。
  GUI 層の自動テストは行わず、browser-free な core 層のテストと、人間による
  ブラウザ確認手順の提示で代替する。

## 規模判定

単一フェーズの実装計画として扱える。新規は examples アプリ1式、
dependency-group 1つ、docs 1ファイル、unit / integration テストの追加のみで、
既存の generator / CLI / bundle 契約に変更はない（`pyproject.toml` への
group 追加を除き、既存ファイルのロジック変更なし）。

## ゴール

1. `designlab` viser アプリが、フォーム穴埋めだけで検証済み canonical bundle
   を `--output-root` へ atomic に発行する。
2. config save → load → 再実行で同一 payload digest になる（GUI=CLI 再現
   契約のテスト固定）。
3. 実行失敗（不正パラメータ、サイズガード超過、発行先衝突）で output root
   に部分成果物が残らず、失敗段階が status に表示される。
4. 方式レジストリのインターフェースが定義・文書化され、2方式目の追加手順が
   README レベルで書ける状態になる。
5. 発行された bundle が既存 viewer の Input カタログに現れ、Load/Rebuild で
   目視確認できる。

## 決定事項

### 配置と依存

- アプリ配置: `vdbmat-utils/examples/designlab/`。生成・bundle 化・発行の
  全段が vdbmat-utils の venv で完結する（vdbmat CLI も同 venv にある）ため、
  viewer が `vdbmat/examples/` にあるのと対称に utils 側へ置く。
- `vdbmat-utils/pyproject.toml` に dependency-group
  `designlab = ["viser>=0.2"]` を追加する（バージョン制約は vdbmat の
  `mitsuba-viewer` group と揃える）。
- 起動:

  ```bash
  cd vdbmat-utils
  uv run --group designlab python examples/designlab/designlab_app.py -- \
    --config-root <CONFIG_ROOT> \
    --output-root <OUTPUT_ROOT> \
    [--work-root <WORK_ROOT>] [--port 8081]
  ```

- module 分割は viewer と同じ「GUI 薄皮 + browser-free core」:
  - `designlab_app.py` — viser 結線・起動引数処理（薄皮。自動テスト対象外）
  - `designlab_registry.py` — `GeneratorMethod` インターフェースと
    レジストリ、primitive array の登録
  - `designlab_configs.py` — config カタログ
    （scan / refresh / save / load / containment）
  - `designlab_pipeline.py` — 一括実行ジョブ
    （stage 進行、run.json 組み立て、atomic publish）
  - `designlab_jobs.py` — 単一 worker thread によるジョブ直列化
  - ファイル数は目安であり、実装時の統合・分割は許す（GUI 薄皮と core の
    分離だけは崩さない）。
- designlab は `vdbmat_utils` の config 契約（`PrimitiveArrayConfig`、
  `config_digest()` 等）を直接 import してよい。ただし生成と optical mapping
  の**実行**は必ずサブプロセス CLI 経由とする（roadmap のパッケージ境界）。
  vdbmat viewer の module（`mitsuba_stage_*`）は import しない。

### 方式レジストリ（最小骨格）

`GeneratorMethod` を frozen dataclass（または Protocol）として定義する。

```text
GeneratorMethod
├── method_id: str            # "primitive-array"。発行名・表示に使う
├── title: str                # ドロップダウン表示名
├── config_suffix: str        # ".primarray.json"。カタログの方式判別に使う
├── config_cls: type[GeneratorConfig]
├── build_form(gui) -> FormBinding      # viser widget 群の構築
├── form_to_config(values) -> GeneratorConfig
│        # 失敗はフィールド名つき例外（config __post_init__ のエラーを透過）
├── config_to_form(config) -> None      # load 時のフォーム反映
└── generator_argv(config_path, out_dir, name) -> list[str]
         # [sys.executable, "-m", "vdbmat_utils.cli.main",
         #  "generate-primitive-array", "--config", ..., "--out", ..., "--name", ...]
```

- レジストリは module レベルの tuple 1つ。方式ドロップダウンはその列挙で、
  登録は当面 primitive array の1件。
- config スキーマ → フォームの自動生成はしない（roadmap のリスク方針
  どおり、Phase 4 完了までは方式ごとの手書きフォーム定義）。

### primitive array フォーム

`PrimitiveArrayConfig` は全フィールドがフラットなスカラー/三つ組なので、
JSON テキスト編集とのハイブリッドは本方式では不要（全フィールドを
フォームで表現する）。

| config フィールド | widget |
|---|---|
| `voxel_size_xyz_m` | number 入力 ×3 |
| `primitive` | dropdown（`cube` / `sphere`） |
| `counts_xyz` | int 入力 ×3 |
| `primitive_size_m` / `gap_m` / `margin_m` | number 入力 |
| `base_material_name` / `inclusion_material_name` | dropdown（`BUILTIN_MATERIAL_IDS` のキー） |
| `max_axis_cells` / `max_total_cells` / `seed` | Advanced folder 内の int 入力 |

フォームとは別に、ジョブ入力として **name**（asset 名・発行名の一部）を
取る。`[a-z0-9][a-z0-9-]*` に制限し、validate 段で検査する。name は config
の一部ではない（既存 CLI の `--name` と同じ位置づけ）。

### config save / load

- カタログ: `--config-root` 配下（再帰）の、登録方式の `config_suffix` に
  一致するファイル（当面 `*.primarray.json`）。dropdown + Refresh。
  containment は viewer と同規則（resolve + `is_relative_to`、symlink での
  root 離脱は除外・拒否）。ブラウザからの upload はしない。
- Load: `from_json()` でパースし、未知フィールド拒否等のエラーはそのまま
  status へ表示する（メッセージの再解釈をしない）。成功時にフォームへ反映。
- Save: フォーム → config → `to_json()`（canonical）で
  `--config-root/<入力名>.primarray.json` へ書く。**既存ファイルへの上書きは
  拒否**する（roadmap 共通非ゴール「既存 config の破壊的上書き」。明示
  エラーでファイル名を変えるよう案内する）。
- GUI だけに存在する永続状態は作らない。保存対象は config JSON のみ。

### 実行パイプライン（STAGE 語彙と各段）

STAGE 語彙は `validate → generate → map → verify → publish` とする。

roadmap のスケッチは `validate → generate → import → map → publish` だが、
ADR-009 D1 により canonical bundle は `vdbmat run` が direct-voxel manifest
を直接 consume し、persist-material 段で `material.zarr` を自ら生成する。
単独の `import-voxels` 呼び出しは「bundle が参照しない中間 zarr」を増やす
だけなので、独立の段として置かず `map` 段へ吸収する。roadmap 方針
（後方互換のためだけのアーティファクトを残さない）に沿った逸脱として
ここに記録する。

ジョブの work dir を `W` とすると:

1. **validate** — フォーム → `form_to_config()`（config validation を透過）、
   name 検査、roots の存在・containment 検査、発行先衝突チェック
   （下記「発行規則」）。configのcanonical JSONを `W/<name>.primarray.json`
   へ書く（Save 済みファイルと同一内容になることが canonical 化で保証
   される）。
2. **generate** — サブプロセス
   `vdbmat-utils generate-primitive-array --config W/<name>.primarray.json
   --out W --name <name>`。
3. **map** — `W/run.json` を組み立てて（`input.kind = "direct-voxel"`、
   `input.path = "<name>.voxels.json"`、
   `mapping = {"name": "phase0-provisional-materials-v1"}`、
   `output = {"path": "bundle", "overwrite": false}`、
   `execution.random_seed = 0`）サブプロセス `vdbmat run W/run.json`。
4. **verify** — サブプロセス `vdbmat validate W/bundle --json` が ok。
5. **publish** — `os.replace(W/bundle, 発行先)`。

- 各段は viewer と同形式の `STAGE <transaction> <stage> <elapsed_s>` 行を
  stdout へ出し、GUI status 行に段階名と経過を表示する。
- 失敗時は失敗段の名前と、サブプロセスの stderr 末尾を**再解釈せずに**
  表示する（roadmap 方針。CLI のエラーが不親切ならCLI側を直す）。

### 発行規則

- 発行名: `<method_id>-<name>-<config_digest 先頭12hex>`
  （例 `primitive-array-demo-3fa9c2d81b04`）。roadmap の
  「方式名 + config digest」命名規約に従い、手動削除可能な単位にする。
- 発行先が既に存在する場合（validate 段で検出。config digest は config
  だけから計算できるため生成前に判定できる）:
  - 既存が有効な bundle（`run.json` + `optical.zarr` を持つ）なら、生成を
    スキップし「発行済み bundle を再利用」として成功終了する（決定論的
    generator + 同一 mapping なので科学的内容は同一）。
  - 無効（部分成果物等）なら明示エラーとし、手動削除を案内する。
    **output root 内の自動削除・自動上書きは一切しない。**
- work root: `--work-root`。既定は `--output-root` の sibling
  `<basename>.designlab-work`。**output root 配下は拒否する**
  （viewer カタログが dot-directory も走査するため）。`os.replace` が
  cross-device（EXDEV）で失敗した場合は、output root と同一 filesystem の
  `--work-root` を指定するよう明示エラーで案内する。
- ジョブ work dir は `<work-root>/<NNN>-<name>/`。成功時に自ジョブの
  work dir を削除し、失敗時は調査用に残す。次回起動時に自 work root の
  stale entry を sweep する（viewer の cleanup 規則を踏襲。sweep 対象は
  自分の work root のみ）。

### ジョブ直列化

worker thread 1本にジョブを直列化する。実行中に Generate が押された場合は
拒否して status に表示する。cancel は作らない（viewer と同じく、STAGE の
実測データが揃ってから採否を判断する。Phase 1 級の入力では generate も
run も数秒以内であることを p1 で確認済み）。

### GUI=CLI 再現契約（Phase 2 での定義）

GUI が保存した config `C` と name `N` について、

```bash
uv run vdbmat-utils generate-primitive-array --config C --out D --name N
```

が出力する `N.material_id.npy` の sha256 が、designlab が発行した bundle の
`source/` 内 manifest に記録された payload sha256 と一致すること。
integration test で固定する。

## 対象ファイル

### 新規

- `vdbmat-utils/examples/designlab/designlab_app.py`
- `vdbmat-utils/examples/designlab/designlab_registry.py`
- `vdbmat-utils/examples/designlab/designlab_configs.py`
- `vdbmat-utils/examples/designlab/designlab_pipeline.py`
- `vdbmat-utils/examples/designlab/designlab_jobs.py`
- `vdbmat-utils/tests/unit/test_designlab_registry.py`
- `vdbmat-utils/tests/unit/test_designlab_configs.py`
- `vdbmat-utils/tests/unit/test_designlab_pipeline_unit.py`
- `vdbmat-utils/tests/integration/test_designlab_pipeline.py`
- `vdbmat-utils/docs/designlab.md`

（テストファイルの分割は実装時に整理してよい。examples module は viewer と
同水準の型注釈で書き、テストからは viewer 回帰テストと同じ
`sys.path.insert` パターンで import する。）

### 変更

- `vdbmat-utils/pyproject.toml` — dependency-group `designlab` 追加
- `vdbmat-utils/README.md` — designlab アプリの節を追加
- `README_QUICK.md` — designlab の Use Case を追加
  （p1 report5 で「designlab GUI 全体の記述は Phase 2」と繰り延べた分）

既存 module のロジック変更は想定しない。

## 実装ステップ

### Step 1 — 方式レジストリと config カタログ（browser-free）

1. `GeneratorMethod` インターフェースとレジストリを定義し、primitive array
   を登録する（フォーム構築は callable の骨組みだけ置き、結線は Step 3）。
   `generator_argv()` までをここで確定する。
2. config カタログ: scan / refresh / containment / load（エラー透過）/
   save（canonical 書き出し、上書き拒否）。
3. unit test: レジストリ列挙、argv golden、カタログ検出、containment 離脱
   拒否、save 上書き拒否、load → config → save の round-trip で
   `config_digest` が不変、未知フィールド config のエラー透過。

### Step 2 — 実行パイプライン core（browser-free）

1. run.json 組み立て（golden で固定）、発行名導出、STAGE 進行、
   サブプロセス実行、verify、atomic publish、reuse / 衝突 / EXDEV の分岐、
   work dir cleanup 規則を実装する。ジョブ直列化（`designlab_jobs.py`）も
   ここで入れる（GUI なしで駆動できる形）。
2. unit test: run.json golden、発行名、衝突分岐（有効 = reuse / 無効 =
   エラー）、work-root が output-root 配下のとき拒否。
3. integration test（tiny config、`integration` marker）:
   - happy path: 発行された bundle が `run.json` + `optical.zarr` を持つ
     （viewer 検出契約）こと、`vdbmat validate` が ok なこと。
   - GUI=CLI 再現契約: 保存 config の CLI 再実行で payload sha256 一致。
   - 失敗時非発行: サイズガード超過 config で generate 段が失敗し、
     output root に何も現れないこと。
   - 再発行: 同一 config の2回目が reuse で成功すること。

### Step 3 — viser GUI 結線

1. `designlab_app.py`: 起動引数（`--config-root` / `--output-root` /
   `--work-root` / `--port`）、方式ドロップダウン、primitive array フォーム、
   config カタログ（dropdown + Refresh + Load / Save）、name 入力、
   Generate ボタン、status 行（STAGE 進行・失敗段・発行結果パス）。
2. 起動時チェック: roots の存在と containment 前提、`vdbmat_utils` /
   `vdbmat` の import 可否（venv 取り違え検出）を確認し、不備は起動エラー
   で案内する。
3. viser API は viewer（`mitsuba_stage_viewer.py`）で使用済みの範囲に
   限定する。GUI 層の自動テストはしない（core 層で担保。理由は前提調査の
   環境制約のとおり）。

### Step 4 — docs と end-to-end 確認

1. `docs/designlab.md`: 起動方法、フォームと config の対応、STAGE 語彙、
   発行・cleanup 規則、GUI=CLI 再現契約、**レジストリのインターフェースと
   2方式目（voxelize-mesh を想定）の追加手順**（roadmap 完了条件の
   「README レベルで書ける」に対応）。
2. `vdbmat-utils/README.md` / `README_QUICK.md` を更新する。
3. 手動 walkthrough を実施し report に記録する（成果物は
   `.local/designlab/p2/`、git 管理しない）:
   - scripted: pipeline core を直接呼んで発行 → viewer 側の
     カタログ検出・Load/Rebuild 相当を p1/p5 と同じ代替経路
     （viewer core のスクリプト駆動 / headless レンダー）で確認する。
   - human向け: 起動コマンドを提示し、ブラウザでフォーム → Generate →
     既存 viewer での Refresh + Load/Rebuild 確認を依頼する
     （本環境ではブラウザ操作ができないため）。

各 Step の完了時に p1 と同様 `.devdocs/vision/designlab/p2/reportN.md` を
記録する。

## テスト計画

### unit（viser・サブプロセス不要）

- レジストリ: 列挙、`config_suffix` 対応、`generator_argv` golden。
- config カタログ: 検出、containment（symlink 離脱含む）、上書き拒否、
  round-trip digest 不変、config エラーの透過。
- パイプライン: run.json golden、発行名導出、衝突・reuse・EXDEV・
  work-root 配置の分岐。

### integration（サブプロセス CLI、`integration` marker）

Step 2-3 のとおり（happy path / GUI=CLI digest 一致 / 失敗時非発行 /
reuse）。入力は数秒で終わる tiny config に限る。

### GUI 層

自動テストなし（thin binding に保つ）。core 直呼びで全動線を担保する
方針は viewer 回帰テストの前例に合わせる。

### 静的検査

- 変更 Python への `ruff check`（examples 含む）
- `uv run pytest tests/unit tests/contract tests/integration`（vdbmat-utils。
  既存テストが無変更で pass することを含む）
- `git diff --check`
- mypy は現行構成（`src` / `tests` 対象）に従う。examples は viewer と同じく
  ruff のみを必須とする。

## 実施順序

```text
Step 1: レジストリ + config カタログ（browser-free）
    ↓
Step 2: 実行パイプライン core + integration テスト（browser-free）
    ↓
Step 3: viser GUI 結線
    ↓
Step 4: docs・手動 end-to-end・report
```

browser-free な層で契約（レジストリ、round-trip、STAGE、発行規則、
GUI=CLI 再現）を先に枯らし、GUI は最後に薄く結線する。Step 2 完了時点で
Phase 3 以降が依存する骨格は全て確定している状態にする。

## 非ゴール

- 2方式目以降の登録（voxelize-mesh は Phase 3）。
- 入力アセット（ファイル/ディレクトリ）カタログ。
- viewer への自動通知・自動リロード（root 共有の疎結合のみ）。
- designlab 内でのレンダリングプレビュー。
- フォームの自動生成（Phase 5 以降に実測差分で判断）。
- config JSON テキスト編集ハイブリッド（primitive array は全フィールドが
  フォーム化可能。ハイブリッドは Phase 5 の generate-formation で導入）。
- ジョブの cancel・並列実行。
- 発行済み bundle の世代管理・cleanup（Phase 6）。
- headless 一括実行 CLI（テストと検証は core 関数の直接呼び出しで足りる。
  必要が確認されたら以降のフェーズで扱う）。
- リモート公開、認証、複数ユーザー同時編集。

## 完了条件

- フォーム穴埋め → Generate で、`--output-root` へ
  `primitive-array-<name>-<digest12>` の canonical bundle が atomic に
  発行される。
- 発行 bundle が viewer の検出契約（`run.json` + `optical.zarr`）を満たす
  ことが integration test で固定され、viewer（本環境では p1 同様の代替
  経路）での目視確認が report に記録されている。
- GUI が保存した config の CLI 再実行で payload sha256 が一致することが
  integration test で固定されている。
- 不正パラメータ・サイズガード超過・発行先衝突・EXDEV の失敗で output root
  が汚れず、失敗段階が status に表示されることがテストで固定されている。
- レジストリのインターフェースと2方式目の追加手順が `docs/designlab.md` に
  文書化されている。
- 既存テストが無変更で pass し、検証成果物が `.local/designlab/p2/` に
  隔離されている。

## リスクと方針

### viser API の使い方が viewer と乖離する

viewer で使用実績のある API 範囲（folder / dropdown / number / button /
markdown status）に限定する。挙動に迷ったら viewer の実装を**参照**する
（import はしない）。

### サブプロセスが別 venv で走る事故

`sys.executable -m ...` 形式で自 venv の interpreter を固定し、起動時に
`vdbmat_utils` / `vdbmat` の import 可否を検査して、`uv run --group
designlab` での起動を促すエラーを出す。

### `os.replace` の cross-device 失敗

既定 work root を output root の sibling にすることで通常は発生しない。
発生時は同一 filesystem の `--work-root` を案内する明示エラーとする
（黙って copy へフォールバックしない — atomic 発行の保証を優先する）。

### 生成・mapping が重く GUI が固まって見える

ジョブは worker 1本に直列化し、STAGE 進行と経過秒を表示する。実行中の
Generate は拒否する。cancel は STAGE 実測が閾値（viewer の判断と同じ
~30秒）を超えるのを確認してから個別に計画する。

### output root にゴミが蓄積する

work root 分離 + 検証後 atomic publish + 「衝突時は reuse か明示エラー」で、
output root には完成 bundle 以外を置かない。`run_pipeline()` 由来の
`.tmp-*` / `.bak-*` は work dir 内にしか生じず、work dir ごと cleanup
される。

### roadmap 記載の `import` 段との差分

決定事項に記録済み（`map` 段へ吸収、理由は ADR-009 D1）。Phase 2 の report
に結果を残し、必要なら roadmap のスケッチ側を同一フェーズ内で追随修正する
（破壊的変更方針の「同一フェーズで一本化」に従う）。

### config 上書き拒否が編集ループの摩擦になる

Phase 2 は roadmap の非破壊規約を優先する。実運用で摩擦が確認されたら
Phase 6（世代管理）で versioned save 等を検討し、本フェーズでは緩めない。

### 発行名の digest が config 微修正のたびに増殖する

想定どおりの挙動（手動削除可能な命名の対価）。蓄積の整理は Phase 6 の
世代管理の対象であり、本フェーズでは docs に「digest 違いは別 bundle」と
明記するに留める。
