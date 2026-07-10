# Phase 1-side1 実装計画 — Material & Input Contract Extensibility

対象: `.local/roadmap.md` の「Phase 1-side1」。Phase 1 完了時点のコードベース
(`src/vbdmat/`) を前提に、入力境界と材料係数マッピングを拡張可能にする。
忠実度(fidelity)向上は一切含まない。

## 現状把握(2026-07 時点)

- コアパイプライン (`pipeline/config.py`, `pipeline/runner.py`) は
  `InputKind.DIRECT_VOXEL`(`vbdmat.voxels` マニフェスト、ADR-006)と
  `InputKind.MESH`(STL → `voxelize/mesh.py`)の 2 入力を受け付ける。
- CLI (`cli/main.py`) に `voxelize` サブコマンドがあり、STL 直接処理を露出している。
- 光学マッピングは `pipeline/config.py` の `_BUILTIN_MAPPINGS` にハードコードされた
  `phase0-provisional-materials-v1` のみ(`optics/config.py` の
  `phase0_provisional_mapping()`)。`mapping_name` で名前参照 + digest 照合する仕組みは
  既にあるが、外部データからの読み込み手段がない。
- マッピングとパレットの照合は `material_id`(整数)のみで行われ、名前
  (`materials[].name`)や `external_id` は照合に使われていない。
  マニフェストの `external_id` は将来の物理プリンタ材料カタログ用として既に
  分離フィールドになっている(ADR-006)。

## ゴール(exit criteria の言い換え)

1. コアパイプラインの入力は `vbdmat.voxels` マニフェストのみ。
2. メッシュボクセル化はコアから削除する。外部ツール化(`vbdmat-voxelize`)は
   **本フェーズでは実装しない**。実装に必要な知見は
   `.local/memo_stltovoxel.md` に保全済み(roadmap の「exists (if at all)」に該当)。
3. 材料係数マッピングはコード変更なしに差し替え可能(外部 JSON)。
4. メッシュ以外の外部ジェネレータが最低 1 つ、契約を end-to-end で実証する
   (メッシュツールを延期するため、これが唯一の契約実証ジェネレータになる)。
5. シミュレーション側の材料名/パレット契約と物理プリンタ材料カタログ
   (`external_id`)の区別が文書として形式化される。

## 作業ステップ

### Step 1 — ADR-009: 入力ジェネレータ契約と材料マッピング外部化の決定記録

- `docs/adr/0009-input-generator-contract-and-external-mappings.md` を新規作成。
- 決定事項:
  - D1: コアパイプラインの唯一の入力は `vbdmat.voxels` マニフェスト。
    `input.kind` は `direct-voxel` のみ(スキーマ major は据え置き可か判断 →
    `vbdmat.pipeline-config` は破壊的変更なので **2.0.0** に上げる)。
  - D2: 「入力ジェネレータ契約」= ADR-006 マニフェストを正とし、ジェネレータ側の
    義務(units 明示、sha256、`source.generator{,_version}`、パレット宣言)を明文化。
  - D3: 材料係数マッピングの外部ファイル形式(`vbdmat.optical-mapping` JSON、
    下記 Step 3)と、ビルトイン名参照との共存・digest による再現性担保。
  - D4: 材料識別の二層構造 —— シミュレーション側契約は
    `material_id`(照合キー)+ `name`(人間可読・パレットとマッピングで一致検証)。
    物理カタログは `external_id` に隔離し、光学マッピングの照合には使わない。

### Step 2 — コア入力を voxel マニフェストに限定

- **後方互換は考慮しない(破壊的変更前提)**。旧 config の救済・案内は行わず、
  未知キー/未知値として通常の検証エラーで落ちれば十分。
- `pipeline/config.py`:
  - `InputKind.MESH` と `MeshVoxelizationSettings` を削除。
    `PIPELINE_CONFIG_SCHEMA` を `2.0.0` へ。`input.voxelization` は
    未知キーとして自然に拒否される(専用エラーは作らない)。
  - `input.kind` は当面 `direct-voxel` 固定(将来拡張余地として enum は残す)。
- `pipeline/runner.py`: `_load_mesh` 分岐、`read_stl` / `voxelize_mesh` import、
  voxelization provenance 記録を削除。ソース保全はマニフェスト+payload コピーのみに。
- `cli/main.py`: `voxelize` サブコマンドを削除。
- テスト更新: `tests/pipeline/test_pipeline_config.py`,
  `test_pipeline_runner.py`, `tests/cli/test_cli.py`,
  `tests/integration/test_phase1_end_to_end.py` から mesh 入力ケースを削除。

### Step 3 — 材料係数マッピングのプラガブル化

- 新形式 `vbdmat.optical-mapping` v1(JSON、`docs/schemas/` に仕様追加):
  - `format`, `format_version`, `configuration_id`, `version`,
    `optical_basis`, `mixing_rule`, `calibration_status`, `materials[]`
    (`material_id`, `name`, `sigma_a_rgb_per_m`, `sigma_s_rgb_per_m`, `g`, `ior`)。
  - 既存 `OpticalMappingConfig.canonical_json()` とフィールドを一致させ、
    digest が形式に依らず安定するようにする。
- `optics/` に `load_optical_mapping(path) -> OpticalMappingConfig` を追加
  (voxel_manifest.py と同様の strict reader: 未知キー拒否、単位・範囲検証)。
