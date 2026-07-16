# mitsubagui_improve Phase 3 実装計画 — Stage preset読込とviewer session manifest

作成日: 2026-07-16

## この計画の位置づけ

本計画は `.devdocs/vision/mitsubagui_improve/roadmap.md` の Phase 3 を、
Phase 2完了時点の実装へ接続するための実装計画である。

Phase 1で `StageConfig` 1.1と `max_depth` のGUI／headless再現契約が完成し、
Phase 2でcanonical run bundle／単体 `optical.zarr` のカタログ、transactionalな
入力切替、session世代guard、入力別work directoryが完成した。Phase 3ではこの上に、
次の2つを追加する。

1. 許可ルート以下の既存 `*.stage.json` をGUIから選び、明示的に適用する。
2. 入力、実効stage、render transport、Mitsuba variant、seedを1つのversioned
   viewer session manifestとして保存し、GUIとheadlessの双方で検証付き再生する。

材料mappingの選択・再生成はPhase 4で扱う。本フェーズでは既存
`optical.zarr` のconsumerであるという境界を維持する。

参照した前提資料:

- `README_QUICK.md`
- `.local/local_env_memo.md`
- `.devdocs/vision/mitsubagui_improve/roadmap.md`
- Phase 1／2の実装planとPhase 2の `report1.md`〜`report5.md`
- Phase 2完了時点の `mitsuba_stage.py`、`mitsuba_stage_inputs.py`、
  `mitsuba_stage_viewer.py`、`mitsuba_stage_demo.py` と関連テスト

## 前提調査（確認済み事実）

### StageConfigとpreset契約

- `mitsuba_stage.py` の `StageConfig` はrender、backdrop、floor、key light、
  camera override、backlight overrideを保持する。
- writerは `vdbmat.stage-config/1.1.0` を全field明示で出力する。readerは部分指定を
  受け付け、旧1.0 presetには `render.max_depth=8` を補完する。
- unknown key、未対応version、型違い、範囲外値は `StageConfigError` になる。
- viewerは起動時の `--stage-config` を読めるが、起動後にpresetを選択／適用する
  GUIはない。
- `StageBinder` は起動時configを `base` とし、量子化を伴うwidgetについて
  per-field dirty trackingを行う。現在は構築後に別の `StageConfig` を一括反映する
  APIを持たない。

### Phase 2の入力sessionとtransaction境界

- `StageCore` の交換単位は `InputSession` であり、volume、入力別work directory、
  preview scene、final cache、seedを保持する。
- `StageCore.load_input()` は
  `validate → prepare → load → smoke → swap` を単一render-worker job内で実行する。
  swap前の失敗では旧sessionを維持し、失敗した一時directoryを破棄する。
- 入力切替後も呼出時の `StageConfig` を維持し、`session_generation` により旧previewの
  publishを抑止する。
- 現在のseedは各 `InputSession` に入るが、常に
  `MitsubaExportConfig().seed`（現状 `20260628`）から作られ、CLI／GUIからは指定できない。
- Mitsuba variantは `StageCore` 構築時に選ばれ、既定は `llvm_ad_rgb`。既にロード済みの
  Mitsuba sceneを保持したままvariantを安全にhot switchする契約はない。

### Viewer GUIとCLI

- viewerの位置引数は初期 `optical.zarr` またはrun bundleで、`--input-root` 未指定時は
  初期入力の親directoryをカタログrootとする。
- Inputタブはdropdown、Refresh、概要、`Load / Rebuild` を持つ。選択と適用は分離済み。
- Outputタブはpreset保存pathとfinal PNG pathを任意のserver-local文字列として持つ。
- `RenderWorker` はpreviewと明示jobを1 threadで直列化する。session loadのZarr digest
  検証とscene構築もこのworkerへ載せられる。
- `mitsuba_stage_demo.py` は単体 `optical.zarr`、stage preset、variantを引数で受けるが、
  run bundle、viewer session、seed引数はまだ受けない。

### 利用できるdigest実装

