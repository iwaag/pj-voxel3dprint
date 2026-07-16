# mitsubagui_improve Phase 4 実装計画 — Optical mappingファイル選択とcanonical再生成

作成日: 2026-07-17

## この計画の位置づけ

本計画は `.devdocs/vision/mitsubagui_improve/roadmap.md` の Phase 4 を、
Phase 3完了時点の実装へ接続するための実装計画である。

Phase 1〜3で、`max_depth` を含むrender契約、入力カタログとtransactionalな入力切替、
stage preset適用、`vdbmat.viewer-session/1.0.0` によるGUI／headless再現が完成した。
現在のviewerは既存 `optical.zarr` の純粋なconsumerであり、材料mappingを変更する
手段を持たない。

Phase 4ではこの上に次を追加する。

1. `--mapping-root` 以下の `vdbmat.optical-mapping` JSONをGUIから列挙・Refresh・
   概要確認・選択できるようにする。
2. 選択したmappingをcanonical材料入力へ適用し、新しい派生canonical bundleを
   非破壊・transactionalに生成して、Phase 2と同じscene swapで描画へ切り替える。
3. mapping参照とdigestをviewer sessionへ追加し、GUI／headlessで再現可能にする。

材料係数のGUI編集は行わない。外部エディタでmapping JSONを編集→Refresh→
Load/Rebuildで反映する、というワークフローを成立させることが本フェーズの目的である。

参照した前提資料:

- `README_QUICK.md`
- `.local/local_env_memo.md`
- `.devdocs/vision/mitsubagui_improve/roadmap.md`
- Phase 1〜3の実装planとPhase 3の `report1.md`〜`report5.md`
- `src/vdbmat/pipeline/`（`config.py`、`runner.py`、`artifacts.py`）
- `src/vdbmat/optics/`（`config.py`、`document.py`、`mapping.py`）
- Phase 3完了時点の `mitsuba_stage_inputs.py`、`mitsuba_stage_presets.py`、
  `mitsuba_viewer_session.py`、`mitsuba_stage_viewer.py`、`mitsuba_stage_demo.py`
  と関連テスト

## 前提調査（確認済み事実）

### Optical mapping契約

- `vdbmat.optics.document.load_optical_mapping()` は
  `vdbmat.optical-mapping/1.x` JSONを厳格に読み、unknown field、missing field、
  wrong format/version、`external_id` 混入、型・範囲違反を
  `OpticalMappingError` として拒否する。
- `OpticalMappingConfig.digest` はcanonical JSONへのSHA-256であり、空白・key順に
  依存しない。`configuration_id`、`version`、`calibration_status`、材料ID／名前／
  係数を保持する。
- `map_material_volume_to_optical()` は `_require_palette_coverage()` で、材料volume
  palette内の全material IDがmappingに存在すること、および共有IDの名前が一致する
  ことを検証してから変換する。GUI側で混合則や係数解釈を再実装する必要はない。
- チェックイン済みのmapping文書は
  `vdbmat/examples/pipeline_run/mappings/phase0-provisional-materials-v1.optical-mapping.json`
  の1つ。ローカルには `.local/marble/marble-like.optical-mapping.json` がある。

### Pipelineと run bundle

- `run_pipeline(config, base_dir=...)` はADR-007の固定stage列
  `load → validate/persist material → map-optics → validate/persist optical →
  summarize → (export)` を実行し、一時directory構築＋`os.replace()` による
  atomic publishで bundleを発行する。中断時に部分bundleを残さない。
- `PipelineConfig` の唯一の入力は `direct-voxel` manifest（ADR-009 D1）。
  file-based mappingは `mapping.digest` の宣言を必須とし、`resolve_mapping()` が
  実file digestとの一致を検証する。
- run bundleは `source/` に入力manifestとpayloadのコピーを常に保持し、`run.json` に
  `input_payload_sha256`、`mapping_digest`、`config_digest`、全assetのsha256を記録する。
- `run_id` と canonical成果物は科学入力（config digest、input payload、mapping digest）
  の純関数であり、同一入力の再実行はbyte-equalな `material.zarr`／`optical.zarr` を
  生成する（`created_utc` は `run.json` のみ）。したがって派生bundleの
  `zarr_store_sha256(optical.zarr)` は再現可能なdigestになる。
- 生成される `optical.zarr` のprovenanceには `mapping-digest:sha256:...` と
  `mapping-config:<id>@<version>` が既に記録される（`_restamp` と
  `_output_provenance`）。Phase 4完了条件の1つはpipeline再利用だけで満たされる。

