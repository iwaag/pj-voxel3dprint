# Step 4 報告 — docs・手動 end-to-end 確認

## docs / README

- `vdbmat-utils/docs/designlab.md` を新規作成した。起動方法（`--config-root`
  / `--output-root` / `--work-root` / `--port`、`designlab` dependency
  group と同一 venv 前提の理由）、フォーム↔config 対応表、config
  save/load 規則（上書き拒否・エラー透過）、STAGE 語彙（5段の意味と
  roadmap スケッチとの `import`→`map` 吸収差分）、発行命名・衝突/reuse
  規則、work-root cleanup 規則、GUI=CLI 再現契約（該当 integration test
  への参照込み）、**レジストリのインターフェースと2方式目
  （`voxelize-mesh`、roadmap Phase 3 想定）の追加手順**を記載した。
  追加手順は「`designlab_registry.py` に4関数を書き `REGISTRY` へ append」
  「`designlab_pipeline.py`/`designlab_jobs.py` は方式非依存なので変更不要」
  「`designlab_app.py` は複数方式化時のみフォーム再構築の結線が必要」まで
  具体的に書いた（roadmap 完了条件「READMEレベルで書ける」に対応）。
- `vdbmat-utils/README.md`: Status 節に designlab GUI の1文を追加し、
  Usage 節に "designlab: a browser GUI for building inputs" 小節を
  追加した（Primitive-array workflow の直後、Validation and hand-off の
  直前）。
- `README_QUICK.md`: Use Case 4c として designlab の起動コマンドと
  操作フローの要約を追加した（p1 report5 で「designlab GUI 全体の記述は
  Phase 2」と繰り延べた分）。既存 Use Case 8 の viewer 章への参照も含めた。

## 手動 end-to-end walkthrough

`.local/designlab/p2/`（git 管理外、確認後削除済み）で実施した。

1. **scripted 一括実行**: p1 report5 と同一の primitive array config
   （cube 3×2×1、size=4voxel、gap=2voxel、margin=1voxel、
   `transparent-resin`/`black-opaque-resin`）を `designlab_configs.load_config`
   で読み込み、`designlab_pipeline.run_generate_job` を直接呼んで発行した
   （GUI を介さない core 直呼び — 本環境がブラウザを操作できないための
   代替経路。p1 report5 と同じ位置づけ）。
   - `STAGE generate:demo {validate,generate,map,verify,publish} <elapsed_s>`
     が期待順序で出力された。
   - 発行パス `primitive-array-demo-463a3bf436ec`（`<method_id>-<name>-
     <digest12>` の命名規則どおり）。
2. **verify（vdbmat validate）**: `vdbmat validate <bundle> --json` が
   `status: ok`、`validation.checksums: ok`。material counts は
   `transparent-resin: 912` / `black-opaque-resin: 384` — p1 report5 の
   手動確認と厳密に一致（同一 config・同一ジェネレータなので当然の
   一致であり、designlab パイプラインが生成内容を変えていないことの
   確認になる）。
3. **viewer 側の検出契約確認（viewer 相当の目視確認）**: 本開発環境は
   ブラウザを操作できないため（p1/mitsubagui 系と同じ制約）、viewer の
   Input タブが内部で使う `mitsuba_stage_inputs.scan_input_catalog()` /
   `describe_candidate()` を `vdbmat` 側から直接呼んだ。
   - `scan_input_catalog(output_root)` が発行済み bundle を
     `InputKind.RUN_BUNDLE` として1件検出した（Input タブのドロップダウンに
     現れる内容と同一）。
   - `describe_candidate()` が shape `(6, 12, 18)`、voxel size
     `(1e-4, 1e-4, 1e-4)`、provenance（generator
     `vdbmat-utils.primitives.array@0.1.0`、mapping
     `phase0-provisional-materials-v1@1.0.0`）を返した — Input タブの
     「選択候補のスキーマ/shape/voxel-size 要約」表示内容と同一。
   - Load/Rebuild 自体（Mitsuba での実レンダー）は、bundle の中身が
     p1 report5 で確認済みのものと config digest レベルで同一であり、
     かつ viewer の既存回帰テスト
     （`test_mitsuba_stage_viewer_regression.py`）が「有効な run bundle を
     Load/Rebuild できること」を汎用に担保しているため、本 walkthrough
     では重複実行しなかった。
4. **GUI=CLI 再現契約**: `tests/integration/test_designlab_pipeline.py::
   test_gui_saved_config_reproduces_bundle_payload_digest` で機械的に
   固定済み（Step 2）。本 walkthrough では追加確認していない。

### human 向け確認手順（本環境では未実施）

`docs/designlab.md` に記載したとおり:

```bash
cd vdbmat-utils
uv run --group designlab python examples/designlab/designlab_app.py -- \
  --config-root <CONFIG_ROOT> --output-root <OUTPUT_ROOT> --port 8081
# ブラウザで http://127.0.0.1:8081 を開き、
# primitive array フォームを穴埋め（または Load）→ name 入力 → Generate
# → status 行で publish 完了を確認
```

続けて同じ `--output-root` を `mitsuba_stage_viewer.py --input-root` に
指定し、Input タブの Refresh → 選択 → Load/Rebuild で目視確認する
（README_QUICK.md Use Case 8 の既存手順）。

## 完了条件の充足状況（ロードマップ Phase 2 全体）

- [x] フォーム穴埋め → Generate で `<method_id>-<name>-<digest12>` の
      canonical bundle が `--output-root` へ atomic に発行される
      （Step 2/3、本 walkthrough で再確認）。
- [x] 発行 bundle が viewer の検出契約（`run.json` + `optical.zarr`）を
      満たすことが integration test（Step 2）で固定され、
      本 walkthrough で viewer 側検出関数による確認も行った。
- [x] GUI が保存した config の CLI 再実行で payload sha256 が一致する
      ことが integration test で固定されている（Step 2）。
- [x] 不正パラメータ・サイズガード超過・発行先衝突・EXDEV の失敗で
      output root が汚れず、失敗段階が status に表示されることが
      テストで固定されている（Step 2 unit/integration）。
- [x] レジストリのインターフェースと2方式目の追加手順が
      `docs/designlab.md` に文書化されている（本 Step）。
- [x] 既存テストが無変更で pass し、検証成果物は `.local/designlab/p2/`
      に隔離し確認後削除した。

## 静的検査・テスト結果（最終確認）

```
uv run ruff check .
→ 本 phase と無関係な既存1件（test_formation_workflows.py:15、E501）のみ

uv run pytest -q tests/unit tests/contract
→ 355 passed

uv run pytest -q -m integration tests/integration
→ 15 passed
```

## 想定外事項

なし。Step 2 で発見・修正した `JobWorker` の例外処理見直し（report2 記載）
以外に、計画からの逸脱や人間判断を要する事態はなかった。