- `vdbmat.pipeline.sha256_file()` は `sha256:<64 hex>` 形式で単一fileをhashする。
- `vdbmat.pipeline.zarr_store_sha256()` はZarr store配下の相対pathとfile内容を決定的順序で
  foldし、store全体のdigestを返す。
- stage presetには既存のdigest APIがない。JSONの空白や旧version／部分指定にdigestが
  依存しないよう、readerで完全な `StageConfig` に正規化してからcanonical JSONをhashする
  helperが必要である。

### ローカル検証境界

- Mitsuba検証はホストの `uv run --group mitsuba-viewer` で実行できる。
- OpenVDB／BlenderはDocker限定だが、本Phaseの変更範囲には含まれない。
- 動作確認成果物は `.local/mitsubagui_improve/p3/` に置き、git管理しない。

## 規模判定

**大規模**と判定する。

理由は、単なるpreset dropdown追加ではなく、versioned schema、複数rootに対する
containment、file／Zarr digest検証、GUI stateの一括置換、入力sessionとのtransaction、
viewer起動経路、headless再生経路を同時に整合させる必要があるためである。

ただし変更先は引き続きdemo-trackへ閉じる。canonical volume schema、pipeline、
exporterの公開契約、`src/vdbmat` のrenderer非依存境界は変更しない。

## ゴール

- `--preset-root` 以下のstage presetをGUIで列挙・Refresh・概要確認できる。
- presetの選択だけでは設定を変えず、`Apply stage preset` 成功時だけ全GUI fieldへ
  反映し、previewを1回発行する。
- 現在の入力、実効stage、render設定、variant、seedを
  `vdbmat.viewer-session/1.0.0` として保存できる。
- sessionに含まれる全参照は許可root相対pathとし、input／presetのdigestを保存・検証する。
- session読込は入力sceneのprepare・smoke renderまで完了してから現在sessionとGUI設定を
  一括commitし、失敗時は入力、画像、GUI値、選択状態を維持する。
- sessionをviewer起動時およびheadless demoで再生できる。
- 同一variant、seed、入力digest、実効stage／render設定で、viewer finalとheadless PNGが
  画素完全一致する。

## 決定事項

### 新moduleの責務

demo directoryへ次の2moduleを追加する。いずれもviser／Mitsubaをimportしない。

`mitsuba_stage_presets.py`:

```text
PresetCandidate
├── root_relative: str
└── path: Path

resolve_preset_root(cli_root, initial_stage_config) -> Path
scan_preset_catalog(root) -> list[PresetCandidate]
resolve_preset(root, user_path) -> PresetCandidate
load_preset(candidate) -> StageConfig
stage_config_digest(config) -> str
describe_preset(candidate) -> PresetSummary
```

`mitsuba_viewer_session.py`:

```text
ViewerSession
ResolvedViewerSession
ViewerSessionError(stage, message)

viewer_session_from_dict(document) -> ViewerSession
viewer_session_from_json(path) -> ViewerSession
viewer_session_to_dict(session) -> dict
write_viewer_session(path, session) -> None
resolve_viewer_session(session, input_root, preset_root) -> ResolvedViewerSession
```

session moduleはschemaのparse／serializeと参照解決／digest照合を担当し、scene生成やGUI更新は
行わない。viewerとheadlessは同じresolverを使い、検証規則を二重実装しない。

### `--preset-root` とpreset catalog

- `--preset-root DIR` をviewerへ追加する。
- 未指定時は、`--stage-config` があればその親directory、なければdemo directory直下の
  `presets/` を既定rootとする。
- `scan_preset_catalog()` はroot以下の `*.stage.json` regular fileを再帰列挙し、
  resolve後にroot外へ出るsymlinkを除外する。結果はPOSIX相対path昇順とする。
- 一覧走査ではsuffixとcontainmentだけを確認し、全presetのJSON parseは行わない。
  選択中の概要表示またはApply時にだけparseする。
- 直接指定も `Path.resolve()` 後の `is_relative_to(resolved_root)` を必須とし、絶対path、
  `..`、root外symlink、存在しないfile、suffix違いを明示的に拒否する。

PresetタブをInputタブの次、Renderタブの前に追加し、次を置く。

