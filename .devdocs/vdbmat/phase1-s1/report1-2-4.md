# Phase 1-side1 実装報告 — Step 1, 2, 4

対象計画: `.local/phase1-s1/plan.md`(破壊的変更前提に調整済み)
実施日: 2026-07-04

## 実施範囲

計画の Step 1(ADR-009)、Step 2(コア入力の voxel マニフェスト限定)、
Step 4(mesh コード削除+マニフェスト書き出しヘルパ)を完了した。
Step 3(マッピングのプラガブル化)、Step 5(第 2 ジェネレータ)、
Step 6(材料契約文書+name 照合)、Step 7(baseline 再生成)は未着手。

## Step 1 — ADR-009

- `docs/adr/0009-input-generator-contract-and-external-mappings.md` を新規作成。
  決定: D1(voxel マニフェストが唯一のコア入力、pipeline-config 2.0.0、
  後方互換なし)、D2(入力ジェネレータ契約と writer ヘルパの依存方向)、
  D3(外部マッピング形式と digest 必須 — **実装は Step 3**)、
  D4(material_id+name のシミュレーション契約 / external_id の物理カタログの二層分離
  — **name 照合の実装は Step 6**)。
- `docs/adr/0006` のヘッダに「mesh 入力節は ADR-009 により supersede」の注記を追加。

## Step 2 — コア入力の限定(破壊的変更)

- `pipeline/config.py`: `InputKind.MESH`・`MeshVoxelizationSettings`・
  `voxelization` フィールドを削除。`PIPELINE_CONFIG_SCHEMA` を **2.0.0** に bump。
  v1 config(`input.voxelization` 付き)は未知キー/メジャー不一致として通常の
  検証エラーで拒否される(専用の移行メッセージは設けない)。
- `pipeline/runner.py`: `_load_mesh`・voxelize ステージ分岐・voxelization provenance
  を削除。先頭ステージは常に `load`。`_ASSET_SCHEMAS` の config スキーマ参照を
  2.0.0 に更新。
- `cli/main.py`: `voxelize` サブコマンドと `_voxel_size`/`_placement` ヘルパ、
  mesh 系例外ハンドラを削除。
- `io/__init__.py`・`io/errors.py`: mesh エクスポートと `MeshReadError` を削除。

## Step 4 — mesh コード削除とヘルパ追加

- 削除: `src/vbdmat/voxelize/`(3 ファイル)、`src/vbdmat/io/mesh.py`、
  `tests/voxelize/`、STL fixture(`stepped_wedge.stl`, `stepped_wedge.open.stl`)。
  実装は git 履歴(最終コミット `8f55562`)に残り、復元手順と設計知見は
  `.local/memo_stltovoxel.md` に記録済み。
- 追加: `vbdmat.io.voxel_manifest.write_material_label_manifest()` —
  canonical `MaterialLabelVolume` を `vbdmat.voxels` マニフェスト+checksummed
  `.npy` として書き出す共有エミッタ(ADR-009 D2)。reader との round-trip を
  テストで担保(`tests/io/test_voxel_manifest.py` に 2 テスト追加)。

## 付随作業 — fixture / examples / テスト更新

- `fixtures/phase1.py`: stepped wedge を STL+ボクセル化から **解析的に生成する
  直接ボクセルマニフェスト** に転換(階段占有を直接ラベル配列として構成、
  形状・per-step 占有数・payload sha を解析的サマリに記録)。STL 生成関数は削除。
- `examples/phase1/generate_{fixtures,configs,reference_baselines}.py` を
  direct-voxel 前提に更新し、committed fixture / config を再生成
  (wedge config digest: `sha256:08d9f0bd…`)。
- テスト更新: `test_pipeline_config.py`(mesh ケース除去、2.0.0 検証、
  v1 mesh 文書の拒否テスト追加)、`test_pipeline_runner.py`(wedge を
  マニフェスト入力に、generator provenance 検証に変更)、`test_cli.py`
  (voxelize → import-voxels ベースの exit-code / help 検証)、
  `test_phase1_fixtures.py`(wedge をリーダー経由の解析的検証に)。
- `README.md` のモジュールツリーから `io/mesh.py`・`voxelize/` を除去。

## 検証結果

- `pytest`: **344 passed, 2 skipped**(skip は従来からの pyopenvdb 未導入)。
- `ruff check src tests`: パス(examples/phase1/demo の既存指摘のみ残置、今回未変更)。
- `mypy src`: 40 ファイル、指摘なし。
- End-to-end: `vbdmat run examples/phase1/configs/stepped_wedge.run.json` が
  全ステージ ok(`run-51a02d11ec84d8f1`)、`vbdmat validate` で checksums ok、
  材料カウント {0: 960, 1: 480} が解析値(48+96+144+192=480)と一致。

## 未完了・申し送り

- **Step 3**: 外部マッピング形式(`vbdmat.optical-mapping` v1)のローダと
  `mapping_path` 対応。ADR-009 D3 に仕様は記載済み。
- **Step 5**: 画像スタッキングジェネレータ(唯一の外部契約実証)。
  `write_material_label_manifest()` が使える状態。
- **Step 6**: palette↔mapping の name 不一致検証(現状 ID のみ照合)と
  材料契約文書。
- **Step 7**: Mitsuba 参照 baseline の再生成。wedge の入力 payload が変わったため
  `docs/phase1-reference-baselines.md` 系の digest は失効している
  (`generate_reference_baselines.py` は更新済み、`--group mitsuba` で再実行が必要)。
- ADR-007/008 と `docs/phase1-research-mvp-report.md` に残る mesh/voxelize への
  歴史的言及は Step 6/7 の文書整理で扱う(ADR-006 には supersede 注記済み)。
- 環境メモ: `.venv` が旧パス(`~/projects/vbdmat`)由来で entry point が壊れていた
  ため `uv sync --group dev --group mitsuba` + reinstall で修復した。