- `pipeline/config.py`:
  - `mapping_name`(ビルトイン参照)に加え `mapping_path` を追加(排他)。
  - `mapping.digest` は外部ファイル使用時は **必須** とし、ロード結果と照合
    (パス自体は scientific digest から除外、digest は含める —— ADR-007 D3 と同型)。
  - `resolve_mapping()` を base_dir を取る形に整理(パス解決は runner 側で明示)。
- `phase0-provisional-materials-v1` はビルトインとして残し、同内容の外部 JSON を
  `examples/` に置いて digest 一致をテストで担保。
- CLI: `convert` 系コマンドに `--mapping-file` を追加。
- テスト: `tests/optics/test_mapping_loader.py`(正常系 / 各フィールド異常系 /
  digest 不一致 / ビルトインとの等価性)、pipeline config の排他・digest 検証。

### Step 4 — メッシュボクセル化コードの削除と知見保全(ツール化は延期)

- 外部ツール `vbdmat-voxelize` の実装は **本フェーズでは行わない**(別の機会に実施)。
  代わりに、実装に有用な情報を `.local/memo_stltovoxel.md` に集約済み:
  アルゴリズム要点(winding 判定・ジッタ・ドメインスナップ・規模上限)、
  トポロジ検証手順、STL リーダの判定規則、将来のツール設計方針、移設すべきテスト。
- コア側 `src/vbdmat/voxelize/`, `src/vbdmat/io/mesh.py` と
  `tests/voxelize/`・関連 unit テストを削除(実装は git 履歴に残る。
  削除コミットのハッシュを memo に追記する)。
- マニフェスト書き出しヘルパ `write_material_label_manifest()` は
  ジェネレータ共通で必要なので `vbdmat.io.voxel_manifest` に追加する
  (Step 5 のジェネレータと将来のメッシュツールの双方が使う)。

### Step 5 — 外部ジェネレータ(契約の end-to-end 実証)

- メッシュツールを延期するため、これが exit criteria の「外部ジェネレータによる
  契約実証」を担う唯一の実装になる。roadmap の例から最小コストのものを選ぶ:
  **層状 3D 画像スタッキング**(PNG/グレースケール画像列 → 閾値/パレット割当 →
  マニフェスト)を `tools/vbdmat-stack/`(または
  `examples/generators/image_stack/`)に実装。
  画像 I/O は Pillow のみ、~200 行規模で契約実証には十分。
- 統合テスト: 合成画像列 → マニフェスト → コアパイプライン → optical.zarr まで
  通し、材料分率保存の解析的チェックを再利用。

### Step 6 — 材料契約の文書化と検証強化

- `docs/` に「material identity contract」文書を追加(ADR-009 の D4 を展開):
  - パレット(`material_id` + `name` + `role`)= シミュレーション側契約。
  - 光学マッピングとの照合は `material_id`。加えて **name 不一致を警告 or
    エラーにする検証** を `optics/mapping.py` の palette 照合に追加
    (現在は ID のみ照合 → 名前ずれが黙って通る問題の是正)。
  - `external_id` は光学マッピングに現れてはならないことを明記し、
    マッピング形式のスキーマでも `external_id` キーを拒否。
- README / README_EXTEND.md の入力・拡張手順を更新。

### Step 7 — 仕上げ

- `examples/phase1/generate_*` スクリプトと reference baseline を新契約で再生成し、
  scientific digest が(マッピング内容不変なら)変わらないことを確認。
- `docs/phase1-research-mvp-report.md` 系に side-mission の完了記録を追記。
- 全テスト + lint + type check、`/verify` 相当の end-to-end 実行
  (両ジェネレータ → convert → export)。

## 実施順序と依存

Step 1 (ADR) → Step 2 と Step 3 は独立に並行可 → Step 4(削除+ヘルパ追加)は
Step 2 の後 → Step 5 は Step 4 のヘルパに依存するのでその後 →
Step 6 は Step 3 以降いつでも → Step 7 最後。

## リスク・判断点

- **STL 入力手段の一時的な空白**: メッシュツール延期により、本フェーズ完了後は
  STL からマニフェストを作る公式手段が存在しない(git 履歴 +
  `.local/memo_stltovoxel.md` のみ)。STL 由来のデモ・fixture が必要になった時点で
  ツール実装を着手するトリガーとする。既存の STL 由来 fixture / baseline は
  削除前に一度マニフェスト化して保存しておくと再生成に困らない(Step 4 で実施)。

- **pipeline-config major bump (2.0.0)**: 既存の保存済み config.json は読めなくなる。
  後方互換は不要という前提なので移行策は設けない。ADR-009 で決定として残す。
- **外部マッピングの digest 必須化**: 利便性は下がるが再現性 > 利便性
  (ADR-007 の思想)。CLI に digest を計算表示するヘルパ(`vbdmat mapping-digest`
  等)を足すと運用が楽になる —— Step 3 に小項目として含める。
- **ツールの配布形態**: 当面は同一リポジトリ内サブパッケージ。uv workspace 化は
  必要になってから(Phase 7 の判断に委ねる)。
- **name 照合の厳格度**: 破壊的変更前提なので最初からエラーとし、
  不一致を含む既存 fixture は修正する。