- preset dropdown
- Refresh
- format version、実効render値、camera/backlight override有無、semantic digestの概要
- `Apply stage preset`

dropdown変更／Refresh／概要表示はpreviewを要求しない。Applyはcandidateを再解決・再parseし、
成功後にのみbinderへ反映する。読込失敗時は現在のGUI値、`StageBinder.base`、dirty set、
previewを一切変更しない。

### StageBinderの一括置換

`StageBinder.replace_config(config)` を追加する。

- callback抑止flagを有効にして全widget値を更新する。
- `base = config`、`dirty.clear()` とし、量子化widgetは「表示は近似、未編集時の実効値は
  読み込んだexact値」という既存契約を維持する。
- camera／backlightのenabled state、radiance分解、direction分解も同時に更新する。
- 更新完了後にcallback抑止を解除する。メソッド自身はpreviewを要求しない。
- 呼出側がcommit後に `_schedule_preview()` を正確に1回だけ呼ぶ。

全 `on_update` callbackは共通の抑止判定を通す。viserがprogrammaticなvalue更新でeventを
発火するか否かに依存しない実装とする。

### Stage presetのsemantic digestとsource追跡

stage digestは、読込後の完全な `StageConfig` を `stage_config_to_dict()` で1.1形式へ
正規化し、key順を固定したcompact JSONのUTF-8 bytesへSHA-256を適用する。

- 空白、改行、object key順には依存しない。
- 1.0／部分presetは、補完後の実効値が同じなら同じdigestになる。
- digest形式は既存と同じ `sha256:<64 hex>` とする。

ViewerAppは最後に適用したpresetのroot相対pathとdigestを任意の
`AppliedPresetRef` として保持する。preset適用後にstage／renderのGUI fieldが1つでも
編集された時点でこの参照をclearする。入力切替だけではstageが変わらないためclearしない。
これによりsessionへ「現在値と一致しないpreset」を出典として記録しない。

### Viewer session schema 1.0

format名は `vdbmat.viewer-session`、format versionは `1.0.0` とする。
writerは全必須fieldを明示し、readerはunknown key、型違い、unsupported version、
不正digestを拒否する。

代表形:

```json
{
  "format": "vdbmat.viewer-session",
  "format_version": "1.0.0",
  "input": {
    "kind": "run-bundle",
    "path": "catalog/nested_material_cube",
    "optical_sha256": "sha256:...",
    "run_manifest_sha256": "sha256:..."
  },
  "stage": {
    "effective": {
      "format": "vdbmat.stage-config",
      "format_version": "1.1.0",
      "backdrop": {},
      "floor": {},
      "key_light": {},
      "camera": null,
      "backlight": null
    },
    "effective_digest": "sha256:...",
    "preset": {
      "path": "stage-highkey.stage.json",
      "digest": "sha256:..."
    }
  },
  "render": {
    "width": 512,
    "height": 512,
    "spp": 128,
    "max_depth": 16
  },
  "mitsuba": {
    "variant": "cuda_ad_rgb",
    "seed": 20260628
  }
}
```

上例の `{}` は説明用省略であり、writerは各非render stage sectionの全fieldを明示する。

schema上の単一の正本を次のように定める。

- `input.path` は `--input-root` 相対のPOSIX path。`kind` は
  `run-bundle`／`optical-zarr` のいずれか。
- `input.optical_sha256` は、どちらのkindでも実際に描画する `optical.zarr` store全体の
  `zarr_store_sha256()`。
- run bundleでは `run_manifest_sha256` を必須とし、standaloneではfield自体を禁止する。
- `stage.effective` は全非render sectionを明示したinline stage-configであり、
  `render` sectionを含めてはならない。
- top-level `render` がwidth／height／spp／max_depthの唯一の正本。読込時に
  inline stageと結合して完全な `StageConfig` を作る。
- `stage.effective_digest` は、結合後の完全な `StageConfig` のsemantic digest。
- `stage.preset` は現在値が最後に適用したpresetと一致する場合だけ付く任意のprovenance。
  読込時はpathとdigestを検証するが、実効値は必ずinline configを使う。
