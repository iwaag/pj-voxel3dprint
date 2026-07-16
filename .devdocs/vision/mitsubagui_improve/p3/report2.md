# mitsubagui_improve Phase 3 実施報告 — Step 2

`plan.md` の Step 2（viewer session schema、portable path、digest resolver）まで完了した。
`vdbmat.viewer-session/1.0.0` のstrict reader/writer、root相対path、bundle／standalone
input digest、任意preset provenance、atomic writer、viewer／headless共用resolverを、
viser・Mitsuba非依存の新moduleとして実装した。

この時点でPhase 3の永続化・再生契約がpure unit testで固定されたため、Step 1に続く
独立したコミット境界として適切と判断した。Step 3以降のBinder／Presetタブ、
StageCore transaction、GUI Session Save/Load、headless CLI配線は未着手である。

## 変更内容

### 新module `mitsuba_viewer_session.py`

`vdbmat/examples/pipeline_run/demo/mitsuba_viewer_session.py` を新設した。
viser・Mitsubaはimportしない。

主な型:

- `SessionInputRef`
  - `InputKind`、input-root相対path、`optical.zarr` digest。
  - run bundleのみ `run_manifest_sha256` を必須とする。
- `SessionPresetRef`
  - preset-root相対pathとsemantic digest。
- `ViewerSession`
  - input ref、完全な実効 `StageConfig`、effective digest、variant、seed、任意preset ref。
- `ResolvedViewerSession`
  - 検証済み `InputCandidate`／`PresetCandidate` と実 `optical.zarr` path、
    StageConfig、variant、seedをviewer／headlessへ渡す返り値。
- `ViewerSessionError(stage, message)`
  - `capture`／`parse`／`resolve`／`verify` の段階名付き診断。

主なAPI:

```text
create_viewer_session(...)
viewer_session_from_dict(...)
viewer_session_from_json(...)
viewer_session_to_dict(...)
write_viewer_session(...)
resolve_viewer_session(...)
```

### `vdbmat.viewer-session/1.0.0` strict schema

top-levelは次の6fieldを必須かつ唯一のkeyとした。

```text
format
format_version
input
stage
render
mitsuba
```

- formatは `vdbmat.viewer-session`、versionは `1.0.0` の完全一致。
- unknown key、missing key、wrong type、unsupported versionを拒否する。
- digestは `sha256:<64 lowercase hex>` のみ受理する。
- variantは `llvm_ad_rgb`／`cuda_ad_rgb`、seedはboolを除く0以上の整数。

### Stageとrenderの単一正本

session JSONでは `stage.effective` から `render` を除き、top-level `render` を
width／height／spp／max depthの唯一の正本とした。

- `stage.effective` はformat/versionとbackdrop、floor、key light、camera、backlightを
  必須とする。
- 各非render sectionの全fieldも必須にした。session再生が将来のdefault値変更へ
  依存しない。
- camera／backlightは `null` または全field明示objectだけを受ける。
- readerはinline stageとtop-level renderを結合して完全な `StageConfig` を作る。
- `stage.effective_digest` は結合後configのsemantic digestと一致しなければ拒否する。
- preset provenanceがある場合、`stage.preset.digest` はeffective digestとも一致することを
  必須にした。実効値と異なるpresetを出典として記録できない。

writerは既存 `stage_config_to_dict()` の全field明示1.1 documentからrenderを分離するため、
既存stage schemaを複製せず、session内でも同じfield名とvalidationを維持する。

### Portable path契約

`input.path` と `stage.preset.path` は正規化済みPOSIX相対pathだけを受理する。

次を拒否する。

- 空path／`.`。
- absolute path。
- `..` component。
- backslash separator。
- 重複slash、末尾slash等の非正規表現。
- NUL。

JSON parse時のlexical検証に加え、resolverはPhase 2の `resolve_candidate()` とStep 1の
`resolve_preset()` を再利用し、resolve後のroot containmentとsymlink境界も検証する。

### Input digest

`create_viewer_session()` は既存のproject共通helperを使用する。

- bundle／standalone共通:
  `zarr_store_sha256(candidate.optical_zarr)`。
- run bundleのみ:
  `sha256_file(candidate.path / "run.json")`。

resolverはscene構築前に実体を再hashし、期待値／実値付きの段階診断で不一致を拒否する。
run bundleとstandaloneのkindがpath実体と一致しない場合もresolve段階で拒否する。

### Preset provenance検証

sessionにpreset refがある場合だけ `preset_root` を要求する。

1. Step 1の `resolve_preset()` でpath／containmentを検証する。
2. `load_preset()` でStageConfig schemaを検証する。
3. `stage_config_digest()` でsemantic digestを照合する。