### Phase 3完了時点のviewer

- 入力カタログ（`mitsuba_stage_inputs.py`）は `--input-root` 以下のrun bundleと
  単体 `optical.zarr` を列挙し、containment検証付きで解決する。
  `InputKind` は `RUN_BUNDLE`／`OPTICAL_ZARR` の2値。
- `StageCore.prepare_input_session()` が
  `validate → prepare → load → smoke` をswapなしで実行し、`load_input()` ／
  session load transactionがそれを使う。失敗時は一時directoryを破棄し
  現在sessionを維持する。引数は `(root, user_path, ...)` で、内部で
  `resolve_candidate()` を呼ぶ。
- `InputSession` は `optical_zarr`、入力別work directory、volume、seed、
  preview scene、final cacheを保持するswap単位である。
- `vdbmat.viewer-session/1.0.0`（`mitsuba_viewer_session.py`）はinput参照
  （kind／root相対path／optical digest／bundle時のrun manifest digest）、
  inline実効stage、render、variant、seed、任意preset provenanceをstrictに
  round-tripする。readerは `format_version` の完全一致を要求する。
- `mitsuba_stage_demo.py --session` はviewerと同じ
  `resolve_viewer_session()` で検証してからheadless renderする。
- preset catalog（`mitsuba_stage_presets.py`）が、root解決・再帰列挙・containment・
  遅延parse・semantic digestという本フェーズのmapping catalogと同型のパターンを
  既に確立している。

### ローカル検証境界

- `run_pipeline` とmapping loaderはMitsuba／viser非依存であり、通常の
  `uv run pytest` でテストできる。
- Mitsuba検証はホストの `uv run --group mitsuba(-viewer)` で実行できる。
  OpenVDB／Blenderは本フェーズの変更範囲外。
- 動作確認成果物は `.local/mitsubagui_improve/p4/` に置き、git管理しない。

## 規模判定

**大規模**と判定する。

理由は、mapping catalog（新しい許可root）、pipeline実行を含む長いLoad/Rebuild
transaction、派生bundleのcache／reuse方針、viewer session schemaのversion互換
拡張、headless再生経路を同時に整合させる必要があるためである。

ただし科学ロジックは追加しない。mappingの読込・検証・変換・provenance・
atomic publishはすべて既存 `vdbmat.optics`／`vdbmat.pipeline` の再利用であり、
変更はdemo-trackと `README_QUICK.md` に閉じる。`src/vdbmat` は変更しない。

## ゴール

- `--mapping-root` 以下の `*.optical-mapping.json` をGUIで列挙・Refresh・概要確認
  （configuration id／version／digest／calibration status／材料IDと名前）できる。
- mappingの選択・Refreshだけでは何も再構築せず、`Load / Rebuild` 実行時のみ
  材料再生成とscene swapを行う。
- 再生成は選択canonical bundleを上書きせず、明示されたwork root以下へ新しい派生
  bundleとしてtransactionallyに発行する。
- 同じ材料入力×mapping digestの組み合わせは再生成せずcacheを再利用する。
- mapping JSONを外部エディタで編集後、Refresh→Load/Rebuildで再起動なしに反映できる。
- mapping不正（unknown field、材料不足、名前不一致、digest不整合）はscene構築前に
  段階名付きの明瞭なエラーになり、現在のsceneとpreviewを維持する。
- mapping参照とdigestを含むsessionを保存でき、GUI再起動／headlessで同一条件を
  再構成できる。
- 同一材料入力へ2種類以上のmappingを適用し、GUIを再起動せず描画比較できる。

## 決定事項

### 材料再生成の入力契約 — canonical bundle＋mapping選択、実装は `run_pipeline()` 再利用

roadmapが実装planへ委ねた2経路のうち、**ユーザー契約としては専用経路
（canonical bundleへ選択mappingを適用して派生bundleを発行する）を採用し、
その実装機構として既存 `run_pipeline()` を再利用する**。

- GUIで選ぶのは「Inputタブの現在の入力候補（run bundle）」と「mapping候補」の
  2つであり、`vdbmat.pipeline-config` ファイルをユーザーに選ばせない。
  pipeline-configは `mapping.digest` を宣言必須とするため、「JSONを編集して
  Refreshで反映する」ワークフローと構造的に噛み合わない（編集のたびに
  config側のdigest更新が必要になる）。
