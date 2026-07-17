# Step 3 報告 — viser GUI 結線

## 実装

- `vdbmat-utils/examples/designlab/designlab_app.py`: GUI 薄皮。Step 1/2 の
  browser-free モジュール（`designlab_registry` / `designlab_configs` /
  `designlab_pipeline` / `designlab_jobs`）を viser widget へ結線するだけで、
  生成・検証・パイプラインロジックは一切持たない。
  - `_parse_args`: `--config-root`（必須）/ `--output-root`（必須）/
    `--work-root`（既定は `designlab_pipeline.default_work_root()`）/
    `--port`（既定 8081）。
  - `_check_environment`: `vdbmat_utils` / `vdbmat` の import 可否を起動時に
    検査し、失敗時は `uv run --group designlab` での起動を促す
    `SystemExit` を出す（venv 取り違え事故対策、plan のリスク方針）。
  - `DesignlabApp.__init__`:
    1. `--config-root`/`--output-root` の存在確認、`--work-root` の
       `mkdir(parents=True, exist_ok=True)` 後に
       `designlab_pipeline.check_roots()` で containment 再検証。
    2. `sweep_stale_work_dirs()` を起動時に1回呼ぶ（自 work-root 限定の
       stale entry 一掃）。
    3. `JobWorker` を起動（`on_error` はステータス行への表示）。
    4. viser widget 構築: 方式ドロップダウン（`REGISTRY` の列挙。
       Phase 2 は1件のみなので選択変更時のフォーム再構築は未実装 — 2方式目
       追加時に必要になる差分として docs に記録する）、
       `method.build_form(gui)` で primitive array フォーム、config カタログ
       （dropdown + Refresh + Load + 保存名 + Save）、asset 名入力 +
       Generate ボタン、status markdown。
  - `_refresh_catalog` / `_load_config` / `_save_config`:
    `designlab_configs` の関数をそのまま呼び、`DesignlabConfigError` の
    メッセージをそのまま status へ表示する（再解釈しない）。
  - `_on_generate`: `method.form_to_config()` の例外（config
    `__post_init__` のフィールド名付きエラー）をそのまま表示、
    `job_worker.submit()` で `run_generate_job()` をバックグラウンド実行、
    `on_stage` コールバックで `STAGE` 進行を status へ反映、
    `PublishError` は失敗段名とメッセージをそのまま表示、成功時は発行パス
    （reuse なら注記付き）を表示する。`JobBusyError` は「実行中」として
    拒否メッセージを表示する（cancel は作らない、plan どおり）。
  - viser API は viewer で使用実績のある範囲
    （`add_folder` / `add_dropdown` / `add_number` / `add_text` /
    `add_button` / `add_markdown` / `.value` / `.content` / `.options`）に
    限定した。

## 検証（browser-free の代替、本 Step 分）

本開発環境はブラウザを操作できないため、GUI 層の自動テストは作らない
（plan どおり）。Step 3 では widget 構築コード自体が正しい viser API 呼び出し
であることを、実サーバ起動によるスモークで確認した:

```bash
cd vdbmat-utils
uv sync --group designlab --group dev
uv run --group designlab python -u examples/designlab/designlab_app.py -- \
  --config-root .local/designlab/p2/smoke/config \
  --output-root .local/designlab/p2/smoke/output \
  --port 8097
```

- viser の HTTP バナーが表示され、`designlab ready: http://127.0.0.1:8097
  (work root: .../output.designlab-work)` が出力された
  （widget 構築が例外なく完了したことの直接証跡）。
- `curl http://127.0.0.1:8097/` が `200` を返した。
- `--work-root` 省略時に `<output-root>.designlab-work` が自動作成される
  ことを確認した。
- 検証成果物は `.local/designlab/p2/`（git 管理外）に置き、確認後削除した。

フォーム穴埋め → Generate → 既存 viewer での Load/Rebuild のブラウザ経由
end-to-end 確認は Step 4（`docs/designlab.md` の human 向け手順提示 +
scripted 代替確認）で実施する。

## 静的検査・テスト結果

```
uv run ruff check examples/designlab
→ All checks passed

uv run ruff check .（リポジトリ全体）
→ 本 Step と無関係な既存1件（test_formation_workflows.py:15、E501）のみ

uv run pytest -q tests/unit tests/contract
→ 355 passed（`uv sync --group designlab` で Pillow が一緒に解決され、
  従来 PIL 未導入でスキップしていた2件が実行されるようになった。regression
  なし）

uv run pytest -q -m integration tests/integration
→ 15 passed
```

## 完了条件の充足状況（Step 3 分）

- [x] 起動引数（`--config-root`/`--output-root`/`--work-root`/`--port`）、
      方式ドロップダウン、primitive array フォーム、config カタログ
      （dropdown + Refresh + Load/Save）、name 入力、Generate ボタン、
      status 行（STAGE 進行・失敗段・発行結果パス）を実装した。
- [x] 起動時チェック（roots の存在・containment、`vdbmat_utils`/`vdbmat`
      の import 可否）を実装した。
- [x] viser API を viewer 実績範囲に限定し、GUI 層の自動テストは行わず
      core 層のテストで担保する方針を維持した。

## 想定外事項

なし。`uv sync --group designlab` で Pillow が随伴解決され、既存の
PIL-skip 2件が実行対象になったのは Phase 1 完了時点の環境差であり、
本 Step の変更が引き起こした regression ではない（テストは pass）。