JSONの空白やkey順だけの変更は許容するが、presetの実効field変更、欠落、root外pathは
明示エラーになる。描画に使う正本はsession内のinline configであり、preset refは
検証対象provenanceとして扱う。

### Atomic writer

`write_viewer_session()` は次の手順でpublishする。

1. serializer出力をreaderへ戻し、schema round-tripを検証する。
2. 出力directory内に一時fileを作る。
3. UTF-8／indent 2／末尾改行でwriteし、flush＋`fsync()` する。
4. `os.replace()` で最終pathへ原子的に置換する。
5. 失敗時は一時fileを削除し、既存session fileを維持する。

## テスト

`vdbmat/tests/test_mitsuba_viewer_session.py` を新設し、43ケースを追加した。

### Schema／round-trip

- 全field、non-default render／stage、preset refを含むwriter→reader一致。
- top-level／input／stage／render／mitsubaのunknown key拒否。
- unsupported version、bool seed、不正digestの拒否。
- stage.effective内render、非render field欠落の拒否。
- effective digest mismatch、preset/effective digest不一致の拒否。
- bundleのrun digest必須、standaloneでのrun digest禁止。

### Portable path

- 空、`.`、absolute、`..`、backslash、重複slash、末尾slash、NULを拒否。
- preset pathにも同じ規則を適用。
- input-root外symlinkを既存Phase 2 containment経由で拒否。

### Digest resolver

- standalone sessionのcapture／resolve。
- run bundle sessionのcapture／resolveとrun manifest digest。
- Zarr storeへfileを追加した場合のoptical digest mismatch。
- `run.json` 変更時のrun manifest digest mismatch。
- input kind mismatch、input欠落。
- preset JSONのformatting変更はsemantic一致として許可。
- preset実効値変更、preset-root欠落、preset file欠落を拒否。

### Atomic writer

- 親directory作成、末尾改行、JSON read-back一致、一時file非残存。
- `os.replace()` 失敗時に既存fileが維持され、一時fileが削除される。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q tests/test_mitsuba_viewer_session.py
43 passed in 0.20s

uv run pytest -q \
  tests/test_mitsuba_stage_presets.py \
  tests/test_mitsuba_viewer_session.py
63 passed（Step 1: 20、Step 2: 43）

uv run pytest -q --ignore=tests/integration
472 passed in 21.75s

uv run ruff check \
  examples/pipeline_run/demo/mitsuba_stage_presets.py \
  examples/pipeline_run/demo/mitsuba_viewer_session.py \
  tests/test_mitsuba_stage_presets.py \
  tests/test_mitsuba_viewer_session.py
All checks passed!

git diff --check
問題なし

新規fileは git diff --no-index --check でも問題なし
```

本StepはMitsuba／viser非依存のschema、filesystem、hash処理だけであるため、
Mitsuba integration test、ブラウザ操作、render成果物生成は実施していない。

## コミット境界としての判断

Step 2完了地点を独立したコミット境界として適切と判断する。

この境界で次の不変条件が単独で成立する。

- viewer sessionのformat/versionと全fieldの責務が固定されている。
- inline stageとrenderの単一正本が明確で、全実効値が明示される。
- input／preset参照に絶対pathを保存できない。
- lexical path検証とresolve後containmentの二層でroot境界が守られる。
- bundle／standaloneのinput kindと必要digestが区別される。
- input bytes、run manifest、preset意味内容の不一致をscene生成前に検出できる。
- preset provenanceとinline実効configが乖離できない。
- atomic writer失敗時に既存manifestを破壊しない。
- viewer／headlessが共通で利用できるresolved objectを返す。
- 新moduleはviser／Mitsuba非依存で、viewerやcanonical coreの挙動を変更していない。

変更対象は次の2fileだけである。

- `vdbmat/examples/pipeline_run/demo/mitsuba_viewer_session.py`
- `vdbmat/tests/test_mitsuba_viewer_session.py`

## 未実施事項

- Step 3: `StageBinder.replace_config()`、callback抑止、`--preset-root`、Presetタブ、
  Apply、AppliedPresetRef追跡。
- Step 4: seed引継ぎ、`prepare_input_session()` 抽出、`--session-root`、GUI Save/Load、
  startup `--session` 復元。
- Step 5: `mitsuba_stage_demo.py --session`、viewer／headless画素一致、README、実bundle検証。

Step 1の `mitsuba_stage_presets.py` は読取利用のみで変更していない。
`mitsuba_stage.py`、`mitsuba_stage_viewer.py`、`mitsuba_stage_demo.py`、
`mitsuba_stage_inputs.py`、canonical exporter／pipeline／`src/vdbmat` も変更していない。
動作確認用 `.local` 成果物は生成していない。
