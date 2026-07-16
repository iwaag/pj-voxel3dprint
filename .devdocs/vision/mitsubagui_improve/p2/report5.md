# mitsubagui_improve Phase 2 実施報告 — Step 5

`plan.md` の Step 5（統合検証・文書）を完了した。Phase 2で追加した入力カタログ、
transactional Load/Rebuild、session世代guard、per-input work directoryを、追加の
Mitsuba統合テストと実bundle検証で固定した。また `README_QUICK.md` のviewer節へ
`--input-root`、Inputタブ、安全な切替手順を追記した。

## 変更内容

### Mitsuba統合テスト

`vdbmat/tests/integration/test_mitsuba_stage_viewer.py` に次の2ケースを追加した。

- `test_load_input_round_trip_renders_and_separates_final_artifacts`
  - canonical bundle A → standalone optical store B → bundle Aの往復切替を行う。
  - 各swap後にpreview/finalをレンダーできることを確認する。
  - `session_generation` が2まで単調増加し、3 sessionすべてが異なるwork
    directoryを使うことを確認する。
  - 全sessionの `final_scene/scene-summary.json` が個別に残り、切替中も
    非既定 `max_depth=13` が維持されることを確認する。
- `test_load_input_rejects_invalid_candidates_without_changing_live_preview`
  - optical asset typeを宣言したままarray manifestを壊したZarr、material
    volume、root外を指すsymlinkを実際の `StageCore.load_input()` に渡す。
  - 3ケースとも `validate` 段階の `InputLoadError` になり、現在sessionと
    `session_generation` が不変であることを確認する。
  - 失敗前後のpreviewを再レンダーし、画素が完全一致することを確認する。

既存のworker unit testが持つsession世代guard（旧sessionのpreview結果をpublish
しない）、latest-wins、例外回復、work directory連番の検証も全件再実行した。

### README_QUICK

browser viewerの起動例へ `--input-root` を追加し、次を文書化した。

- 初期位置引数はcanonical run bundleまたはstandalone optical `*.zarr` を受理する。
- `--input-root` 未指定時は初期入力の親directoryを使う。
- Inputタブはserver-local catalogであり、ブラウザuploadは行わない。
- material-only storeとroot外へ解決されるsymlinkは候補に含めない。
- dropdown変更／Refreshは再構築せず、`Load / Rebuild` のみが適用操作である。
- validate・prepare・load・smokeが成功してからswapし、失敗時は現在scene、preview、
  stage/render設定を維持する。
- 成功時もstage/render設定（`max_depth`を含む）を維持し、新previewを発行する。

## 実入力による検証

実在する次の2つのcanonical run bundleを
`vdbmat/.local/mitsubagui_improve/p2/step5/catalog/` へ実体コピーし、検証した。

- `nested_material_cube`
- `marble`

同catalogに、manifestを意図的に壊した `broken.zarr`、containedなmaterial store
へのsymlink、root外bundleへのsymlinkも用意した。検証成果物はすべて
`vdbmat/.local/mitsubagui_improve/p2/step5/` に隔離しており、git管理対象外である。

実行結果:

1. catalog走査は `broken.zarr`、`marble`、`nested_material_cube` を列挙した。
   material storeとroot外symlinkは列挙しなかった。壊れたstoreはasset typeだけを
   軽量判定するcatalogには現れ、完全validationをLoad/Rebuildまで遅延する設計どおり。
2. `nested_material_cube → marble → nested_material_cube` の往復切替は、両方向とも
   `validate → prepare → load → smoke → swap` を完了した。session generationは
   0 → 1 → 2となり、work directoryは入力／世代ごとに分離された。
3. 切替後に24×24, spp 1のpreviewと32×32, spp 2のfinalをレンダーし、実効
   `max_depth=12` が全結果で維持された。
4. `broken.zarr` は `vdbmat.arrays.g.unit: expected '1'`、material storeは
   `not a run bundle or optical.zarr`、root外symlinkは
   `input resolves outside --input-root` として、すべて `validate` 段階で拒否された。
   3失敗後もcurrent sessionは往復後のnested inputのまま維持された。
5. viewer coreから `step5.stage.json` を保存し、同presetとnested入力を
   `mitsuba_stage_demo.py` でheadless再生した。viewer finalとheadless PNGは
   画素完全一致した。
6. 実bundle directoryを位置引数、catalogを `--input-root` に指定して実際の
   viewerをport 8099で起動し、Inputタブを含むGUI構築が完了してHTTP 200を返す
   ことを確認後、正常終了した。

主要成果物:

- `validation.json`: catalog、切替段階、世代、診断、画素一致結果
- `marble-final.png`
- `nested-viewer-final.png`
- `nested-headless.png`
- `step5.stage.json`
- `work/inputs/*`: session別preview/final scene
- `nested-headless_scene/`: headless再生scene

この実行環境ではブラウザを対話操作する機構がないため、実ブラウザからのdropdown・
Refresh・buttonクリックそのものは未実施である。代わりに、実viser serverの起動／
HTTP応答／widget構築と、button callbackが呼ぶのと同じ `load_input()` 経路を実入力で
検証した。GUI callbackの配線自体はStep 4のunit/integration testを再実行している。

## 自動テスト・静的検査

実行場所は `vdbmat/`。

```text
uv run --group mitsuba-viewer pytest -q \
  tests/integration/test_mitsuba_stage_viewer.py
13 passed in 4.13s

uv run pytest -q --ignore=tests/integration
409 passed in 22.36s

uv run --group mitsuba-viewer pytest -q \
  tests/integration/test_mitsuba_stage_viewer.py \
  tests/integration/test_mitsuba.py \
  tests/integration/test_pipeline_end_to_end.py
30 passed in 7.67s

uv run ruff check \
  examples/pipeline_run/demo/mitsuba_stage_inputs.py \
  examples/pipeline_run/demo/mitsuba_stage_viewer.py \
  tests/test_mitsuba_stage_inputs.py \
  tests/test_mitsuba_stage_viewer_worker.py \
  tests/integration/test_mitsuba_stage_viewer.py
All checks passed!

git diff --check
問題なし
```

## Phase 2完了条件との対応

- catalog列挙・Refresh・Inputタブ・明示的Load/Rebuild: Step 1／4とREADMEで完了。
- bundle／standalone間の往復切替とpreview/final: 本Stepの統合・実入力検証で完了。
- stage/render設定維持: 非既定 `max_depth` を統合・実入力の双方で確認。
- 壊れ入力・非optical・root外path/symlink拒否と旧scene維持: unit／統合／実入力で確認。
- 旧session previewのpublish抑止: worker session-generation testで確認。
- input別work directoryとscene summary分離: 往復統合テストで確認。
- 従来の位置引数起動とbundle位置引数: CLI testと実viewer起動で確認。
- stage-config契約、headless demo、canonical exporter、`src/vdbmat`: 本Stepでは変更なし。

以上により、Phase 2の実装計画は完了した。