- 実装は、選択bundleが `source/` に保持するdirect-voxel manifestを入力とする
  `PipelineConfig` をin-memoryで組み立て、`run_pipeline()` を派生bundle出力先へ
  向けて実行する。mapping参照は `mapping_path`＋Load/Rebuild時に
  `load_optical_mapping()` で計算した現在digestで渡す。
- これによりmapping loader、palette coverage／名前一致検証、mixing rule、
  provenance（mapping digest入り）、run_id、asset checksums、atomic publishを
  一切二重化せずに得る。roadmapのリスク「mapping実行がpipelineロジックを
  二重化する」への回答がこの選定である。
- `material.zarr` へ直接mappingを適用する専用publish経路は実装しない。
  bundleの `material.zarr` はsource manifestからの決定的な派生物であり、
  source経由の再実行と科学的に同値。専用経路はbundle発行ロジックの複製を
  必要とするため採らない。
- 副産物として、派生bundleは完全なcanonical run bundleになるため、既存の
  入力カタログ・検証・session digest計算がそのまま適用できる。

適用対象は `InputKind.RUN_BUNDLE` の入力に限定する。単体 `optical.zarr` 入力は
材料情報を持たないため、mapping選択時のLoad/Rebuildを `validate` 段階で
「mapping適用にはrun bundle入力が必要」という診断付きで拒否する。

### 新module構成

demo directoryへ次の2moduleを追加する。いずれもviser／Mitsubaをimportしない。

`mitsuba_stage_mappings.py` — mapping catalog（preset catalogと同型）:

```text
MappingCandidate
├── root_relative: str
└── path: Path
MappingSummary
├── configuration_id / version / digest
├── calibration_status
└── materials: [(material_id, name), ...]

resolve_mapping_root(cli_root) -> Path
scan_mapping_catalog(root) -> list[MappingCandidate]
resolve_mapping_candidate(root, user_path) -> MappingCandidate
describe_mapping(candidate) -> MappingSummary   # load_optical_mapping()を再利用
```

- rootは `--mapping-root DIR`。未指定時はチェックイン済みの
  `examples/pipeline_run/mappings/` を既定rootとする。
- `*.optical-mapping.json` regular fileを再帰列挙し、resolve後にroot外へ出る
  symlinkを除外する。結果はPOSIX相対path昇順。列挙時はparseせず、概要表示／
  Load/Rebuild時にのみ `load_optical_mapping()` でparseする（編集後のRefresh→
  再選択で常に現在のfile内容が反映される）。
- 直接指定・カタログ経由の双方に `resolve()` 後の containment検証を必須とする。

`mitsuba_stage_regen.py` — 派生bundle生成とcache:

```text
RegenError(stage, message)
DerivedBundle
├── bundle_path: Path
├── optical_zarr: Path
├── mapping_digest: str
├── source_payload_sha256: str
└── reused: bool

locate_bundle_source(bundle_path) -> Path        # run.jsonからsource manifestを特定
derived_bundle_key(source_payload_sha256, mapping_digest) -> str
regenerate_optical(source_bundle, mapping_candidate, work_root,
                   *, on_stage=...) -> DerivedBundle
```

- `locate_bundle_source()` は選択bundleの `run.json` を読み、`source/` 以下の
  direct-voxel manifestを特定し、manifestの実payload digestが `run.json` の
  `input_payload_sha256` と一致することを確認する。不一致・欠落は
  「bundle sourceが壊れている／改変されている」旨の明示エラー。
- `regenerate_optical()` はmappingを `load_optical_mapping()` で読み（現在digestを
  ここで確定）、`PipelineConfig(input=direct-voxel manifest, mapping_path+digest,
  output=work_root内のcache path, validate両方true, exports空)` を組み立てて
  `run_pipeline()` を呼ぶ。GUI独自のmapping処理・簡易混合則は一切持たない。

### 派生bundleのcacheと再利用方針

- 派生bundleは `--mapping-work-root DIR`（未指定時は `<work_dir>/derived`）以下の
  `<入力slug>-<key先頭12桁>/` へ発行する。keyは
  `sha256(source input_payload_sha256 + "\n" + mapping digest)`。
  科学入力が同じなら同じpathになる。
- Load/Rebuild時、cache pathに既存bundleがあれば `run.json` を読み、
  `input_payload_sha256` と `mapping_digest` が一致する場合のみ再利用する
  （`reused=True`）。一致しない・parse不能な残骸は破棄して再実行する。
