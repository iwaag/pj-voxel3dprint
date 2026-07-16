# mitsubagui_improve Phase 3 実施報告 — Step 4

`plan.md` の Step 4（Session Save/Loadとstartup復元）まで完了した。
viewer session manifestをGUIの保存／読込、起動時復元、StageCoreのinput transactionへ接続し、
non-default seedを入力切替後も維持できるようにした。

session読込はdigest検証とsmoke renderが終わるまでlive stateを変更せず、成功時だけinput、
StageConfig、seed、dropdown、preset sourceを一括commitする。unit test、Mitsuba integration、
実viser server起動が通ったため、Step 4完了地点を独立したコミット境界として適切と判断した。

Step 5のheadless `--session` replay、viewer/headless画素一致、README更新は未着手である。

## 変更内容

### StageCoreのprepare／swap分離とseed契約

- `StageCore` constructorと `_build_session()` でseedを外部指定可能にした。
- `prepare_input_session()` を抽出し、validate／prepare／load／smokeまでをlive sessionへ
  触れずに実行するようにした。
- 既存 `load_input()` はprepare後にswapする互換wrapperとして維持した。
- 通常のInput Load/Rebuildでseed未指定の場合は、現在の `InputSession.seed` を引き継ぐ。
- preview／finalのMitsuba export configにもlive seedを渡し、scene summaryと実render seedを
  一致させた。
- `current_session` read-only propertyを追加し、GUI側が現在input／seedを安全に参照できるようにした。

### Session rootとGUI Save

viewerへ `--session-root DIR` を追加した。GUIで指定するsession pathはroot相対に限定し、
absolute path、`..`、resolve後のroot escape、root外symlinkを拒否する。

Outputタブへsession pathと `Save session` を追加した。保存jobはrender worker上で次を行う。

1. 現在選択を `--input-root` 内のcandidateとして再解決する。
2. candidateの実 `optical.zarr` とlive sceneのinputが一致することを確認する。
3. optical store、bundleなら `run.json` をdigestする。
4. binderの実効config、Mitsuba variant、live seed、任意preset sourceからmanifestを作る。
5. round-trip検証後に一時file＋`os.replace()`で原子的にpublishする。

初期inputがinput-root外にあるlegacy起動ではportable pathを作れないため、session保存を明示的に
拒否する。hash中はbuttonをdisableし、statusへ段階を表示する。

### Transactional Session Load

Inputタブへsession pathと `Load session` を追加し、単一worker jobへ次を接続した。

```text
parse → resolve → verify → prepare → load → smoke → commit
```

- parse／portable path／input kind／digest／preset provenanceはStep 2の共通resolverを使う。
- resolverへstage callbackを追加し、viewerがresolveとverifyを区別して表示できるようにした。
- runtime variantがmanifestと異なる場合はsceneを作らず、`--session` での再起動を案内する。
- prepareではmanifest configとseedで新 `InputSession` を構築しsmoke renderする。
- commit前の失敗ではcore session、generation、binder、dropdown、preset source、previewを変更しない。
- commitではbinder置換、session swap、input選択、preset sourceを更新し、成功後にpreviewを1回だけ
  要求する。
- commit中の予期しない例外に備え、旧session／generation／config／選択／sourceへ戻し、prepared
  work directoryを破棄するrollbackを実装した。

### Startup Session復元

viewer CLIへ `--session SESSION` と `--seed SEED` を追加し、`--session` 使用時だけ初期input
位置引数を省略可能にした。

- legacy modeは従来どおり位置引数必須で、variant既定 `llvm_ad_rgb`、seed既定
  `MitsubaExportConfig().seed` を維持する。
- session modeは `--input-root` 必須で、位置引数と `--stage-config` の併用を拒否する。
- session JSON、input／preset root、全digest、config、variant、seedを
  `StageCore` 構築前、したがってMitsuba import前に解決する。
- 明示 `--variant`／`--seed` はmanifestと同値なら許可し、不一致なら起動エラーにする。
- preset provenanceを持つsessionでは明示 `--preset-root` を要求する。
- `--session-root` 未指定のsession起動ではstartup session fileの親directoryをGUI rootにする。

