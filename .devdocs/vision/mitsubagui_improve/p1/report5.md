# mitsubagui_improve Phase 1 実施報告 — Step 5 / Phase 1完了

`plan.md` のStep 5（Preset・文書）とend-to-end回帰まで完了した。Step 1〜4で
構築したstage-config、headless、viewer core、GUI bindingをsample presetと文書へ
反映し、既定／非既定depthの再現性を統合検証した。これによりPhase 1全体の完了条件を
満たしたため、ここをPhase完了のコミット境界と判断した。

## 変更内容

### Sample preset

- `vdbmat/examples/pipeline_run/demo/presets/stage-default.stage.json`
  - `format_version`を`1.1.0`へ更新した。
  - 完全schema例として`render.max_depth: 8`を明示した。
  - `stage_config_from_json()`で読むと`StageConfig()`と完全一致することを確認した。
- `vdbmat/examples/pipeline_run/demo/presets/stage-highkey.stage.json`
  - `format_version`を`1.1.0`へ更新した。
  - 部分指定例という既存の役割を維持し、`max_depth`は意図的に省略した。
    新readerによって既定値8が補完される。

両presetを実readerで読み、実効depthが8、再serialize時のcurrent versionが1.1.0で
あることを確認した。

### README_QUICK

- stage設定の説明をresolution / spp / max depthへ更新した。
- headless例へ`--max-depth`を追加した。
- 組み込み既定値 < preset < 明示CLI overrideの優先規則と、
  `--width/--height/--spp/--max-depth/--checker-scale`を明記した。
- current writerは1.1.0、readerは旧1.0.0も受理してmax_depth=8を補完すること、
  1.0.0文書には新fieldを混在できないことを明記した。
- max depthは正整数で、既定8、大きな値はrender時間を増やし得ることを明記した。
- GUIが将来計画という古い説明を、現在のbrowser GUIとpreset保存／headless replayの
  説明へ更新した。
- max depth変更はpreviewのplanned rebuildであり、PLY/gridを再生成しないこと、
  finalはresolution/depth差でre-prepareしてscene summaryへ実効値を残すことを
  説明した。
- headless/viewerのstatus・PIXELSTATSから実効max depthを確認できることを追記した。

## End-to-end自動回帰

`vdbmat/tests/integration/test_mitsuba_stage_viewer.py`へ、計画どおりbuilt-in
`nested_material_cube`を使うGUI相当の再現テストを追加した。

各`max_depth`（8、16）について次を実行する。

```text
nested material manifest
    ↓ optical mapping / optical.zarr
StageConfig → StageCore.save_preset()
    ├─ StageCore.render_final() → viewer.png
    └─ mitsuba_stage_demo.py --stage-config → headless.png
```

- width=12、height=12、spp=2、同一variant/seedで比較した。
- depth 8: viewer finalとheadless replayのPNGが`np.array_equal=True`。
- depth 16: viewer finalとheadless replayのPNGが`np.array_equal=True`。
- 両方でheadless scene summaryのmax depthが指定値と一致した。
- 両方でheadless PIXELSTATS logに実効depthが出た。

見た目の差そのものではなく、同一条件のGUI final/headless再現性を合否条件にする
計画上の原則を満たしている。

## 実入力marble確認

ローカルの複雑入力`.local/marble/bundle/optical.zarr`を、highkey preset、
32x32、spp2、`llvm_ad_rgb`でdepth 8／16それぞれheadless描画した。成果物はすべて
`.local/mitsubagui_improve/p1/`へ隔離した。

```text
depth 8:
PIXELSTATS max_depth=8 min=0 max=6.11288 mean=0.22904 std=0.406941
PNG sha256 e8ecf92420d3b08434ac01b74bd94a8785c152819d26fbac775372d1da5b78ed
scene-summary max_depth=8

depth 16:
PIXELSTATS max_depth=16 min=0 max=7.98559 mean=0.270737 std=0.607657
PNG sha256 872f52c1be1595f7593ef4d706a6b1a366bab1bd8c61663acdbd021acee6ac57
scene-summary max_depth=16
```

2画像は`np.array_equal=False`、8-bit読込時の最大絶対差255だった。効果量は合否条件に
していないが、この実入力ではtransport設定による画像差も実際に観測できた。
MitsubaからASCII PLYのperformance warningは出たが、load/renderは双方正常終了した。

## 検証結果

実行場所は`vdbmat/`。

```text
uv run pytest -q \
  tests/test_mitsuba_stage_config.py \
  tests/test_mitsuba_stage_demo.py \
  tests/test_mitsuba_stage_viewer_worker.py
29 passed

uv run --group mitsuba pytest -q tests/integration/test_mitsuba_stage_viewer.py
5 passed in 2.95s

uv run --group mitsuba-viewer pytest -q
405 passed, 2 skipped in 27.57s

uv run ruff check <関連8ファイル>
All checks passed!

git diff --check
問題なし
```

全体実行のskip 2件はlocal hostに`pyopenvdb`がないための既知の
`test_blender_cycles.py` / `test_openvdb.py`で、今回の変更とは無関係である。

## Phase 1完了条件との対応

- `RenderSettings.max_depth`が既定8の正整数契約: 達成。
- stage-config 1.1 writerと1.0/1.1互換reader: 達成。
- GUI Renderタブで変更しSave presetへ保存: 達成。
- preview interactive/settled、final、headlessへ同じ値を反映: 達成。
- preview depth変更=`rebuild`、後続の連続変更=`traverse`: 達成。
- final summaryとGUI/headless status/logで実効値を確認: 達成。
- 旧1.0 presetをdepth=8として読込: 達成。
- depth=8の既定挙動維持: 達成。
- 非既定depthでGUI相当finalとheadless replayが同一: 達成（全画素一致）。
- canonical exporter、volume、boundary mesh、material mappingを変更しない: 達成。
- local検証成果物を`.local`へ隔離: 達成。

## 次Phaseへの引き継ぎ

Phase 1に未実施事項はない。次は親roadmapのPhase 2（許可root以下の既存
`optical.zarr`／canonical bundle catalogとtransactional input切替）である。
Phase 2着手時は本Phaseで確立したrender設定契約とpreview/final rebuild境界を維持し、
入力切替のwork directory lifecycleを別planで設計する。