- 再実行時は同一pathへ `overwrite=True` で発行する。`run_pipeline` のatomic
  publishにより、途中失敗で旧cacheが壊れることはない。
- Zarr全体の再hashによるcache検証は行わない（session save/loadで必要になった
  時点では既存のsession digest経路が担う）。cache判定は `run.json` の宣言digest
  照合までとし、より強い検証の必要性はPhase 5の実測へ委ねる。
- 入力bundle・mapping fileへの書き込みは一切行わない。`--mapping-work-root` が
  `--input-root` 内のbundleと同一pathへ解決される構成は起動時に拒否する。

### GUI: Inputタブへのmapping選択とLoad/Rebuildの拡張

Inputタブの入力dropdown群の下へ次を追加する。

- mapping dropdown。先頭に固定候補 `(bundle optical as-is)` を置き、既定とする。
- Refresh（mapping catalogの再走査。選択・sceneは変えない）
- 選択mappingの概要（configuration id／version／digest／calibration status／
  材料IDと名前の一覧、parse失敗時はその診断）
- 適用は既存の `Load / Rebuild` ボタンに統合する。ボタンを増やさない。

Load/Rebuild transactionを次へ拡張する（render worker上の単一job、各段階を
statusへ表示）。

```text
validate : 入力候補解決。mapping選択時はrun bundle入力であること、
           bundle sourceの特定とpayload digest照合、mapping parse、
           palette coverage／名前一致の事前検査
map      : regenerate_optical()（cache hit時はskipし "map: reused cache" 表示）
prepare  : 派生（またはそのまま）のoptical.zarrからPLY／preview scene構築
load     : preview scene load
smoke    : 低spp render
swap     : 現在sessionと交換、mapping選択状態をcommit
```

- `validate` の事前検査は、bundle source manifestの `materials` 一覧とmapping
  材料一覧の突合（ID包含と名前一致）で行う。これは高速fail用の前段であり、
  正本の検証は `run_pipeline` 内の `map_material_volume_to_optical()` が担う。
- swap前のどの段階の失敗でも、現在のsession、preview、GUI値、mapping選択の
  commit済み状態を変更しない。診断は既存様式
  `load failed at <stage>: <message>` に従う。
- mapping未選択（as-is）のLoad/Rebuildは、Phase 2/3の経路と完全に同一の挙動を
  維持する（回帰境界）。

`StageCore.prepare_input_session()` は `resolve_candidate()` 済みの
`InputCandidate` を直接受け取れる形へ分離する
（`prepare_candidate_session(candidate, ...)` を抽出し、既存signatureは
wrapperとして維持）。派生bundleは `--input-root` 外にあるため、
root＋user_pathの形では渡せない。

`InputSession` へ任意の由来情報を追加する。

```text
InputSession.derivation: SessionDerivation | None
├── source_candidate: InputCandidate       # input-root内の選択bundle
├── mapping_candidate: MappingCandidate    # mapping-root内の選択mapping
├── mapping_digest: str
└── derived_bundle: Path
```

- `derivation=None` は従来どおりの直接入力。
- Input dropdownの「現在の入力」はsource bundleのままとし、statusと入力概要に
  `mapping: <root相対path> (<digest先頭12桁>)` を併記する。

### Viewer session schema 1.1 — mapping参照の追加

`vdbmat.viewer-session` を `1.1.0` へ更新する。

- readerは `1.0.0` と `1.1.0` を受理する（1.0にmapping sectionは存在し得ない）。
  それ以外のversion、unknown keyは従来どおり拒否する。
- writerは常に `1.1.0` を出力する（stage-config 1.1と同じ方針）。
- top-levelへ任意の `mapping` sectionを追加する。

```json
"mapping": {
  "path": "marble-like.optical-mapping.json",
  "digest": "sha256:...",
  "derived_optical_sha256": "sha256:..."
}
```

- `mapping.path` は `--mapping-root` 相対のPOSIX path（既存の
  `_portable_path` 規則を適用）。
- `mapping.digest` は保存時点のmapping semantic digest
  （`OpticalMappingConfig.digest`）。
- `derived_optical_sha256` は描画に使った派生 `optical.zarr` の
  `zarr_store_sha256()`。
- `mapping` があるsessionでは、`input` は**source bundle**（`--input-root` 内、
  kind＝run-bundle、source bundleのoptical／run manifest digest）を指す。
  描画対象のpin留めは `derived_optical_sha256` が担う。
- `mapping` sectionがあるのに `input.kind` が `optical-zarr` の文書はparse段階で
  拒否する。

