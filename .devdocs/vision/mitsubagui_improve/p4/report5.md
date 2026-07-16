# mitsubagui_improve Phase 4 実施報告 — Step 5

`plan.md` の Step 5（headless replay、統合検証、文書）を完了した。
mapping付きviewer sessionを `mitsuba_stage_demo.py --session` で再生成・検証・描画でき、
cache無しの初回生成とcache有りの再利用の双方で、viewer finalとheadless PNGが
画素完全一致することを統合テストで固定した。

## 変更内容

### Headless mapping replay

`mitsuba_stage_demo.py` のsession modeへ次を追加した。

- `--mapping-root` と `--mapping-work-root`。mapping付きsessionでは両方必須、
  mapping無しsessionでは不要。
- mapping-root containmentとsemantic digest検証はviewerと同じ
  `resolve_viewer_session()` を使用する。
- `regenerate_optical()` で派生canonical bundleを生成または再利用した後、
  `verify_derived_optical()` でsessionがpin留めした派生digestを照合する。
- mapping work rootとinput rootの重なりを拒否する。
- `MAPPING ... cache=generated|reused` を標準出力へ記録する。
- 既存のsession override禁止、variant／seed一致要求、mapping無しsession経路を維持する。

### Work rootに依存しない派生digest

cache無しheadless replayの統合テストで、同じsource＋mappingでもviewerとheadlessが
異なるwork rootを使うと `optical.zarr` digestが変わる問題を検出した。

原因は、`regenerate_optical()` がin-memory `PipelineConfig.output_path` に派生bundleの
絶対pathを設定しており、その値を含むconfig digestがvolume provenanceへstampされる
ためだった。出力pathをwork root相対の決定的なbundle名へ変更し、work rootを
`run_pipeline(..., base_dir=...)` 側へ渡すよう修正した。これにより、科学入力とmappingが
同じなら異なるwork rootでもconfig内容と派生 `optical.zarr` digestが一致する。

この境界は `test_regenerate_optical_is_digest_stable_across_work_roots` で固定した。

### 検証用mappingと切替回帰

`phase0-provisional-materials-v1-tinted.optical-mapping.json` を追加した。
`transparent-resin` のRGB吸収を `[45.0, 4.0, 1.0] /m` とした、視覚比較用の
`provisional-uncalibrated` mappingであり、測定済み材料値ではない。

checked-inの `nested_material_cube` sourceからcanonical bundleを生成し、viewerの
transaction APIで次を再起動なしに往復する統合テストを追加した。

1. tinted mapping
2. `(bundle optical as-is)`
3. checked-in provisional mapping

tintedはas-isと異なるoptical contentになり、provisional再生成はas-isと係数配列が
一致することを確認した。provenanceが異なるためZarr store全体のdigest一致は要求しない。

### Viewer finalとheadlessの再現

mapping付きsessionについて次を1テスト内で確認した。

- viewer側の派生volumeを同一stage、variant、seedでfinal renderする。
- 空のheadless work rootへ再生成し、派生digestを照合してrenderする
  （`cache=generated`）。
- 同じheadless work rootで再実行しcacheを再利用する（`cache=reused`）。
- 2枚のheadless PNGがいずれもviewer final PNGと画素完全一致する。

### README

`README_QUICK.md` に以下の標準手順を追加した。

- mappingを `.local/mitsubagui_improve/p4/` へコピーして編集する。
- mapping dropdownで概要・digestを確認する。
- Refreshだけではsceneを変えず、Load/Rebuildで明示適用する。
- as-is／provisional／tintedを比較する。
- mapping編集後にRefresh→Load/Rebuildし、sessionを保存する。
- mapping付きsessionを `--mapping-root`／`--mapping-work-root` 付きでheadless再生する。
- 派生bundleのcache、provenance、root非重複条件を確認する。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q --ignore=tests/integration
557 passed in 39.54s

uv run pytest -q tests/integration/test_mitsuba_stage_viewer.py
30 passed, 1 warning in 24.96s

uv run ruff check <Step 4/5のdemo・test 7ファイル>
All checks passed!

uv run ruff format --check <同7ファイル>
7 files already formatted

git diff --check
問題なし
```

integration warningはStep 4報告と同じ、既存テスト終了時にviser background threadが
終了済みevent loopへstatusをpublishする
`PytestUnhandledThreadExceptionWarning` である。全30テストは成功している。

ブラウザを人手操作する確認は行っていないが、Load/Rebuildの同一transaction APIを
使ったnested cubeの往復切替、実Mitsubaによるviewer/headless render、cache無し／有り、
session digest検証までを自動統合テストで通している。検証成果物はpytestの一時directory
だけに生成され、git管理領域へ動作確認出力は残していない。

## Phase 4完了状態

Step 1〜5の実装と自動検証が完了した。mapping catalog、非破壊派生bundle生成とcache、
viewer-session 1.1、GUI Load/Rebuild、GUI/startup/headless session replay、サンプル、
READMEの標準手順が揃っている。
