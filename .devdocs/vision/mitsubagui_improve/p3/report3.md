# mitsubagui_improve Phase 3 実施報告 — Step 3

`plan.md` の Step 3（Binder置換とPresetタブ）まで完了した。
`StageBinder.replace_config()` とprogrammatic callback抑止を実装し、viewerへ
`--preset-root`、Presetタブ、Refresh／概要／`Apply stage preset`、適用presetの
source追跡を追加した。

この時点で「presetを選ぶ」「内容を確認する」「明示的に適用する」「適用後のGUI編集で
sourceを無効化する」というGUI側の契約が、Step 1のcatalog／digestと接続されている。
unit test、Mitsuba integration test、実viser server起動が通ったため、Step 3完了地点を
独立したコミット境界として適切と判断した。

Step 4のseed引継ぎ、Session Save/Load transaction、startup session復元は未着手である。

## 変更内容

### `StageBinder.replace_config()`

`mitsuba_stage_viewer.py` の `StageBinder` に、完全な `StageConfig` を全widgetへ一括反映する
`replace_config(config)` を追加した。

- render、backdrop、floor、key light、camera、backlightの全handleを更新する。
- camera／backlightのenabled stateもconfigの `None`／overrideに合わせる。
- radianceはGUIのcolour＋intensityへ、key-light directionはazimuth＋elevationへ分解する。
- 更新後に `base = config`、`dirty.clear()` とする。
- slider／RGB widgetには表示可能範囲へclamp／量子化した値を置く。
- 実効値の正本はexactな `base` に残すため、ユーザーが未編集のfieldは
  `current()` で元のunquantized値を返す。

これにより、StageConfig上は正当だがGUI slider範囲外の値も、表示だけを安全にclampしつつ
presetのexact値を失わない。

### Programmatic callback抑止

`StageBinder` に `_suspend_updates` と `_notify_change()` を追加した。

- exact widgetのcallbackもlossy widgetのdirty callbackも共通の抑止判定を通す。
- `replace_config()` 中は全 `handle.value` 更新がeventを発火してもdirty追加／preview要求を
  行わない。
- 置換完了後に抑止を解除する。
- 実viserがprogrammatic update eventを発火するか否かに実装を依存させない。

fake GUIのhandle setterを「value代入時にcallbackを必ず発火する」挙動へ強化し、その条件でも
callback 0回をテストした。

### Presetタブ

`StageBinder` に任意の `preset_tab` builderを追加し、tab順を次へ変更した。

```text
Input → Preset → Render → Backdrop → Floor → Key light → Camera → Backlight → Output
```

ViewerAppのPresetタブには次を追加した。

- stage preset dropdown
- Refresh
- 選択preset概要
  - format version
  - width／height／spp／max depth
  - camera／backlight override有無
  - semantic digest
- `Apply stage preset`

catalogが空の場合は `"(no presets found)"` sentinelと説明を表示し、Applyは明示エラーにする。

### 選択と適用の分離

dropdown変更、Refresh、概要表示はStep 1のfilesystem／config APIだけを使い、binder、worker、
Mitsubaへ触れない。

`Apply stage preset` は次の順で処理する。

1. 選択pathをpreset-root内で再解決する。
2. JSON／StageConfigを再検証する。
3. semantic digest付き `SessionPresetRef` を作る。
4. ここまで成功した後にだけ `binder.replace_config()` する。
5. sourceを記録し、previewを正確に1回要求する。

壊れJSON、wrong schema、欠落／root外pathでは現在のbinder config、dirty state、
`applied_preset`、preview要求回数を変更しない。

### `--preset-root`

viewer CLIへ `--preset-root DIR` を追加した。

rootの既定値とvalidationはStep 1の `resolve_preset_root()` をそのまま使う。

- 明示 `--preset-root` が最優先。
- 未指定かつ `--stage-config` ありならその親directory。
- どちらもなければdemoのchecked-in `presets/`。

viewer module docstringの起動例にも `--preset-root` を追記した。

### AppliedPresetRefの追跡

ViewerAppは最後に適用されたpresetを `SessionPresetRef` として
`self.applied_preset` に保持する。

- startup `--stage-config` がpreset-root内の有効candidateなら初期sourceとして記録する。
- PresetタブのApply成功時にroot相対path＋semantic digestを記録する。
- stage／render GUI fieldをユーザーが編集した時は `_on_stage_change()` でsourceをclearし、
  previewを1回要求する。
- `replace_config()` 中のprogrammatic eventではsourceをclearしない。
- Input Load/Rebuildはstageを変更しないため、既存sourceへ触れない。

これにより、Step 4のSession Saveで実効値と一致しないpreset provenanceを書き出さないための
状態が整った。