resolve（`resolve_viewer_session()`）の拡張:

```text
resolve : input（従来どおり）＋ mapping.pathをmapping-root内で解決
verify  : input digests（従来どおり）＋ mapping fileの現在digestが
          mapping.digestと一致すること
（呼出側）: regenerate_optical()でcache再利用または再生成し、得られた
          派生optical.zarrのzarr_store_sha256()が
          derived_optical_sha256と一致することを確認してからscene構築
```

- mapping fileが保存後に編集されていればverifyで
  `mapping digest mismatch`（期待値・実値付き）として拒否する。黙って
  新係数で描画しない。
- 決定的pipelineにより、digest一致のsource＋mappingからの再生成は同じ
  `derived_optical_sha256` になる。不一致は環境・実装の変化を意味するため
  明示エラーとし、別データを黙って描画しない。
- `resolve_viewer_session()` の引数へ `mapping_root: Path | None` を追加する。
  mapping付きsessionでmapping_root未指定はresolve段階のエラー。

Save session（Outputタブ）は、現在sessionが `derivation` を持つ場合に
source入力の再解決・digest計算に加えて、mapping fileの現在digestが
`derivation.mapping_digest` と一致することを確認してから `mapping` sectionを
書く。不一致（保存前にmappingが編集された）は「Load/Rebuildで反映してから
保存する」旨の診断付きで保存を拒否する。

### Viewer起動とheadless replay

- viewer CLIへ `--mapping-root DIR` と `--mapping-work-root DIR` を追加する。
- `--session` 起動でmapping付きsessionを受けた場合、resolve→verify→再生成→
  derived digest照合をStageCore構築前に行い、派生bundleを初期入力として起動する。
  mapping無しsessionは従来どおり。
- `mitsuba_stage_demo.py --session` も同じresolver＋`mitsuba_stage_regen`を使い、
  mapping付きsessionをheadless再生する。`--mapping-root`／`--mapping-work-root`
  を追加する（mapping無しsessionでは不要）。
- session再生形で従来のoverride併用不可の規則は維持する。

### 検証用サンプルmapping

「同一material inputへ2種類以上のmapping」を成立させるため、既存
`phase0-provisional-materials-v1` と同じ材料ID／名前集合で係数だけ変えた
サンプルmapping（例: `phase0-provisional-materials-v1-tinted.optical-mapping.json`、
transparent-resinの吸収を変えるなど視覚差が明確なもの）を
`examples/pipeline_run/mappings/` へ追加する。テストと手動確認の両方で使う。
係数はdemo用のuncalibrated値であり、`calibration_status` は
`provisional-uncalibrated` のまま、schema拡張は行わない。

### 変更しないもの

- `vdbmat.optical-mapping` schemaとloader、`map_material_volume_to_optical()`、
  `PipelineConfig`／`run_pipeline()` の公開契約（`src/vdbmat` は無変更）。
- canonical volume schema、run bundle形式、`vdbmat.stage-config`。
- Phase 2/3のInputカタログ判定、preset適用、session transactionの基本動作。
- mapping未選択時のLoad/Rebuild、既存sessionの再生（1.0 readerとして互換維持）。
- Blender／OpenVDB経路。

## 対象ファイル

### 主変更

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_mappings.py`（新規）
  - mapping catalog、containment、概要
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_regen.py`（新規）
  - bundle source特定、in-memory PipelineConfig組み立て、cache／reuse、
    `run_pipeline()` 呼出し
- `vdbmat/examples/pipeline_run/demo/mitsuba_viewer_session.py`
  - format 1.1、`mapping` section、resolverのmapping-root／digest検証
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
  - `--mapping-root`／`--mapping-work-root` CLI
  - Inputタブのmapping dropdown／Refresh／概要
  - Load/Rebuild transactionの `map` 段階、`prepare_candidate_session()` 抽出
  - `InputSession.derivation`、Save/Load sessionのmapping対応、startup対応
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`
  - session再生のmapping対応（`--mapping-root`／`--mapping-work-root`）
- `vdbmat/examples/pipeline_run/mappings/`
  - 検証用サンプルmapping 1件追加
- `README_QUICK.md`
  - mapping選択→再生成→比較→session保存→headless再現の標準手順

### テスト

- `vdbmat/tests/test_mitsuba_stage_mappings.py`（新規、Mitsuba不要）
- `vdbmat/tests/test_mitsuba_stage_regen.py`（新規、Mitsuba不要）
- `vdbmat/tests/test_mitsuba_viewer_session.py`
  - 1.1 schema、mapping section、resolver拡張
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`
  - CLI追加分、derivation状態、Save session時のmapping鮮度検査