- `mitsuba.variant` は現行の `llvm_ad_rgb`／`cuda_ad_rgb`、seedは0以上の整数。

inline実効値を常に保存するため、presetを移動せずともstage内容自体はmanifestから確認できる。
ただし `stage.preset` が記録されているsessionでは、その参照も再現契約の一部とし、欠落／
digest不一致を黙って無視しない。

### portable pathと許可root

session v1は絶対pathを保存しない。

- input pathは `--input-root` 相対。
- preset provenance pathは `--preset-root` 相対。
- pathは空文字、絶対path、`.`、`..` component、NULを拒否し、resolve後containmentも検証する。
- 現在入力が `--input-root` 外の初期input sentinelである場合、`Save session` は
  「inputを含む `--input-root` で再起動すること」という診断を出して保存しない。
- git管理用サンプル／fixtureにローカル絶対pathを書かない。

GUIからsession file自体を任意pathで読ませないため `--session-root DIR` も追加する。

- 未指定時、`--session FILE` があればその親directory、なければ `--work-dir` を使う。
- InputタブのLoad session pathとOutputタブのSave session pathはsession-root相対で解決し、
  同じcontainment規則を適用する。
- session gallery／session catalogは作らない。path textとLoad／Save buttonだけとする。

`--session-root` はロードマップに明記されたcatalog機能の追加ではなく、GUIのserver-local
path入力を許可rootへ閉じるための境界である。

### Session保存

Outputタブへ次を追加する。

- session path（既定 `viewer.session.json`、session-root相対）
- `Save session`

保存jobは明示操作として次を行う。

1. 現在入力を `--input-root` 内の `InputCandidate` として再解決し、live sessionの
   `optical_zarr` と同じ実体であることを確認する。
2. `optical.zarr` 全体をhashする。bundleなら `run.json` もhashする。
3. `binder.current()`、現在variant、live session seed、任意のpreset sourceから
   `ViewerSession` を組み立てる。
4. schema round-trip検証後、同directoryの一時fileへwrite＋flushし、`os.replace()` で
   原子的にpublishする。

hash中は `session save: digest input…` とstatusへ出す。既存renderと競合しないよう
render workerへsubmitする。失敗時に既存session fileをtruncateしない。

### Session読込とtransactional commit

Inputタブへ次を追加する。

- session path（session-root相対）
- `Load session`

読込はrender worker上の単一jobで次を実行する。

```text
parse          : session JSON schemaとinline StageConfigを検証
resolve        : input-root／preset-root内で参照を解決
verify         : optical store、run.json、任意presetのdigestを照合
prepare        : 新input sessionのPLY／base preview生成（session config／seed）
load           : preview scene load
smoke          : session config／seedで低spp render
commit         : InputSession、binder config、選択値、preset sourceを一括更新
```

Phase 2のロジックを複製しないため、`StageCore.load_input()` からswap前までを
`StageCore.prepare_input_session(..., seed=...)` として抽出する。

- 既存 `load_input()` はprepare helper＋`swap_session()` の互換wrapperとして残し、
  Phase 2のAPI／テストを維持する。
- 通常のInput Load/Rebuildはseed未指定時に現在sessionのseedを引き継ぐ。
- session loadはmanifest seedを新 `InputSession` へ渡す。
- runtimeの `manifest.variant != core.mi.variant()` はresolve段階で拒否し、
  `--session` でviewerを再起動する診断を出す。ロード済みsceneを跨ぐvariant hot switchは
  行わない。
- commit前の失敗ではcore session、session generation、binder base／dirty／widget値、
  input dropdown、preset source、preview pixelsを変更しない。
- commitではcallback抑止下でbinderを置換し、prepared inputをswapし、選択値とsourceを
  更新してからpreviewを1回だけ要求する。
- commit処理自体で予期しない例外が起きた場合に備え、旧config／選択／sourceをsnapshotし、
  swap前ならそのまま、swap後なら旧 `InputSession` へ戻せる内部rollbackを用意する。

digest不一致は `session load failed at verify: input optical digest mismatch` のように、
参照種別、期待値、実値を含む診断にする。欠落、kind違い、root外、preset不一致も同様に
段階名付きで報告する。

