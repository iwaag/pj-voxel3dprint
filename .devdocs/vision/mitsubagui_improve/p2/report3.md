# mitsubagui_improve Phase 2 実施報告 — Step 3

`plan.md` の Step 3（transactionalなload/rebuildとswap）まで完了した。
`StageCore.load_input()` としてvalidate→prepare→load→smoke→swapの5段階を
実装し、Mitsuba integration testで成功経路と各段階の失敗経路（現在session
維持・一時ディレクトリ破棄）を固定した。GUI（Inputタブ、Load/Rebuild
button、statusへの段階表示）はまだ配線しておらず、`load_input()` は
StageCore層のAPIとしてのみ存在する。

## 変更内容

### `StageCore.load_input()`（`mitsuba_stage_viewer.py`）

Step 1のカタログ契約（`mitsuba_stage_inputs.resolve_candidate`）とStep 2の
`InputSession`/`swap_session()` を接続する新メソッドを追加した。

```text
validate : resolve_candidate(root, user_path) + read_volume +
           optical-property型検証
prepare  : prepare_mitsuba_scene()（新sessionのwork directoryへ、
           MitsubaExportConfigは現在のstage/render設定のmax_depthを使う）
load     : TraversedPreviewScene構築（現在のstage/render設定で）
smoke    : interactive相当のspp（呼び出し側が渡す smoke_spp）での
           1回の小レンダー
swap     : StageCore.swap_session() 呼び出し（session世代インクリメント）
```

- 各段階の開始を `on_stage(stage_name)` callbackへ通知する（既定は
  no-op）。Step 4でGUIの `status.content` 更新に接続する想定。
- `swap` 段階に到達する前のあらゆる例外は
  `InputLoadError(stage, message)` として再送出する。メッセージは
  plan指定の文言 `input load failed at <stage>: <error要約>` をそのまま
  組み立てる。
- `validate` を除く各段階の失敗時、新sessionの一時work directory
  （`_session_work_dir()` で採番済みの `inputs/<seq>-<slug>/`）を
  `shutil.rmtree()` で削除する。削除自体が失敗した場合は例外にせず
  `INPUT LOAD CLEANUP WARNING` をstderrへ出す（plan通り、cleanup失敗を
  致命的に扱わない）。
- `swap` に到達するまで `self._session` / `self.session_generation` は
  一切変更しない。失敗時は現在のsession・previewが無傷であることを
  テストで確認した。
- `prepare`/`load`/`smoke` はすべて呼び出し時点の `current_config`
  （GUIの現在のstage/render設定）を使う。これにより「切替後も現在の
  設定を維持する」ことと「新入力との不整合を事前検出する」ことを
  同じ経路で満たす（plan通り）。

### 例外型とヘルパー

- `InputLoadError(stage, message)`: `stage` は5段階名のいずれか
  （assertで保証）、`message` はplan文言。`.stage` / `.message` を属性として
  保持し、GUI側が段階別の表示分岐をしたくなった場合にも使える。
- `_discard_session_dir(path)`: 存在すれば `shutil.rmtree`、失敗はwarning
  ログに留める、Mitsuba/viser非依存の純粋関数。

### `mitsuba_stage_inputs` との初結線

Step 1で作った `resolve_candidate()` を `mitsuba_stage_viewer.py` から
importした、両moduleの最初の実配線。containment検証・bundle/単体判別は
Step 1の契約をそのまま再利用し、viewer側で重複実装していない。

## テスト

すべて `tests/integration/test_mitsuba_stage_viewer.py`（Mitsuba必須、
`uv run --group mitsuba-viewer` で実行）に追加した。段階別の失敗が
実際に「そこで」起きることを保証するため、`monkeypatch` で
`prepare_mitsuba_scene` / `TraversedPreviewScene`（コンストラクタ・
`render` メソッド）を狙って壊す構成にした。