- `vdbmat/tests/test_mitsuba_stage_demo.py`
  - mapping付きsession CLIの必須／排他
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
  - mapping適用transaction、cache再利用、失敗時不変、session round-trip、
    headless一致

## 実装ステップ

### Step 1 — Mapping catalog（pure）

1. `mitsuba_stage_mappings.py` にroot解決、再帰列挙、containment、candidate解決、
   概要を実装する。parseは `load_optical_mapping()` へ委譲し、検証を二重実装しない。
2. unit test: suffix一致のみ列挙・相対path昇順、root外symlink除外、直接指定の
   containment、壊れJSON／unknown field／`external_id` 混入がdescribeで
   `OpticalMappingError` 由来の診断になること、file編集後のdescribeが新しい
   digestを返すこと。
3. このstepではviewerへ配線しない。

### Step 2 — 派生bundle生成とcache（pure）

1. `mitsuba_stage_regen.py` に `locate_bundle_source()`、cache key、
   `regenerate_optical()` を実装する。
2. unit test（実 `run_pipeline` を小さなfixture manifestで実行、Mitsuba不要）:
   - 生成bundleの `run.json` にmapping digestが記録され、`optical.zarr` の
     provenanceに `mapping-digest:` sourceが残る。
   - 同一source＋mappingの2回目呼出しが `reused=True` でbyte生成をskipする。
   - mapping file編集後は同keyでも新keyでも正しく再生成される（digestが変わる
     ためcache pathが変わることを固定）。
   - source manifest欠落／payload digest不一致、材料不足、名前不一致、
     mapping parse失敗が段階名付き `RegenError` になる。
   - 入力bundle・mapping fileが変更されていないこと（mtime／内容）を確認する。
   - 2種類のmappingが異なる `optical.zarr` digestを生む。

### Step 3 — Session schema 1.1とresolver拡張（pure）

1. `mitsuba_viewer_session.py` を1.1へ更新する。1.0文書の受理、1.1のstrict
   round-trip、`mapping` sectionの必須field／portable path／digest形式、
   `optical-zarr` inputとの組合せ拒否をunit testで固定する。
2. `resolve_viewer_session()` へmapping_rootとmapping digest検証を追加する。
   mapping編集後のdigest不一致、mapping-root外、mapping欠落、mapping_root未指定を
   段階名付きで拒否することを実fileで検証する。
3. 派生digest照合はresolver呼出し側の契約として関数化し
   （例: `verify_derived_optical(resolved, derived_bundle)`)、viewerとheadlessが
   同一実装を使う形に固定する。

### Step 4 — GUI配線: mapping選択、map段階、session Save/Load

1. `--mapping-root`／`--mapping-work-root` CLIと起動時のroot衝突検査を追加する。
2. `prepare_candidate_session()` を抽出し、既存 `prepare_input_session()` を
   wrapperにする（既存テスト無変更で通ることを確認）。
3. Inputタブへmapping dropdown／Refresh／概要を追加する。選択・Refreshが
   previewもsceneも変えないことを維持する。
4. Load/Rebuildへ `validate` 事前検査と `map` 段階を追加し、
   `InputSession.derivation` をcommitする。mapping未選択経路の完全互換を回帰確認する。
5. Save sessionへmapping鮮度検査と `mapping` section出力を、Load sessionへ
   resolve→verify→regenerate→derived digest照合→prepare→load→smoke→commitを配線する。
6. `--session` startupのmapping対応を追加する。

### Step 5 — Headless replay、統合検証、文書

1. `mitsuba_stage_demo.py` のsession modeへmapping対応を追加する。
2. サンプルmapping（tinted）を追加し、nested_material_cube bundleへ
   as-is／provisional／tintedを適用してGUI再起動なしで往復切替できることを確認する。
3. mapping付きsessionのviewer finalとheadless PNGの画素完全一致
   （同一variant・seed）をintegration testと手動で確認する。
4. README_QUICKへ「mapping JSON編集→Refresh→Load/Rebuild→比較→session保存→
   headless再現」の標準手順を追記する。
5. 成果物・検証入出力は `.local/mitsubagui_improve/p4/` へ隔離する。

## テスト計画

### Mitsuba不要のunit test

Step 1／2／3に記載のとおり。加えて `test_mitsuba_stage_viewer_worker.py` へ:

- CLI: `--mapping-root` 既定値、`--mapping-work-root` 既定値（work-dir配下）、
  work rootとinput bundleの衝突拒否。
- mapping dropdown選択のみでは再構築要求が発生しない（fake GUI）。
- Save session: derivation付きsessionでmapping fileを編集した後の保存が
  鮮度検査で拒否される。derivation無しsessionは1.1として従来内容で保存される。

### Mitsuba integration test

- run bundle＋mapping選択のLoad/Rebuild成功で、preview／finalが派生
  `optical.zarr` を使い、`derivation` が記録される。
- 同じ組み合わせの再Load/Rebuildがcacheを再利用する（statusに `reused` が出る）。
- mapping JSONを編集→Refresh→Load/Rebuildで新しい係数のbundleが生成され、
  描画が変わる（PIXELSTATSではなくbundle digestとprovenanceで確認）。
- 単体 `optical.zarr` 入力＋mapping選択が `validate` で拒否され、scene不変。
- 材料不足mapping／名前不一致mapping／壊れJSONのLoad/Rebuildが段階名付きで
  失敗し、現在のsession、preview、GUI値が不変。
- mapping付きsessionのsave→（別入力・別mapping表示中に）load→元の
  source＋mapping＋stage＋render＋seedへ復元。
- session load時のmapping digest不一致・derived digest不一致で何も変わらない。
- mapping無しの既存操作（Phase 2/3の全回帰tests）が通る。

### Viewer／headless再現テスト

mapping付きsessionについて、同一variant・seed・derived optical digestで
viewer finalと `mitsuba_stage_demo.py --session` のPNGを画素完全一致で比較する。
cache有り（再利用）とcache無し（再生成）の両起動条件で一致することを確認する。

### End-to-end／手動確認

- nested_material_cube bundleへprovisionalとtinted mappingを交互に適用し、
  再起動なしの描画比較を確認する。
- tinted mappingをエディタで変更→Refresh→Load/Rebuild→反映を確認する。
- marble-like bundle＋ローカルmapping（`--mapping-root .local/marble` 等）でも
  一巡させる。
- mapping付きsessionを保存し、GUI再起動（`--session`）とheadless再生の双方で
  復元を確認する。
- 生成された派生bundleの `run.json`／provenanceにmapping digestが残ることを確認する。
- 成果物は `.local/mitsubagui_improve/p4/` のみに置く。

### 静的検査

- 変更Pythonへの `ruff check`
- Mitsuba不要unit tests（`uv run pytest`）
- `uv run --group mitsuba-viewer` のintegration tests
- Phase 1〜3の関連回帰tests
- `git diff --check`
- git管理対象に `.local`、ローカル絶対path、派生bundle、巨大成果物が
  混入していないことの確認

## 実施順序

```text
mapping catalog（pure）
    ↓
派生bundle生成／cache（pure、run_pipeline再利用）
    ↓
session schema 1.1／resolver拡張（pure）
    ↓
GUI配線（mapping選択、map段階、derivation、Save/Load）
    ↓
headless replay
    ↓
統合検証・サンプルmapping・README
```

Phase 3と同様、viser／Mitsuba非依存の契約（catalog、再生成、schema）を先に固定し、
GUIはそれを呼ぶだけにする。特にStep 2の決定的digest（同一入力→同一派生bundle）を
先にテストで固定しないと、session再生のderived digest照合が設計どおり機能するか
確認できない。

## 非ゴール

- GUI上の材料係数テーブル編集・フォーム編集・別名保存（Phase 6候補）。
- `vdbmat.optical-mapping` schemaの拡張、新しいmixing rule、calibration status追加。
- pipelineと異なる簡易混合則・GUI独自のmapping適用ロジック。
- source material volume、既存canonical bundle、mapping fileの破壊的上書き。
- `material.zarr` 直接入力の新しいpipeline経路（bundle sourceの再実行で代替）。
- 単体 `optical.zarr` 入力へのmapping適用。
- 派生bundleの自動cleanup・容量管理（Phase 5で規則を定める）。
- mapping catalogのgallery UI、複数mappingの同時比較ビュー。
- `run_pipeline` の非同期化・cancel（generation guardとtransactional swapで足りる。
  cancelはPhase 5で実測判断）。
- OpenVDB直接入力、Blender経路の変更。
- `src/vdbmat` core・CLI・exporterの変更。

## 完了条件