### Viewer起動時のsession復元

viewerへ `--session SESSION` と `--seed SEED` を追加し、初期入力位置引数は
`--session` 使用時に限り省略可能にする。

- legacy mode: 初期入力位置引数が必須。`--seed` 未指定時は従来どおり
  `MitsubaExportConfig().seed`、variant未指定時は `llvm_ad_rgb`。
- session mode: `--session` と `--input-root` を必須とし、Mitsuba import／StageCore構築前に
  manifestとdigestを検証する。input、StageConfig、variant、seedをmanifestから取得する。
- session modeで明示 `--variant`／`--seed` がmanifestと異なる場合はsilent overrideせず
  起動エラーにする。同値の明示は許可する。
- sessionにpreset provenanceがある場合は `--preset-root` も必要。inlineのみなら
  preset-root既定値でよい。
- 従来の `INITIAL_INPUT [--stage-config ...]` 起動は完全維持する。

起動前にvariantを解決するため、保存sessionからのGUI再起動ではGPU／CPUを含む実効variantを
復元できる。起動済みGUIでvariantの異なるsessionをLoadした場合だけ再起動を要求する。

### Headless session replay

`mitsuba_stage_demo.py` にsession modeを追加し、render本体を
`render_stage(optical_zarr, output_png, stage, variant, seed)` の再利用可能な関数へ整理する。

CLIは次の2形を受ける。

```text
# 既存形（完全互換）
mitsuba_stage_demo.py -- INPUT OUTPUT [--stage-config ...] [既存override...]

# session再生形
mitsuba_stage_demo.py -- --session SESSION --input-root ROOT \
  [--preset-root ROOT] --output-png OUTPUT
```

- session modeはviewerと同じresolverでpath／digest／実効configを検証する。
- session modeでは `--stage-config`、width／height／spp／max-depth／checker-scaleのoverrideを
  併用不可とする。manifestと異なる条件を「session再生」と呼ばない。
- legacy modeへ `--seed` を追加し、未指定時の既定値は従来値を維持する。
- run bundleのsession参照はresolverが実 `optical.zarr` へ解決する。
- scene summaryとPIXELSTATSへ実効seed／variantも出し、比較時の取り違えを防ぐ。

### 変更しないもの

- `vdbmat.stage-config` のformat/versionと既存presetの意味。
- canonical volume、run bundle、optical mapping、pipeline configのschema。
- `prepare_mitsuba_scene()`／`MitsubaExportConfig`／`src/vdbmat` の公開契約。
- Phase 2のInputカタログ判定・transactional swap・世代guardの基本動作。
- Blender／OpenVDB経路。

## 対象ファイル

### 主変更

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_presets.py`（新規）
  - preset catalog、containment、parse、概要、semantic digest
- `vdbmat/examples/pipeline_run/demo/mitsuba_viewer_session.py`（新規）
  - viewer session 1.0 dataclass、strict reader/writer、参照解決、digest照合
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
  - preset/session/seed CLI
  - `StageBinder.replace_config()` とcallback抑止
  - Presetタブ、InputのLoad session、OutputのSave session
  - `StageCore.prepare_input_session()` 抽出、seed引継ぎ、transactional session commit
  - startup session復元
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`
  - render関数抽出、session headless mode、seed対応
- `README_QUICK.md`
  - preset Apply、session Save/Load、root、digest、headless再生手順

### テスト

