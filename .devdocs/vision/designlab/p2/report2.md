# Step 2 報告 — 実行パイプライン core（browser-free）

## 実装

- `vdbmat-utils/examples/designlab/designlab_pipeline.py`:
  `validate → generate → map → verify → publish` の一括実行 core。
  - `_StageTimer`（viewer の `mitsuba_stage_core._StageTimer` と同構造）が
    `STAGE <transaction> <stage> <elapsed_s>` を stdout へ出し、
    `on_stage(stage)` コールバックで GUI 側（Step 3）に進行を通知する。
  - `validate` 段: `validate_name`（`[a-z0-9][a-z0-9-]*`）、
    `check_roots`（`--output-root`/`--work-root` の存在確認、work-root が
    output-root 配下にある場合の拒否）、発行名
    `publish_name_for()`（`<method_id>-<name>-<digest12hex>`）の導出、
    発行先衝突チェック。衝突時は既存が有効 bundle（`run.json` +
    `optical.zarr`）なら `generate`〜`publish` を全てスキップして
    `reused=True` で成功終了、無効なら自動削除・上書きをせず明示エラー。
  - `generate` 段: `method.generator_argv()` で得た argv を
    `subprocess.run` で実行（`vdbmat-utils generate-primitive-array`）。
  - `map` 段: `run.json`（`vdbmat.pipeline-config` 2.0.0、
    `input.kind=direct-voxel`、`mapping.name=phase0-provisional-materials-v1`、
    `output={"path":"bundle","overwrite":false}`、
    `execution.random_seed=0`）を手書き dict として work dir 直下へ書き、
    `sys.executable -m vdbmat.cli.main run <run.json> --json` を実行する。
    `PipelineConfig` を import して組み立てることはしていない —
    roadmap のパッケージ境界どおり、生成・mapping の実行は必ずサブプロセス
    CLI 経由とし、designlab は `vdbmat.pipeline` を import しない。
  - `verify` 段: `vdbmat validate <bundle> --json` をサブプロセス実行し、
    非ゼロ終了コードで stage 名付きエラーへ変換する。
  - `publish` 段: `os.replace(work_dir/bundle, dest)` で atomic 発行。
    `EXDEV`（cross-device）は `--work-root` を output-root と同一
    filesystem にするよう案内する専用メッセージへ変換する。成功時は
    自ジョブの work dir を削除、失敗時は残す（調査用）。
  - `sweep_stale_work_dirs(work_root)`: 自分の `--work-root` 配下の
    エントリを起動時に一掃するための関数（起動時sweepの呼び出し自体は
    Step 3 の app 起動処理で行う）。
  - roadmap スケッチとの差分（`import` 段の吸収）は plan の決定事項どおり
    モジュール docstring に記録した。
- `vdbmat-utils/examples/designlab/designlab_jobs.py`: `JobWorker`。
  worker thread 1本にジョブを直列化し、実行中の `submit()` は
  `JobBusyError` で拒否する（cancel は作らない、plan の decision どおり）。
  ジョブ関数が例外を投げても worker thread は生き続け、`on_error`
  コールバック（既定は stderr 出力）へ委譲する形にした
  （viewer の `RenderWorker._on_error` と同じ安全網パターン）。

## テスト

- `tests/unit/test_designlab_pipeline_unit.py`（subprocess を一切呼ばない）:
  `validate_name` の受理・拒否、`publish_name_for` の
  `<method_id>-<name>-<digest12>` golden、`default_work_root`、
  `check_roots` の work-root 配下拒否・root 不存在拒否、`run.json` の
  golden（`_write_run_config` の出力を厳密比較）、衝突分岐2種
  （有効 bundle → `reused=True`／無効 → `PublishError(stage="validate")`、
  かつ work dir が作られないことも確認）、不正名の拒否、
  `sweep_stale_work_dirs` の全消去・root 不存在時の無害動作。
- `tests/unit/test_designlab_jobs.py`: 別スレッドでの実行、busy 中の
  `submit()` 拒否、成功後・失敗後どちらも `busy` が解除されること、
  失敗時に `on_error` が呼ばれ worker thread が生存し次のジョブを
  受け付けられること、`next_seq` の単調増加。
- `tests/integration/test_designlab_pipeline.py`（`integration` marker、
  4x4x4 voxel の tiny config、実サブプロセス）:
  - happy path: 発行 bundle が `run.json`/`optical.zarr` を持ち
    `vdbmat validate --json` が `status: ok`、成功時に work dir が
    空になることを確認。
  - GUI=CLI 再現契約: `run_generate_job` が発行した bundle の
    `run.json.input_payload_sha256` と、同じ config を素の
    `vdbmat-utils generate-primitive-array` CLI へ渡して得た
    `<name>.material_id.npy` の sha256 が一致することを固定した。
  - 失敗時非発行: `max_axis_cells=1`（導出セル数4に対して超過）の config で
    `generate` 段が `PublishError` を投げ、`--output-root` が空のまま、
    work dir は調査用に残ることを確認した。
  - 再発行: 同一 config・同一 name の2回目呼び出しが `reused=True` で
    同一 `publish_path`/`publish_name` を返すことを確認した。

## 静的検査・テスト結果

```
uv run ruff check examples/designlab tests/unit/test_designlab_pipeline_unit.py \
  tests/unit/test_designlab_jobs.py tests/integration/test_designlab_pipeline.py
→ All checks passed

uv run pytest -q tests/unit tests/contract -m "not integration"
→ 353 passed, 2 skipped（Step 1 完了時の 337+15=352 に対し、jobs テスト分の
  追加込みで整合。warning なし）

uv run pytest -q -m integration tests/integration
→ 15 passed（既存 integration テスト11件 + designlab 新規4件）
```

## 完了条件の充足状況（Step 2 分）

- [x] run.json 組み立て golden、発行名導出、STAGE 進行
      （`_StageTimer`）、サブプロセス実行、verify、atomic publish、
      reuse / 衝突 / EXDEV の分岐、work dir cleanup 規則を実装した。
- [x] ジョブ直列化（`designlab_jobs.py`）を GUI なしで駆動できる形で実装した。
- [x] unit test: run.json golden、発行名、衝突分岐（有効=reuse／
      無効=エラー）、work-root が output-root 配下のとき拒否 — 固定した。
- [x] integration test: happy path / GUI=CLI digest 一致 / 失敗時非発行 /
      再発行 — 固定した。

## 想定外事項

`JobWorker` の初期実装ではジョブ関数の例外がそのままスレッドを終了させ、
pytest が `PytestUnhandledThreadExceptionWarning` を報告した。実運用でも
「1回の失敗で worker thread が死ぬと以後の Generate が永久に効かなくなる」
という同じ問題が起きるため、plan の変更ではなく実装の見直しとして
`on_error` コールバックで捕捉し worker thread を存続させる形に直した
（人間判断が必要な計画変更ではないと判断し、その場で修正・テスト固定した）。