## テスト

### Mitsuba不要unit test

`tests/test_mitsuba_stage_viewer_worker.py` に次を追加した。

- `--session`、`--session-root`、`--seed` のparse。
- session modeのinput-root必須、位置引数／stage-config排他、負seed拒否。
- session pathのroot-relative containmentとload／save path解決。

Step 2 resolverの既存schema／digest testsも再実行した。

### Mitsuba integration test

`tests/integration/test_mitsuba_stage_viewer.py` に次を追加した。

- non-default seedで起動したcoreのprepareがlive session／generationを変更しない。
- prepare後のswapと、その次の通常Input Load/Rebuildがseedを維持する。
- standalone B表示中にAのsessionを読み、A／config／seedへ一括復元する。
- optical digest不一致でcore、generation、binder、選択が不変である。
- 成功時のstage列が計画どおりで、generationが1回だけ進む。
- startup session resolverがinput／config／variant／seed／session-rootを復元する。
- final `scene-summary.json` のseedがmanifest seedと一致する。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q \
  tests/test_mitsuba_stage_viewer_worker.py \
  tests/test_mitsuba_viewer_session.py
70 passed in 0.53s

uv run --group mitsuba-viewer pytest -q \
  tests/integration/test_mitsuba_stage_viewer.py
16 passed in 3.21s

uv run pytest -q --ignore=tests/integration
482 passed in 22.57s

uv run --group mitsuba-viewer pytest -q \
  tests/integration/test_mitsuba_stage_viewer.py \
  tests/integration/test_mitsuba.py \
  tests/integration/test_pipeline_end_to_end.py
33 passed in 7.83s

uv run --group dev ruff check <Step 1〜4関連Python>
All checks passed!

git diff --check
問題なし
```

### 実viser server起動

既存のnested_material_cube bundleを使い、8x8／spp 1、明示input-root／session-root、
新しいSession Save/Load controlsを含むviewerをport 8099へ起動した。

- Mitsuba scene load完了。
- Session Loadを含むInputタブ、Session Saveを含むOutputタブのwidget構築で例外なし。
- viser HTTP／WebSocket serverが `http://127.0.0.1:8099` でlisten開始。
- 20秒後に `timeout` で検証プロセスを終了した（終了code 124は意図したtimeout）。

成果物は `vdbmat/.local/mitsubagui_improve/p3/step4-startup/` に隔離した。最初に試した古い
Phase 1 artifactは現行Zarr manifest以前の形式で読めなかったため、現行Phase 2 bundleへ切り替えた。
この失敗はコード変更やgit管理成果物を発生させていない。

## コミット境界としての判断

Step 4完了地点を独立したコミット境界として適切と判断する。

この境界で次の不変条件が成立する。

- sessionは許可root相対pathとdigestに固定され、保存はatomicである。
- session loadはverifyとsmoke render完了前にlive stateを変更しない。
- 読込成功時だけinput、stage、seed、sourceが一括commitされる。
- 読込失敗時はsession generationとpreviewを含む従来stateが維持される。
- 通常input切替は現在seedを維持する。
- variant hot switchは行わず、異なるvariantには再起動を要求する。
- startup sessionはMitsuba import前に検証される。
- 従来の位置引数起動、Input Load/Rebuild、preset Apply／Save、final renderが回帰testを通る。

変更対象:

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
- `vdbmat/examples/pipeline_run/demo/mitsuba_viewer_session.py`
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
- `.devdocs/vision/mitsubagui_improve/p3/report4.md`

## 未実施事項

- Step 5: `mitsuba_stage_demo.py --session`、legacy demoの `--seed`、viewer／headless session
  画素一致、README_QUICK更新、実bundle総合検証。
- GUIの実ブラウザクリック操作。transaction本体はMitsuba integration、widget構築は実viser起動で
  それぞれ検証した。

canonical volume／pipeline／exporter API、StageConfig schema、`mitsuba_stage_demo.py` は変更していない。