- `vdbmat/tests/test_mitsuba_stage_presets.py`（新規、Mitsuba不要）
- `vdbmat/tests/test_mitsuba_viewer_session.py`（新規、Mitsuba不要）
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`
  - CLI、binder一括置換、callback抑止、source invalidation
- `vdbmat/tests/test_mitsuba_stage_demo.py`
  - legacy/session CLIの排他とseed
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
  - session transaction、digest拒否、seed、GUI final
- 必要なら `vdbmat/tests/integration/test_mitsuba_stage_session_replay.py`（新規）
  - viewer／headless画素一致を独立させる場合

## 実装ステップ

### Step 1 — Preset catalogとsemantic digest

1. `mitsuba_stage_presets.py` にroot解決、catalog、containment、candidate解決、parse、
   概要、semantic digestを実装する。
2. legacy 1.0、partial 1.1、完全1.1を正規化し、意味が同じconfigのdigestが一致することを
   unit testで固定する。
3. root外symlink、絶対／`..`、壊れJSON、wrong format/versionを拒否する。
4. このstepではviewerへ配線しない。Mitsuba／viserなしで契約を先に固定する。

### Step 2 — Session schema、portable path、digest resolver

1. `mitsuba_viewer_session.py` に1.0 dataclass、strict parser、serializer、atomic writerを
   実装する。
2. inline stage＋renderの結合、effective digest、input kind別field規則、variant／seedを
   unit testで固定する。
3. input-root／preset-root相対pathのlexical validationとresolve後containmentを実装する。
4. standalone／bundleの正しいdigest、Zarr変更、run.json変更、preset変更／欠落を実fileで
   検証する。
5. resolverの返り値を、viewer／headlessがそのまま使える
   `(candidate, optical_zarr, stage_config, variant, seed, preset_ref)` 相当へ固定する。

### Step 3 — Binder置換とPresetタブ

1. `StageBinder` の全callbackを抑止可能な共通経路へ揃え、`replace_config()` を実装する。
2. exactなbase／dirty契約、camera/backlight切替、量子化field未編集保持、callback 0回を
   fake GUI unit testで確認する。
3. `--preset-root`、Presetタブ、Refresh／概要／ApplyをViewerAppへ追加する。
4. Apply成功でconfig全体を置換しpreviewを1回だけ発行、失敗で現在値不変を確認する。
5. AppliedPresetRefを保持し、GUI編集時だけclearする。

### Step 4 — Session Save/Loadとstartup復元

1. `InputSession` のseedを外から指定可能にし、通常のinput切替は現在seedを維持する。
2. `StageCore.prepare_input_session()` を抽出し、既存 `load_input()` を互換wrapperにする。
3. `--session-root`、InputのLoad session、OutputのSave sessionを追加する。
4. parse→resolve→verify→prepare→load→smoke→commitをworkerへ配線し、button disable、
   段階status、失敗時rollback、成功時1 previewを実装する。
5. `--session` startup modeと `--seed` を追加し、Mitsuba import前にvariant／input／config／
   seedを解決する。
6. Phase 2のinput dropdown／Load/Rebuild、旧起動、preset保存、final renderを回帰確認する。

### Step 5 — Headless replay、統合検証、文書

1. `mitsuba_stage_demo.py` のrender本体を関数化し、session modeを同じresolverへ接続する。
2. non-default `max_depth`／seedとinline stageを持つsessionについて、viewer finalと
   headless PNGの画素完全一致を確認する。
3. bundle／standalone、preset sourceあり／なし、digest不一致、variant不一致を
   integration testで検証する。
4. README_QUICKへ標準手順を追記する。
5. 実bundle（nested_material_cube、marble）と複数presetでGUI再起動／headless再生を行い、
   成果物を `.local/mitsubagui_improve/p3/` へ隔離する。

## テスト計画

### Mitsuba不要のunit test

`test_mitsuba_stage_presets.py`:

- `*.stage.json` のみを相対path昇順で列挙する。
- root外symlinkを除外し、直接解決でも拒否する。
- file symlinkでも解決先がroot内なら許可する。
- 壊れJSON／wrong schemaはcatalogには現れるがdescribe／loadで失敗する。
- 1.0 partialと同じ実効値の1.1 fullが同じsemantic digestになる。
- 実効値が1 field変わるとdigestが変わる。
- `--preset-root` の明示／stage-config親／builtin presets既定値を確認する。

`test_mitsuba_viewer_session.py`:

- writer→reader round-tripで全fieldが一致する。
- unknown top-level／section key、unsupported version、boolを整数として渡すseed、
  不正digest、stage.effective内renderを拒否する。
- bundleだけが `run_manifest_sha256` を要求し、standaloneでは禁止する。
- absolute、空、`.`、`..`、root外symlinkを拒否する。
- input／run manifest／preset digest一致でresolveできる。
- Zarr chunk、run.json、presetの意味的fieldを変更すると対象を名指しして拒否する。
- presetの空白／key順だけの変更はsemantic digestが一致する。
- inline stage＋renderの結合結果とeffective digestを検証する。
- atomic writer失敗時に既存fileが維持される。

`test_mitsuba_stage_viewer_worker.py` 追加分:

- legacy CLI既定、`--preset-root`、`--session-root`、`--seed`、session modeの必須／排他。
- `StageBinder.replace_config()` が全fieldを置換し、dirtyをclearする。
- programmatic更新でon_updateが発火してもpreview callbackを呼ばない。
- 置換直後の `current()` が量子化前のexact configを返す。
- preset Apply後のGUI編集でsourceがclearされ、入力切替ではclearされない。

### Mitsuba integration test

- preset Apply後のpreview/finalが適用config（非既定max depth含む）を使う。
- 壊れpreset Applyで直前のconfigとpreviewが維持される。
- bundle A＋config A＋seed Aからsessionを保存し、standalone Bを表示中にloadすると、
  A／config A／seed Aへ復元される。
- session load後も次の通常input切替がsession seedを維持する。
- digest不一致（optical、run.json、preset）、欠落、root外、runtime variant不一致で
  core session、generation、binder config、preview pixelsが不変。
- commit後はsession generationが1回だけ進み、旧preview結果がpublishされない。
- session load直後のstage編集が従来のtraverse／rebuild分類で動く。
- final scene summaryのmax depth、variant、seedがmanifest実効値と一致する。

### Viewer／headless再現テスト

同じinput digest、stage effective digest、render、variant、seedで次を比較する。

- viewer coreのfinal PNG
- `mitsuba_stage_demo.py --session` のheadless PNG

同一variant内ではHDR／PNG pixelを完全一致で比較する。CPUとGPUのvariant間は画素一致を
要求せず、別variant sessionを同じものとして扱わないことだけを確認する。

### End-to-end／手動確認

- `--preset-root` にdefault／highkeyと壊れpresetを置き、選択だけでは変化せずApplyでだけ
  previewが変わることを確認する。
- nested_material_cubeでstageとmax depth、non-default seedを設定しsession保存する。
- viewer終了後、`--session` で再起動し、input／GUI値／variant／seedを確認する。
- marble表示中に上記sessionをLoadし、nestedへ安全に戻ることを確認する。
- input Zarrまたはpresetを変更したcopyでdigest mismatchを確認し、旧previewが残ることを
  確認する。
- 保存sessionをheadless再生し、viewer finalとのpixel digest一致を確認する。
- 成果物、検証JSON、PNG、scene directoryは `.local/mitsubagui_improve/p3/` のみに置く。

### 静的検査

- 変更Pythonへの `ruff check`
- Mitsuba不要unit tests
- `uv run --group mitsuba-viewer` のviewer／headless integration tests
- Phase 1／2の関連回帰tests
- `git diff --check`
- git管理対象に `.local`、絶対path入りsession、巨大Zarr／PNGが混入していないことの確認

## 実施順序

```text
preset catalog／semantic digest（pure）
    ↓