- `test_load_input_swaps_to_new_session_using_current_stage_settings`:
  異なる形状の2入力（`homogeneous_transparent()` /
  `transparent_opaque_interface()`）でA→Bへswapし、
  `on_stage` の呼び出し順序が
  `["validate", "prepare", "load", "smoke", "swap"]` であること、
  `session_generation` が1進むこと、`core._session` が新sessionを指す
  こと、`max_depth` を含む現在設定がPIXELSTATSに反映されること、swap後の
  非構造的変更が引き続き `"traverse"` routeで処理されることを確認した。
- `test_load_input_validate_failure_preserves_current_session`: root外の
  パスを指定すると `stage == "validate"` で失敗し、`on_stage` が
  `["validate"]` のみ呼ばれ、`session_generation`/`core._session` が
  無変更で、元sessionが引き続きrenderできることを確認した。
- `test_load_input_prepare_failure_discards_new_session_and_preserves_current`:
  `prepare_mitsuba_scene` をmonkeypatchで壊すと `stage == "prepare"` で
  失敗し、新sessionの一時work directoryが作られない（または残らない）
  こと、現在sessionが無傷であることを確認した。
- `test_load_input_load_failure_removes_prepared_work_dir`:
  `TraversedPreviewScene`（コンストラクタ）を壊すと `stage == "load"` で
  失敗し、実際に作られたprepare済みwork directoryが削除されていることを
  確認した（実際にファイルが書かれた後の破棄を検証する唯一のケース）。
- `test_load_input_smoke_failure_removes_prepared_work_dir`:
  `TraversedPreviewScene.render` を壊すと `stage == "smoke"` で失敗し、
  work directoryが削除され、現在sessionが無傷であることを確認した。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer.py
11 passed in 3.33s

uv run pytest -q --ignore=tests/integration
405 passed in 20.35s

uv run --group mitsuba-viewer pytest -q \
  tests/integration/test_mitsuba_stage_viewer.py \
  tests/integration/test_mitsuba.py \
  tests/integration/test_pipeline_end_to_end.py
28 passed in 6.68s

uv run ruff check \
  tests/integration/test_mitsuba_stage_viewer.py \
  examples/pipeline_run/demo/mitsuba_stage_viewer.py
All checks passed!

git diff --check
問題なし
```

`git status` は2ファイルの変更のみ（`mitsuba_stage_viewer.py` 本体と
viewer integration test）で、他の追跡ファイルへの変更はない。

## コミット境界と未実施事項

Step 3は次の不変条件を単独で満たす。

- `StageCore.load_input()` が5段階を固定順序で実行し、各段階開始を
  `on_stage` で観測できる。
- `swap` に到達する前のいかなる失敗も、現在のsession・
  `session_generation`・previewを変更しない。
- 失敗した新sessionの一時work directoryは（作られていれば）削除される。
- `prepare`/`load`/`smoke` は呼び出し時点の現在stage/render設定
  （`max_depth` 含む）を使い、swap後もその設定のまま追加編集が
  `traverse` routeで処理される。
- Phase 1・Step 2のunit/integration testが全て通る。

この境界では以下は意図的に未実施で、`plan.md` の次Stepに残している。

- Step 4: Inputタブ（dropdown/Refresh/概要/Load・Rebuild button）、
  `_parse_args()` への `--input-root` 追加とbundle初期入力の受理、
  `ViewerApp` からの `worker.submit(lambda: core.load_input(...))` 配線、
  `on_stage` を `status.content` へ反映、成功時の
  `_schedule_preview()` 再発行、Load/Rebuild中のbutton disable。
- Step 5: 統合テスト、README追記、`.local` での実bundle往復切替の手動確認。

`mitsuba_stage.py`（stage-config契約）、`mitsuba_stage_demo.py`
（headless）、`mitsuba_stage_inputs.py`（Step 1、読み取り専用で利用）、
canonical exporter・io・pipeline（`src/vdbmat`）には変更していない。
動作確認用のローカル成果物も生成していない。
