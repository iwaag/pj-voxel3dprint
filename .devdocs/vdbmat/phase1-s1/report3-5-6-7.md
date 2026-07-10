# Phase 1-side1 実装報告 — Step 3, 5, 6, 7

対象計画: `.local/phase1-s1/plan.md`(前報 `report1-2-4.md` の続き)
実施日: 2026-07-05

これで Phase 1-side1 の全ステップが完了した(メッシュ外部ツール化は計画どおり延期、
知見は `.local/memo_stltovoxel.md` に保全)。

## Step 3 — 材料係数マッピングのプラガブル化

- 新形式 **`vbdmat.optical-mapping` v1** を定義(仕様: `docs/schemas/optical-mapping-v1.md`)。
  実装は `src/vbdmat/optics/document.py`:
  `load_optical_mapping()` / `write_optical_mapping()` / dict 変換。
  strict reader(未知キー拒否・basis 固定・`external_id` 禁止)。
  canonical JSON / digest は既存 `OpticalMappingConfig` の規則をそのまま使うため、
  **ビルトインと外部ファイルで digest が一致する**(検証済み: `sha256:da83581c…`)。
- `PipelineConfig` に `mapping_path` + `mapping_digest` を追加(`mapping_name` と排他)。
  ファイル指定時は **digest 宣言が必須**で、`resolve_mapping(base_dir)` がロード時に
  照合し、書き換えられたファイルは実行前に失敗する(ADR-009 D3)。
  scientific digest の mapping 識別を `{name, digest}` → `{digest}` に変更
  (供給方法に依存しない同一性。baseline は Step 7 で再生成済み)。
- CLI: `convert --mapping-file FILE` と新コマンド `vbdmat mapping-digest FILE` を追加。
- 参照文書 `examples/phase1/mappings/phase0-provisional-materials-v1.optical-mapping.json`
  を `generate_fixtures.py` から決定的に生成。
- テスト: `tests/optics/test_mapping_document.py`(round-trip / digest の形式非依存 /
  external_id 拒否 / 各フィールド異常系)、pipeline config に排他・digest 検証・
  path round-trip の 8 テスト、CLI にビルトインとの Zarr 一致テスト。

## Step 5 — 第 2 の外部ジェネレータ(契約の end-to-end 実証)

- `tools/image_stack_generator/generate.py`: グレースケール PGM 断層画像列
  (P5/P2、依存ゼロの自前パーサ)+ gray→材料の対応 JSON から
  `vbdmat.voxels` マニフェストを出力する参照ジェネレータ。
  Step 1-2-4 で追加した `write_material_label_manifest()` を使用
  (依存方向 tool → core、ADR-009 D2 準拠)。
- 未宣言 gray 値・スライス寸法不一致は明示エラー。provenance に
  スライス内容の sha256 identity を記録。
- `tests/tools/test_image_stack_generator.py`:
  **PGM 生成 → ジェネレータ → マニフェスト → コアパイプライン(外部マッピング
  ファイル指定)→ optical.zarr** を通し、材料数保存を検証。
  これが exit criteria「メッシュ以外の外部ジェネレータによる契約実証」を満たす。

## Step 6 — 材料識別契約の形式化と name 照合

- `map_material_volume_to_optical()` の palette 照合を強化: 共有 `material_id` の
  name がパレットとマッピングで食い違う場合、係数を黙って適用せず
  `OpticalMappingError`(`palette.materials`)で失敗する。
- 名称の正準化: coupon パレットを `background/transparent/white/black` →
  `air/transparent-resin/white-resin/black-opaque-resin` に、wedge の背景を `air` に、
  synthetic の軸マーカーを `axis-{x,y,z}-diagnostic` に改名し、ビルトイン
  マッピングの名前と完全整合させた(fixture 再生成済み)。
- 契約文書 `docs/material-identity-contract.md` を新規作成
  (二層構造・実務ルール 4 項)。`README_EXTEND.md` の第 7 節を
  「ADR-009 実装済み」の内容に書き換え、マッピング差し替え手順と
  ジェネレータ向けヘルパの案内を追加。

## Step 7 — 参照 baseline の再生成

- `uv run --group mitsuba python examples/phase1/generate_reference_baselines.py
  .local/phase1/step10 --overwrite` を実行し成功。
  両オブジェクトの run bundle + Mitsuba レンダー(256², 64spp)+
  `baseline-manifest.json` を再生成:
  - window_coupon: `run-66a8fa52e145f117`
  - stepped_wedge: `run-fff95d3975c228d9`(入力がマニフェスト化されたため新 ID)
- OpenVDB/Cycles smoke(`--record-cycles`)は pyopenvdb 未導入のため未実施
  (従来からの optional 扱い。pinned Docker 環境で必要時に実行)。

## 検証結果

- `pytest`: **371 passed, 2 skipped**(skip は従来からの pyopenvdb)。
- `ruff` / `mypy`(src, tools, tests): 指摘なし。
- End-to-end(実 CLI): quickstart 両 config の `vbdmat run` が全ステージ ok、
  `mapping-digest` がビルトイン digest と一致、`convert --mapping-file` の出力
  Zarr がビルトイン指定と byte 一致。

## 影響と注意点

- **digest の変化**: scientific digest の定義変更と fixture 改名により、旧 run の
  run_id / Zarr checksum は今回の出力と一致しない(破壊的変更前提で許容、
  baseline は再生成済み)。config の全体 digest はキー順ソートにより
  coupon で変化なし。
- **パレット名の制約が強化**: 既存の自作マニフェストで `transparent` 等の旧名を
  使っている場合、次回実行時に name 照合エラーになる。正準名は
  `docs/material-identity-contract.md` を参照。
- 残るのは roadmap 上の次フェーズ(Phase 2)と、延期したメッシュ外部ツール
  (`.local/memo_stltovoxel.md`)のみ。