viewer session schema／resolver（pure）
    ↓
StageBinder一括置換＋Presetタブ
    ↓
StageCore prepare抽出＋Session Save/Load transaction
    ↓
startup session復元
    ↓
headless session replay
    ↓
統合検証・README
```

先にviser／Mitsuba非依存のschema、path、digest契約を固定する。GUIを先行させて、
「保存はできるが別環境でpath解決できない」「読込後にdigest不一致が判明する」状態を
中間成果としない。

## 非ゴール

- optical mappingの選択・適用、`material.zarr` からの再生成（Phase 4）。
- sessionへのZarr、run manifest、stage preset本文の埋め込み。
- GUI上の材料係数編集。
- OpenVDB直接入力。
- 複数sessionのgallery、履歴、比較表示。
- 起動済みviewerでのMitsuba variant hot switch。
- session参照のabsolute path mode。
- Zarr digest cache、署名、リモートartifact取得。
- preset適用時のmerge UI（選択presetは完全な実効StageConfigとして適用する）。
- session schemaの `mapping` field先行追加（Phase 4でversion互換を保って拡張する）。
- canonical exporter／pipeline／volume schemaの変更。

## 完了条件

- preset-root以下の `*.stage.json` がGUIに列挙され、Refreshできる。
- preset選択だけでは何も適用されず、Apply成功時だけ全stage／render fieldが置換される。
- 壊れpreset、root外path／symlinkのApplyが拒否され、現在値とpreviewが維持される。
- session manifest 1.0がinput、inline実効stage、render、variant、seed、digestをstrictに
  round-tripする。
- sessionは絶対pathを含まず、input-root／preset-root相対参照だけを保存する。
- bundle／standalone双方のsessionを保存・再読込できる。
- input optical、bundle run.json、任意presetの欠落／digest不一致がscene構築前に検出される。
- session load失敗時に旧input、session generation、GUI値、preview、preset sourceが不変。
- session load成功時に入力とGUI設定が1 transactionとして切り替わり、previewが1回発行される。
- viewerを `--session` で再起動するとinput、stage、max depth、variant、seedが復元される。
- runtime variant不一致は再起動案内付きで拒否され、hot switchしない。
- `mitsuba_stage_demo.py --session` で同sessionをheadless再生できる。
- 同一variantのviewer finalとheadless PNGが画素完全一致する。
- 従来の位置引数＋任意stage preset起動、Input Load/Rebuild、Save preset、Render finalが
  回帰testを通る。
- renderer依存と動作確認成果物がoptional／`.local` 境界内に留まる。

## リスクと打ち切り条件

### Zarr store全体のhashが遅い

session Save/Loadは明示操作であり、worker上で段階statusを出す。まず正確な
`zarr_store_sha256()` を使う。代表bundleでhash時間がscene prepareより支配的でも、
本Phaseでは不検証cacheを追加しない。run bundleのasset宣言だけを信用して実体hashを省く
最適化も行わず、実測値をPhase 5へ引き継ぐ。

### Binder一括更新が大量previewを発行する

programmatic updateでviser eventが発火する前提／しない前提のどちらにも依存せず、共通の
callback抑止flagを使う。fake GUIでeventを強制発火して0 callbackを確認できなければ、
Preset／Session GUI配線へ進まない。

### Session commit途中でGUIとcoreがずれる

scene準備とsmokeはcommit前に完了させる。commit対象をInputSession、binder、input selection、
preset sourceに限定し、旧state snapshotを持つ。integration testで各verify／prepare段階を
故意に失敗させ、旧state完全維持を確認する。rollback不能なGUI APIが判明した場合は、
commitを「binder置換成功後にcore swap」の順へ固定し、swap前のbinder失敗を復元できるまで
session Loadを公開しない。

### Preset provenanceと実効値が乖離する

sessionの正本はinline effective configとrenderであり、presetは任意の検証対象provenanceに
限定する。適用後のどの設定編集でもsourceをclearする。source追跡を確実にできない場合は
preset fieldを出力せずinlineのみを保存し、誤った出典を残さない。

### Variantを実行中に復元できない

Mitsuba objectを保持したままvariantは切り替えない。startup `--session` ではimport前に復元し、
runtime mismatchは明示拒否する。この制約でGUI再起動後の再現条件は満たせる。hot switchは
別Phaseの独立設計なしに追加しない。

### Root相対pathでは現在入力を保存できない

Phase 2互換のためroot外初期inputは表示できるが、portable sessionには保存しない。
診断で正しい `--input-root` を案内する。absolute fallbackを暗黙導入しない。

### Digest付きpresetを移動するとsessionが読めない

preset sourceは任意であり、編集後sessionはinlineのみになる。一方、source付きsessionは
そのfileの存在も契約に含めるため、移動／欠落を明示エラーにする。inlineへ黙ってfallbackする
挙動は「参照欠落を検出する」というPhase 3の目的に反するため採らない。
