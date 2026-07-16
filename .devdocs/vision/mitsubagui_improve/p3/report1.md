# mitsubagui_improve Phase 3 実施報告 — Step 1

`plan.md` の Step 1（preset catalogとsemantic digest）まで完了した。
この時点で、presetの列挙、許可root containment、選択candidateの解決、strictな
StageConfig読込、表示用概要、意味ベースのdigestというPhase 3後続処理の入力契約が、
viewer・viser・Mitsubaへ触れずにunit testで固定された。Step 2以降のsession schema、
Presetタブ、Session Save/Load、headless replayは未着手である。

## 変更内容

### 新module `mitsuba_stage_presets.py`

`vdbmat/examples/pipeline_run/demo/mitsuba_stage_presets.py` を新設した。
viser・Mitsubaはimportしない。

- `PresetCandidate`、`PresetSummary`、`PresetCatalogError`。
- `resolve_preset_root(cli_root, initial_stage_config)`:
  - 明示 `--preset-root` が最優先。
  - 未指定かつ初期 `--stage-config` がある場合はその親directory。
  - どちらもない場合はdemo directoryのchecked-in `presets/`。
  - 選ばれたrootがdirectoryでなければ明示エラー。
- `scan_preset_catalog(root)`:
  - root以下の `*.stage.json` regular fileを再帰列挙する。
  - resolve後にroot外へ出るfile／directory symlinkを除外する。
  - root内fileを指すsymlinkは候補として許可する。
  - 結果はroot相対POSIX path昇順で決定的にする。
- `resolve_preset(root, user_path)`:
  - GUI catalog keyとしてroot相対pathだけを受ける。
  - absolute path、空path、parent traversal、suffix違い、欠落、非file、root外symlinkを
    `PresetCatalogError` で拒否する。
- `load_preset(candidate)`:
  - JSON objectを読み、既存 `stage_config_from_dict()` でformat/version/unknown key/
    type/rangeを検証する。
  - JSON parse、wrong format、unsupported version等をcandidate名付きの
    `PresetCatalogError` に統一する。
- `describe_preset(candidate)`:
  - source format version、実効width/height/spp/max depth、camera/backlight override有無、
    semantic digestを返す。

### Catalog走査とdocument検証を分離した

catalog走査ではsuffix、file種別、containmentだけを確認し、JSON本文をparseしない。
そのため壊れた `*.stage.json` もdropdown候補には現れ、選択時の概要またはApply時に
「not valid JSON」「format must be ...」等の具体的な診断を出せる。

これはPhase 2 input catalogと同じく、「一覧から黙って消す」のではなく、軽量な列挙と
選択対象の完全検証を分ける境界である。viewerへのApply配線はStep 3で行う。

### StageConfigのsemantic digest

`stage_config_digest(config)` を追加した。

1. 読込済み `StageConfig` を `stage_config_to_dict()` で現行1.1、全field明示のdocumentへ
   正規化する。
2. key順固定・compact separatorのJSONへserializeする。
3. UTF-8 bytesをSHA-256でhashし、既存project規約と同じ
   `sha256:<64 hex>` 形式で返す。

このため、次はdigestへ影響しない。

- JSONの空白／改行。
- object key順。
- 省略されたdefault field。
- 1.0 presetで暗黙に補完される `max_depth=8` と、1.1で明示された同じ実効値。

一方、backdrop fieldやrender `max_depth` 等の実効値変更はdigestを変える。

## テスト

`vdbmat/tests/test_mitsuba_stage_presets.py` を新設し、20ケースを追加した。
Mitsuba／viserは不要である。

主な検証:

- `*.stage.json` だけをnested path込みの相対path昇順で列挙する。
- suffixが同じdirectoryや無関係fileは除外する。
- 壊れJSONはcatalogへ残り、describe時に具体的エラーになる。
- root外file symlinkの列挙除外／直接解決拒否。
- root内file symlinkの列挙／直接解決許可。
- absolute、`..`、空、suffix違い、欠落pathの拒否。
- wrong format／unsupported versionの拒否。
- legacy 1.0 partial、1.1 partial、1.1 fullが同一実効configなら同一digestになる。
- JSON formatting／key順がdigestに影響しない。
- stage／render実効値変更がdigestを変える。
- PresetSummaryが部分presetをdefault補完して報告する。
- preset rootの明示、初期preset親、builtin既定値、非directory拒否。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q tests/test_mitsuba_stage_presets.py
20 passed in 0.06s

uv run pytest -q --ignore=tests/integration
429 passed in 21.01s

uv run ruff check \
  examples/pipeline_run/demo/mitsuba_stage_presets.py \
  tests/test_mitsuba_stage_presets.py
All checks passed!

git diff --check
問題なし

新規fileは git diff --no-index --check でも問題なし
```

本StepはMitsuba sceneやviewerへ配線しないpure filesystem/config処理であるため、
Mitsuba integration test、ブラウザ操作、ローカルrender成果物生成は実施していない。
既存のMitsuba不要suite全件を回帰実行した。

## コミット境界としての判断

Step 1完了地点を独立したコミット境界として適切と判断する。

この境界で次の不変条件が単独で成立する。

- preset rootの既定値とdirectory検証が決まっている。
- catalog keyはroot相対POSIX pathで、列挙順は決定的である。
- catalog列挙と選択document検証の責務が分離されている。
- absolute／parent traversal／root外symlinkからserver-local file境界が保護される。
- StageConfig読込は既存schema readerを再利用し、別schemaを作っていない。
- legacy／partial／formatting差を正規化するsemantic digest契約がunit testで固定されている。
- 新moduleはviser／Mitsuba非依存で、viewerやcanonical coreの挙動を変更していない。

変更対象は次の2fileだけである。

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_presets.py`
- `vdbmat/tests/test_mitsuba_stage_presets.py`

## 未実施事項

以下は計画どおり次のコミット境界以降に残している。

- Step 2: `vdbmat.viewer-session/1.0.0` schema、portable path、input／preset digest
  resolver、atomic writer。
- Step 3: `StageBinder.replace_config()`、callback抑止、Presetタブ、Refresh／概要／Apply、
  AppliedPresetRef追跡。
- Step 4: seed引継ぎ、`prepare_input_session()` 抽出、Session Save/Load transaction、
  startup session復元。
- Step 5: headless session replay、viewer／headless画素一致、README、実bundle検証。

`mitsuba_stage.py` のschema、`mitsuba_stage_viewer.py`、`mitsuba_stage_demo.py`、
`mitsuba_stage_inputs.py`、canonical exporter／pipeline／`src/vdbmat` は変更していない。
動作確認用 `.local` 成果物も生成していない。