- `--mapping-root` 以下のmapping JSONがGUIに列挙され、Refreshと概要確認
  （configuration id／version／digest／calibration status／材料IDと名前）ができる。
- mapping選択・Refreshだけではsceneが変わらず、Load/Rebuild成功時のみ派生bundleが
  生成されscene swapされる。
- 派生bundleは `--mapping-work-root` 以下にのみ書かれ、入力bundleとmapping fileは
  変更されない。
- 同一source＋mapping digestの再Load/Rebuildがcacheを再利用し、無駄な再生成をしない。
- 同一material inputへ2種類以上のmappingを適用し、GUIを再起動せず描画比較できる。
- mapping JSONの外部編集がRefresh→Load/Rebuildで反映される。
- mappingの未知フィールド、材料不足、名前不一致、digest不整合、単体zarr入力への
  適用が段階名付きの明瞭なエラーになり、現在のscene・preview・GUI値が維持される。
- 生成された `optical.zarr` のprovenanceと `run.json` にmapping digestが残る。
- viewer session 1.1がmapping参照（path・digest・derived optical digest）を保存し、
  GUI再起動（`--session`）とheadless再生の双方で同じ
  material input＋mapping＋stage＋render条件を再構成できる。
- mapping file編集後のsession load／saveがdigest不整合として明示拒否される。
- 同一variant・seedのmapping付きsessionでviewer finalとheadless PNGが画素完全一致する。
- 既存の1.0 session、mapping未選択のLoad/Rebuild、preset適用、従来起動形が
  回帰testを通る。
- renderer依存と動作確認成果物がoptional／`.local` 境界内に留まる。

## リスクと打ち切り条件

### `run_pipeline` の実行がGUIを長時間塞ぐ

再生成はrender worker上の明示job内で行い、`map` 段階をstatusへ表示する。既存の
demo bundleは小規模で、pipeline実行は既存テストで秒オーダーであることを確認済み。
代表入力（marble-like）でmap段階がsmoke renderを大きく支配する場合も、本フェーズ
ではcancelを追加せず、cache再利用と段階表示で運用し、実測をPhase 5へ引き継ぐ。

### 派生bundleのdigestが環境間で再現しない

session再生のderived digest照合は、pipelineのbyte決定性（ADR-007 D3/D8）に依存
する。Step 2で「同一入力→`zarr_store_sha256` 一致」をテストで固定する。もし
Zarr encodingやNumPy versionの差でbyte再現が破れる事例が出た場合は、derived
digestの照合をエラーからwarning＋再保存案内へ弱めるのではなく、まず原因を特定し、
本フェーズ内で解決できなければ `derived_optical_sha256` をsession必須fieldから
任意fieldへ落とす判断を報告書に明記して行う（黙って別データを描画しない原則は
維持し、その場合もmapping digestとsource digestの照合は必須のまま残す）。

### bundle sourceが無い・信用できない入力

canonical bundleは常に `source/` を持つが、手作業でコピー・改変されたbundleは
payload digest不一致になり得る。この場合は `validate` 段階で「bundleのsourceが
run.jsonと一致しない」ことを明示して拒否する。source無しでの `material.zarr`
直接経路を場当たりに追加しない（必要性が実証されたら別フェーズで契約を定める）。

### cache pathの衝突・残骸

cache keyは科学入力の純関数であり、同keyへの並行書込みはrender worker直列化で
起きない。`run_pipeline` の一時directory（`.<name>.tmp-*`）が異常終了で残った
場合も次回実行が除去する。work root全体のcleanup規則はPhase 5の範囲とし、
本フェーズでは「残骸が次回実行を妨げない」ことだけをテストで保証する。

### mapping選択とinput選択の組合せ爆発でGUI状態が複雑化する

commit済み状態は `InputSession.derivation` の1箇所へ集約し、dropdownの未commit
選択はPhase 2の入力選択と同じ「選択と適用の分離」規則に従わせる。Save sessionは
GUI選択ではなくcommit済みderivationだけを参照する。これで「選択したが適用して
いないmapping」がsessionへ混入しない。実装中にderivationと入力dropdownの整合が
取れない状態が見つかった場合は、mapping dropdownをLoad/Rebuild成功時に
commit値へ巻き戻す仕様へ単純化する。

### viewer-session 1.1で旧toolが読めない

readerは1.0/1.1受理、writerは1.1固定とする。Phase 3以前のreaderは存在しない
（同repo内のviewerとdemoのみが消費者）ため、外部互換の考慮は不要。repo内の
全消費者を本フェーズで同時に更新する。
