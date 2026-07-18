# denoise 実装計画 実施報告 — Step 3

`plan.md` の Step 3（GUI（binder）と session の配線）を完了した。

## 変更内容

### `mitsuba_stage_binder.py`

- `StageBinder.__init__` に `variant: str = "llvm_ad_rgb"`（キーワード専用、
  既定値は `StageCore` と同じ）を追加した。
- Render タブに `denoise (OptiX)` checkbox を追加し、
  `disabled=not variant.startswith("cuda")` で viewer 起動時の variant が
  CUDA 系でなければ無効化する。ヒントテキストで理由（OptiX 依存、CUDA
  必須）を明示した。checkbox は exact widget（backdrop.enabled 等と同じ）
  として即時 `on_update` → `_notify_change()` に載せた。
- `replace_config`（session/preset 読み込み時の全widget再設定）と
  `current()`（GUI から `StageConfig` を組み立てる経路）の両方に
  `denoise` を追加した。

### `mitsuba_stage_viewer.py`

- `StageBinder(...)` 構築呼び出しに `variant=startup.variant` を渡すだけの
  1行追加。`startup.variant` は `ViewerStartup`（`--variant` CLI 解決結果）
  からそのまま取れるため、他の変更は不要だった。

### `mitsuba_session_compat.py` / `mitsuba_viewer_session.py`（想定どおり無変更）

plan の想定（「`_comparable_fields` は `stage.effective_digest` を丸ごと
比較するので render.denoise の差も自動的に拾う」）は今回は的中した。
Step 1 で `mitsuba_viewer_session.py` の `_RENDER_KEYS` を直しておいたため、
`stage.effective_digest = stage_config_digest(session.stage_config)` は
`denoise` を含めて正しく計算されており、`mitsuba_session_compat.py` は
1バイトも変更せずに `denoise` 差を `DIFF stage.effective_digest: ...`
として報告できた。

## テスト

### 単体（`tests/test_mitsuba_stage_viewer_worker.py`, Mitsuba不要）

- `test_stage_binder_denoise_widget_and_preset_round_trip`: checkbox の
  既定値が `RenderSettings.denoise` を反映すること、`set_value` →
  `current()` → プリセット書き出し→読み込みが一致すること。
- `test_stage_binder_denoise_disabled_unless_cuda_variant`: `variant` 省略時
  ・`"llvm_ad_rgb"` 明示時のいずれも `denoise.disabled is True`、
  `"cuda_ad_rgb"` 時のみ `False` であること。
- `test_stage_binder_replace_config_is_exact_and_suppresses_callbacks`
  （既存テスト）に `denoise=True` を含む `replacement` を追加し、
  `replace_config` 経由でも正しく反映されることを確認した。
- `_FakeGui.add_checkbox` を実 viser の `add_checkbox(..., disabled=...,
  hint=...)` シグネチャに合わせて `**options` を受け取り `disabled`
  属性を持たせるよう更新した（既存5件のテストは無回帰）。

### 単体（`tests/test_mitsuba_session_compat.py`, Mitsuba不要）

- `test_denoise_only_difference_is_detected`:
  `RenderSettings(denoise=False)` vs `RenderSettings(denoise=True)` の
  セッション比較が `stage.effective_digest` の差として検出されること
  （`test_effective_stage_render_difference_is_detected` と同型で、
  `denoise` 専用の回帰カバレッジとして追加した）。

### 統合（`tests/integration/test_mitsuba_stage_viewer.py`, 実Mitsuba）

- `test_denoise_recorded_in_saved_session_and_survives_headless_resolve`
  （新規）: `cuda_ad_rgb` variant で `create_viewer_session` →
  `write_viewer_session` → `viewer_session_from_json` →
  `resolve_viewer_session` の一巡を通し、`render.denoise=True` が
  session 保存・再読込・resolve のどの段階でも失われないことを確認した。

  既存の `test_saved_session_viewer_final_matches_headless_session_replay`
  と同型だが、**ピクセル一致までは検証していない**。理由:
  `mitsuba_stage_demo.py` の `render_stage()` はまだ denoise を適用しない
  （plan の Step 4 の範囲）ため、denoise=True の session を今
  `--session` replay すると raw のまま出力され、GUI 側の denoise 済み
  final render とはピクセル一致しない。plan の Step 3 完了条件は
  「headless replay が同一 GPU で pixel-identical に再現する」と
  書かれているが、これは `render_stage()` の denoise 対応（Step 4）が
  完了して初めて成立する条件であり、Step 3 単独では前提が満たせないと
  判断した。人間の判断を要する設計変更ではなく、plan の Step 分割どおり
  Step 4 で解消される順序依存の記述漏れと判断し、今回は「session の
  仕組み自体が denoise を正しく運ぶこと」までを Step 3 の完了条件として
  検証し、pixel-identical replay の確認は Step 4 完了後・Step 5 の
  一巡検証で行うこととした。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q --ignore=tests/integration
609 passed in 35.46s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer.py
43 passed, 2 warnings in 25.60s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer_regression.py
9 passed in 17.25s
```

（warningはStep 1/2と同じ既知の非同期teardown由来。）

```text
uv run ruff check examples/pipeline_run/demo/mitsuba_stage_binder.py \
  examples/pipeline_run/demo/mitsuba_stage_viewer.py \
  tests/integration/test_mitsuba_stage_viewer.py \
  tests/test_mitsuba_session_compat.py tests/test_mitsuba_stage_viewer_worker.py
All checks passed!

uv run ruff format --check (同上ファイル群)
5 files already formatted

git diff --check
問題なし
```

## コミット境界としての判断

Step 3 完了地点を独立したコミット境界とした。この境界で次が単独で成立する。

- Render タブに `denoise (OptiX)` checkbox があり、GUI の variant に応じて
  disabled/enabled が切り替わる。
- checkbox の値が `StageConfig`（save preset / save session / final render
  すべての経路）に正しく伝わる。
- session save/resolve（`create_viewer_session` → `write_viewer_session` →
  `viewer_session_from_json` → `resolve_viewer_session`）が `denoise` を
  一貫して運ぶ。
- `mitsuba_session_compat.py` が denoise 差を `stage.effective_digest` の
  DIFF として検出する（無変更で機能）。
- `mitsuba_stage_demo.py` は未着手（Step 4 の範囲、`render_stage()` は
  まだ denoise を適用しない）。

変更対象は次の5fileのみ。

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_binder.py`
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
- `vdbmat/tests/test_mitsuba_session_compat.py`
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`

vdbmat submodule 側のコミット: `40c6ff1 denoise p0 step3: GUI binder
checkbox and session wiring`。

## 未実施事項

- Step 4: `mitsuba_stage_demo.py --denoise`（legacy CLI 上書き）と
  `render_stage()` への `finalize_render_image` 配線、README_QUICK /
  stage viewer manual の追記。
- Step 5: 白バンドルでの一巡検証（GPU実測、report5.md）。Step 3 で
  先送りにした「session replay のピクセル一致」確認もここで行う。