## テスト

### Mitsuba不要unit test

`tests/test_mitsuba_stage_viewer_worker.py` を17件から24件へ拡張した。

追加／強化した検証:

- fake handleのprogrammatic `value` 代入でも実viser相当のupdate callbackを発火する。
- `replace_config()` が全field、camera／backlight enabledを置換する。
- 置換前のdirty stateをclearする。
- replace中のcallbackが0回である。
- clampされたGUI表示とは別に、`current()` が元のexact configを返す。
- PresetタブがInputとRenderの間に作られる。
- `--preset-root` のparseと既定 `None`。
- user stage editがapplied sourceをclearし、previewを1回要求する。
- preset概要表示だけではbinder／previewが変化しない。
- Apply成功でconfig全体を置換し、sourceを記録してpreviewを1回要求する。
- 壊れpresetのApplyでconfig、source、previewが不変。

### Mitsuba integration test

`tests/integration/test_mitsuba_stage_viewer.py` に
`test_loaded_stage_preset_drives_preview_and_final_render` を追加した。

- 実 `*.stage.json` をStep 1のresolver／loaderで読む。
- presetのnon-default cameraと `max_depth=15` をStageCoreへ渡す。
- previewがrebuild routeでレンダーできる。
- preview stats、final stats、final `scene-summary.json` がすべてmax depth 15を記録する。

既存のtraverse／rebuild、input transaction、viewer final／headless一致テストも全件再実行した。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q tests/test_mitsuba_stage_viewer_worker.py
24 passed in 0.34s

uv run --group mitsuba-viewer pytest -q \
  tests/integration/test_mitsuba_stage_viewer.py
14 passed in 3.74s

uv run pytest -q --ignore=tests/integration
479 passed in 22.74s

uv run --group mitsuba-viewer pytest -q \
  tests/integration/test_mitsuba_stage_viewer.py \
  tests/integration/test_mitsuba.py \
  tests/integration/test_pipeline_end_to_end.py
31 passed in 7.99s

uv run ruff check \
  examples/pipeline_run/demo/mitsuba_stage_presets.py \
  examples/pipeline_run/demo/mitsuba_viewer_session.py \
  examples/pipeline_run/demo/mitsuba_stage_viewer.py \
  tests/test_mitsuba_stage_presets.py \
  tests/test_mitsuba_viewer_session.py \
  tests/test_mitsuba_stage_viewer_worker.py \
  tests/integration/test_mitsuba_stage_viewer.py
All checks passed!

git diff --check
問題なし
```

### 実viser server起動

既存のnested_material_cube `optical.zarr`、builtin preset root、16x16／spp 1設定で
実際のviewerをport 8098へ起動した。

- Mitsuba scene load完了。
- Input／Presetを含む全widget構築で例外なし。
- viser HTTP／WebSocket serverが `http://127.0.0.1:8098` でlisten開始。
- 12秒後に `timeout` で正常に検証プロセスを終了した（終了code 124は意図したtimeout）。

work／scene成果物は `vdbmat/.local/mitsubagui_improve/p3/step3-startup/` に隔離した。
実ブラウザからのクリック操作はこの環境では行っていない。callback本体はfake GUI unit test、
renderer反映はMitsuba integration testでそれぞれ検証した。

## コミット境界としての判断

Step 3完了地点を独立したコミット境界として適切と判断する。

この境界で次の不変条件が成立する。

- preset catalogの選択とApplyが分離されている。
- 読込失敗では現在のstage／render設定とsourceを変更しない。
- Apply成功時だけ全fieldをexactな1 configとして置換する。
- programmatic置換はcallback stormやdirty化を起こさない。
- Apply成功後のpreview要求は1回だけである。
- sourceは実効configと一致する期間だけ保持され、user editで無効になる。
- preset-root containmentとsemantic digestはStep 1契約を再利用する。
- session用source型はStep 2の `SessionPresetRef` を再利用し、GUI専用形式を作っていない。
- preset由来のconfigが実Mitsuba preview／finalへ反映される。
- Phase 1／2のinput切替、render worker、preset保存、headless再現回帰が維持される。

変更対象:

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`

## 未実施事項

- Step 4: seed引継ぎ、`StageCore.prepare_input_session()` 抽出、`--session-root`、
  GUI Session Save/Load、startup `--session` 復元。
- Step 5: `mitsuba_stage_demo.py --session`、viewer／headless session画素一致、README、
  Phase 3実bundle総合検証。

Step 1／2のpure moduleはread-only利用で変更していない。
`mitsuba_stage.py` schema、`mitsuba_stage_demo.py`、canonical exporter／pipeline／
`src/vdbmat` も変更していない。
