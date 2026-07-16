# mitsubagui_improve Phase 2 実装計画 — 入力カタログと既存 `optical.zarr` の安全な切替

親ロードマップ:
`.devdocs/vision/mitsubagui_improve/roadmap.md`（Phase 2）。
前提となる完了済み実装: Phase 1（`.devdocs/vision/mitsubagui_improve/p1/`、
stage-config 1.1、`max_depth` 伝播、preview rebuild境界）。

## この計画の位置づけ

本計画は Phase 2 の実装だけを対象とする。optical mappingの選択・再実行（Phase 4）、
stage presetのGUI読込とsession manifest（Phase 3）、OpenVDB直接入力、複数入力の
同時比較、ブラウザからのuploadは扱わない。

現在のviewerは起動時にCLIで渡した単一の `optical.zarr` を読み、preview/final scene
を一度構築したら入力を変えられない。本フェーズで次を成立させる。

```text
--input-root 以下の走査
        ↓
入力カタログ（canonical bundle / 単体 optical.zarr）
        ↓
Inputタブで選択 → 概要表示 → Load/Rebuild
        ↓
transactionalなscene構築（validate → prepare → load → smoke render）
        ↓
成功時のみ現在sessionと交換（失敗時は旧scene維持）
```

材料から光学特性への再mappingは行わない。読むのは既に生成済みの
optical volumeだけである。

## 前提調査（確認済み事実）

### 入力側の既存契約

- `vdbmat.io.zarr.read_volume()` はZarr storeを完全validateして
  `CanonicalVolume` を返す。asset typeが optical-property なら
  `OpticalPropertyVolume`（provenance、optical basis、sigma_a/sigma_s/g/ior入り）。
- 同moduleの `inspect_volume()` は配列データを読み込まずにasset type、schema
  name/version、`GridGeometry`（shape_zyx / voxel_size_xyz_m）、配列のdtype/shape
  を返す。provenanceは含まないが、storeの `zarr.json` attrs（manifest）には
  provenanceが記録されている。
- canonical run bundleはdirectory直下に `run.json` を持ち、`material.zarr` /
  `optical.zarr` / `config.json` / `diagnostics/` / `source/` を含む
  （`.local/blender_improve1/nested_material_cube` 等で実確認）。
- `vdbmat.cli.main._inspect()` は「`path/run.json` がfileならbundle、それ以外は
  単体volume」という判別規則を既に使っている。カタログでも同じ規則を採用する。
- 壊れたstore・非opticalなstoreは `read_volume` / `inspect_volume` が
  `VolumeIOError` 系で明示的に失敗する。GUI側で独自validationを再実装する必要は
  ない。

### Viewer側の現状構造（`mitsuba_stage_viewer.py`、Phase 1完了時点）

- `_parse_args()` は位置引数 `optical_zarr` を必須とし、rootという概念がない。
- `StageCore.__init__()` が `read_volume()`、`prepare_mitsuba_scene()`（preview用）、
  `TraversedPreviewScene` 構築、`_ensure_final()` までを一括で行う。つまり
  「入力の読込〜scene準備」と「render/preset保存API」が同一オブジェクトの
  生成時に癒着しており、入力交換の単位が存在しない。
- work directoryは単一で、`preview_scene/` と `final_scene/` を固定名で書く。
  入力を切り替えるとPLY・`scene-summary.json` が別入力の成果物を上書きする。
- `RenderWorker` は単一threadで、preview（latest-wins、generation guard付き）と
  submitされたjob（final render）を直列に処理する。renderの並行実行は起きない
  ため、入力切替も同threadのjobとして実行すれば直列化はworker既存機構で足りる。
- ただし `_publish()` のguardはpreview generationのみで、scene（入力）世代という
  上位の識別子がない。また `ViewerApp._publish_preview()` は無条件に
  `self.status` とpreview画像を更新する。
- `StageBinder` はGUI⇔StageConfigのbindingで、入力には依存しない。入力切替後も
  binderの現在値をそのまま新sceneへ適用できる。
- `TraversedPreviewScene` は `base.scene_dict` と `geometry` を受け取り、
  stage適用・traverse更新・planned rebuildを担う。新入力では新しいbase/geometryで
  作り直す設計になっており、入替単位として再利用できる。

### 数値・性能上の前提

- `prepare_mitsuba_scene()` はboundary mesh抽出とPLY書き出しを含む重い処理で、
  入力サイズに依存して数秒〜分単位になり得る。GUI callback threadで実行しては
  ならず、render workerと同じthreadで実行する（Mitsuba variantのthread局所性の
  面でも既存renderと同一threadに揃えるのが安全）。
- 巨大Zarrの候補列挙自体は軽い（directory構造とmanifest JSONだけ見る）。
  ただし `.zarr` store内部やbundle内部へ再帰降下しない列挙にする必要がある。

## 規模判定

単一フェーズの実装計画として扱える。主変更はviewer 1ファイルと、viser/Mitsuba
非依存の新module 1つ、テスト、文書である。canonical volume schema、
`prepare_mitsuba_scene()` / `MitsubaExportConfig`、stage-config契約、
headless demo（`mitsuba_stage_demo.py`）は変更しない。

ただし「dropdownを足すだけ」では成立しない。StageCoreの分割（session化）、
worker publishの世代管理、per-input work directoryを同時に入れないと、
ロードマップの完了条件（stale混入なし・失敗時の旧scene維持）を満たせないため、
これらを一体で実装する。

## ゴール

1. `--input-root` 以下からcanonical run bundleと単体 `optical.zarr` を列挙する
   入力カタログを、viser/Mitsuba非依存の純粋なlogicとして実装する。
2. Inputタブ（dropdown / Refresh / 選択概要 / Load/Rebuild）を追加する。
3. `Load/Rebuild` 実行時のみ、transactionalに新sceneを構築して交換する。
   失敗時は現在のscene・画像・設定を維持し、失敗段階をGUIへ表示する。
4. 入力切替をrender workerへ直列化し、旧入力のpreview結果が新sceneへ
   publishされないことを世代guardで保証する。
5. 入力ごとにwork directoryを分離し、PLY・scene summaryの衝突をなくす。
6. root外パス・root外を指すsymlinkを候補列挙と直接指定の双方で拒否する。
7. 入力切替後も現在のstage/render設定（`max_depth` 含む）を維持する。

## 決定事項

### 入力の種類と判別

カタログが扱う入力は roadmap の定義どおり次の2種類のみとする。

- **canonical run bundle**: 直下に `run.json` があり、かつ `optical.zarr` を
  含むdirectory。実際に読むのは `bundle/optical.zarr`。
- **単体 optical volume**: 名前が `*.zarr` で、manifestのasset typeが
  optical-property のdirectory。

判別規則はCLI `_inspect()` と同じ「`run.json` の有無」を第一キーとする。
bundle内の `material.zarr` は列挙しない（材料再mappingはPhase 4）。asset typeが
material-label / material-mixture の単体storeも候補に含めない。カタログ列挙時は
directory名とmanifest冒頭の判定だけで済ませ、`read_volume()` による完全検証は
`Load/Rebuild` まで遅延する。

### 新module `mitsuba_stage_inputs.py`

viewerの1ファイル肥大を避け、Mitsubaなしのunit testを可能にするため、
`vdbmat/examples/pipeline_run/demo/mitsuba_stage_inputs.py` を新設し、
次を置く。viser・Mitsubaをimportしない。

```text
InputKind = "run-bundle" | "optical-zarr"

InputCandidate
├── kind: InputKind
├── root_relative: str        # GUI表示・選択キー（POSIX相対パス）
├── path: Path                # 実体（bundle rootまたは.zarr）
└── optical_zarr: Path        # 実際に読むstore

resolve_input_root(cli_root, initial_input) -> Path
scan_input_catalog(root) -> list[InputCandidate]     # 決定的順序（相対パス昇順）
resolve_candidate(root, user_path) -> InputCandidate # 直接指定にも同じ検証
describe_candidate(candidate) -> InputSummary        # inspect_volume + manifest概要
```

- `scan_input_catalog()` は `os.walk` 相当で走査し、bundleまたは `.zarr` を
  検出したdirectoryへは降下しない（Zarr chunkやbundle内部を舐めない）。
- containment検証は `Path.resolve()` 後の実体パスがresolve済みrootの内側に
  あることを要求する。symlink自体は許可するが、解決先がroot外に出る候補は
  列挙から除外し、直接指定では明示エラーにする。判定は
  `resolved.is_relative_to(resolved_root)` で行い、文字列前方一致は使わない。
- `describe_candidate()` は `inspect_volume()`（配列データ非読込）と、bundleなら
  `run.json` のrun id / schema / stages概要を合成した表示用summaryを返す。
  provenanceはstore manifest attrsから読み取り、要約（source id等）だけ表示する。
  失敗はexceptionとして呼び出し側へ返し、GUIはエラー文言表示に留める。

### CLI互換と `--input-root` の既定値

- 位置引数は必須のまま維持し、意味を「初期入力」へ拡張する。単体
  `optical.zarr` に加えてbundle directoryも受理し、`run.json` 判別で
  `bundle/optical.zarr` へ解決する（既存呼び出しの互換は完全維持）。
- `--input-root DIR` を追加する。未指定時は「初期入力（bundleならbundle root）の
  親directory」を既定rootとする。これにより既存コマンドラインのまま
  Inputタブが兄弟入力の切替に使える。
- 初期入力自身は、rootの内外に関わらず常に「現在の入力」としてGUIへ表示する。
  root外の初期入力はカタログ候補には並ばない（containment規則を初期入力の
  ために緩めない）。

### StageCoreのsession化

`StageCore` を「入力に束縛される部分」と「共有部分」に分離する。

- 共有部分（プロセスで1つ）: Mitsuba module／variant、seed、preview
  size/spp、render worker、GUI。
- 入力session（交換単位、新class `InputSession` とする）:
  `read_volume()` 済みvolume、session専用work directory、
  `prepare_mitsuba_scene()` のbase preview、`TraversedPreviewScene`、
  final base sceneとそのcache key（`_ensure_final` 相当）、入力の識別情報
  （root相対パス、kind）。

`StageCore` は現在sessionへの参照と `swap_session()` を持つ形へ再編し、
`render_preview()` / `render_final()` / `save_preset()` の外部APIと
既存テストの利用面を維持する。scriptから使えるviser非依存coreという
Phase 1の性質は保つ。

### Transactionalな構築と交換

`Load/Rebuild` は次の段階を、render workerへsubmitした単一jobとして実行する。
段階名は固定文字列でstatusへ流す（Phase 5の進行表示の下地になるが、本フェーズは
開始・成功・失敗段階の表示までとする）。

```text
validate   : resolve_candidate + read_volume + optical-property型検証
prepare    : prepare_mitsuba_scene()（新sessionのwork directoryへ）
load       : TraversedPreviewScene構築（現在のstage/render設定で）
smoke      : interactive sppでの1回の小レンダー
swap       : StageCore.swap_session() + session世代インクリメント
```

- swap以前のあらゆる失敗では、新sessionのオブジェクトを破棄して現在の
  scene・preview画像・GUI設定を一切変更しない。GUIへは
  `input load failed at <stage>: <error要約>` を表示する。
- smokeまでは現在のbinder設定（stage節・render節）をそのまま使う。これにより
  「切替後も現在のstage/render設定を維持」と「不正な組み合わせの事前検出」を
  同じ段階で満たす。stage適用が新入力で失敗する場合はload/smoke段階の
  診断付き拒否になる。
- 失敗した一時work directoryは削除を試み、削除失敗は警告ログに留める
  （cleanup規則の一般化はPhase 5）。
- swap成功後にpreview世代を進めて通常のpreview要求を1回発行し、新sceneの
  settled previewまで既存経路で到達させる。

### 世代guard（scene generationをpreview generationの上位に置く）

roadmapの指示どおり、queueを空にするだけの実装は採らない。

- `StageCore`（またはViewerApp）に単調増加の `session_generation` を持たせ、
  swap成功時にインクリメントする。
- workerのpreview結果publishは `(session_generation, preview_generation)` の
  両方が現在値と一致する場合のみ行う。preview render開始時点のsession世代を
  結果へ添付する。
- final render jobも開始時にsession世代を捕捉し、完了時に世代が変わっていたら
  PNGは書くが「stale (input changed during render)」をstatusへ明示する、
  のではなく——finalはユーザーが明示要求した成果物なので、**job実行時点の
  現在sessionで実行**し、jobとswapはworker上で直列なので途中交換は起きない。
  よってfinalに必要なのは「queueされた時点ではなく実行時点のsessionを使う」
  ことの明示だけである。final job内でsessionを取得する実装にする。
- 単一worker threadという直列性が主防壁、世代guardが再入・再接続・将来の
  並列化に対する保証、という二層構造をdocstringへ明記する。

### Per-input work directory

- `work_dir/inputs/<seq>-<slug>/` をsession work directoryとする。`<seq>` は
  プロセス内単調増加の連番、`<slug>` はroot相対パスから生成した安全な短い
  識別子。同じ入力を再loadしても常に新しいdirectoryを使い、上書きと
  stale成果物の混同を避ける。
- 各sessionのpreview/final sceneはその配下の `preview_scene/` /
  `final_scene/` へ書く。起動時の初期入力も同じ規則で `inputs/000-...` を
  使い、旧来の `work_dir/preview_scene` 固定パスは廃止する（work_dirの
  内容はもともと一時成果物であり、外部契約ではない）。

### Inputタブ

`StageBinder` のtab groupへ「Input」tabを追加する（Renderタブより前、先頭）。

- **input dropdown**: カタログのroot相対パス一覧。現在の入力を初期値にする
  （root外初期入力の場合は `"(initial) <path>"` の1項目を先頭に足す）。
- **Refresh**: rootを再走査してdropdown候補を入れ替える。選択中の値が
  消えた場合は現在入力の表示へ戻す。
- **概要markdown**: dropdown変更時に `describe_candidate()` の結果
  （kind、schema name/version、shape_zyx、voxel_size_xyz_m、bundleなら
  run id等のprovenance概要）を表示する。読めない候補はエラー要約を表示し、
  Load/Rebuildは実行時に改めて拒否する。
- **Load/Rebuild button**: 上記transactional jobをworkerへsubmitする。
  実行中はbuttonをdisableし、二重submitを防ぐ（cancelは実装しない。
  roadmap Phase 5の判断事項）。
- dropdown選択・Refresh・概要表示はいかなるrender・rebuildも起こさない
  （選択と適用の分離、設計原則1）。

dropdown/Refresh/概要のGUI callbackは軽量I/Oのみとし、Mitsubaを触らない。
`describe_candidate()` の失敗はGUI callback内でcatchして表示に変える。

### 変更しないもの

- `mitsuba_stage.py`（stage-config契約）: 変更なし。stage presetへ入力パスを
  記録しない。入力＋stage＋renderの束ねはPhase 3のsession manifestで扱う。
- `mitsuba_stage_demo.py`: 変更なし（headlessは従来どおり単一入力引数）。
- `vdbmat/src/vdbmat`（canonical exporter、io、pipeline）: 変更なし。
  カタログ・GUIはpure consumerに留める。

## 対象ファイル

### 主変更

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_inputs.py`（新規）
  - InputCandidate / InputSummary
  - root解決、カタログ走査、containment検証、候補解決、概要生成
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
  - `--input-root` とCLI互換（bundle受理）
  - `InputSession` 抽出と `StageCore` のsession化
  - transactional load/rebuild job、段階status、失敗時保持
  - session世代guard（publish条件、final jobの実行時session取得）
  - per-input work directory
  - Inputタブ（dropdown / Refresh / 概要 / Load/Rebuild）
  - module docstringのアーキテクチャ説明更新

### テスト・文書

- `vdbmat/tests/test_mitsuba_stage_inputs.py`（新規、Mitsuba不要）
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`（世代guard追加分）
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`（切替統合テスト追加）
- `README_QUICK.md`（viewer節へ `--input-root` とInputタブの説明）

## 実装ステップ

### Step 1 — 入力カタログmodule（Mitsuba/viser非依存）

1. `mitsuba_stage_inputs.py` にInputCandidate/InputSummaryと
   root解決・走査・containment・候補解決・概要生成を実装する。
2. 走査はbundle/`.zarr` 検出directoryへ降下しない。結果は相対パス昇順で
   決定的にする。
3. containmentはresolve済み実体パスの `is_relative_to` で判定し、root外
   symlinkの除外／拒否を実装する。
4. unit testを先に通す（fixture treeをtmp_pathに構築。`write_volume()` で
   本物の小さなoptical/material storeを作り、判別と概要を実データで検証する）。

この時点ではviewerに触れない。カタログ契約を先に固定する。

### Step 2 — StageCoreのsession化（挙動不変のrefactor）

1. `InputSession` を抽出し、`StageCore` を現在session保持＋API委譲へ再編する。
2. per-input work directory規則（`inputs/<seq>-<slug>/`）を導入し、初期入力も
   同規則で構築する。
3. `session_generation` とpublish時の二重guardを `RenderWorker`／ViewerApp
   境界へ実装する。final jobは実行時点のsessionを取得する形へ変える。
4. 既存のpreview/final/preset挙動（Phase 1の全テスト）を維持したまま通す。
   このstepでは入力切替UIをまだ作らない。

### Step 3 — Transactional load/rebuildとswap

1. validate→prepare→load→smoke→swapのjobを実装する（workerへsubmit）。
2. 各段階の開始・失敗をstatusへ表示し、失敗時は新session資材を破棄して
   現在sessionを維持する。
3. swap成功時にsession世代を進め、現在のbinder設定で新previewを要求する。
4. smoke renderは現在のstage/render設定＋interactive spp・preview解像度で行う。

### Step 4 — Inputタブと配線

1. Inputタブ（dropdown / Refresh / 概要 / Load/Rebuild）を追加する。
2. `--input-root` と初期入力のbundle受理を `_parse_args()`／起動経路へ追加する。
3. Load/Rebuild実行中のbutton disableと、完了・失敗時の復帰を実装する。
4. 選択・Refresh・概要がrenderを一切誘発しないことを確認する。

### Step 5 — 統合検証・文書

1. 統合テスト（下記）を追加して通す。
2. README_QUICKのviewer節へ `--input-root`、Inputタブ、Load/Rebuildの
   transactional挙動（失敗時は旧scene維持）を追記する。
3. 実入力（`.local` のnested_material_cube bundleとmarble bundle）で往復切替、
   壊れた入力、root外symlinkを手動確認し、成果物を
   `.local/mitsubagui_improve/p2/` へ隔離する。

## テスト計画

### Mitsuba不要のunit test

`test_mitsuba_stage_inputs.py`:

- bundle（`run.json`＋`optical.zarr`）と単体optical storeが検出される。
- material-labelの単体store、`run.json` はあるが `optical.zarr` を欠くdirectory、
  無関係のdirectory/fileが候補に含まれない。
- bundle・store内部へ降下しない（store内へダミーの `.zarr` 名directoryを
  置いても検出されない）。
- 列挙順序が決定的（相対パス昇順）。
- root外を指すsymlink候補が列挙から除外される。
- `resolve_candidate()` がroot外の直接指定・root外へ解決されるsymlink・
  存在しないパスを明示エラーで拒否する。
- `resolve_input_root()`: CLI指定あり／なし（初期入力の親）、bundle初期入力。
- `describe_candidate()` がkind・schema・shape・voxel size・（bundle時）run id
  を返し、壊れたmanifestで例外を上げる。

`test_mitsuba_stage_viewer_worker.py` 追加分:

- session世代が異なるpreview結果はpublishされない。
- preview世代guardの既存挙動（latest-wins、final直列化、例外回復）が
  session世代導入後も維持される。
- work directory連番が同一入力の再loadでも重複しない。

### Mitsuba integration test

`tests/integration/test_mitsuba_stage_viewer.py` 追加分。入力は既存fixtureで
2種類の小さなoptical volume（nested_material_cubeと、材質・形状の異なる
もう1つ）をtmp内のroot以下にbundle/単体それぞれの形で用意する。

- viewer core経由で入力A→B→Aの往復switchを行い、各swap後のpreviewが
  レンダー可能で、`render_final()` のscene summaryが各入力のwork directory
  に分離して書かれる。
- 切替後にstage/render設定（非既定 `max_depth` を含む）が維持される。
- 壊れたZarr（manifest破壊）、非optical volume（material.zarr）をloadすると
  validate/load段階で失敗し、直前のpreview画像・sessionが不変のまま残る。
- swap成功直後の後続stage変更が従来どおり `traverse` routeで処理される
  （新sessionのTraversedPreviewSceneが正常に機能する）。
- 旧世代のpublish抑止: 切替前にrequestしたpreview結果が切替後のGUIへ
  届かないことを、worker/core APIレベルで検証する。

### End-to-end／手動確認

- `.local` の実bundle（nested_material_cube、marble）を `--input-root` 配下で
  GUI起動し、往復切替・Refresh・壊れ入力・root外symlinkを確認する。
- 切替後にSave presetしたstage JSONが従来どおりheadless
  （`mitsuba_stage_demo.py --stage-config` に新入力を渡す）で再現することを
  1組み合わせ確認する（契約が変わっていないことの回帰）。
- 成果物は `.local/mitsubagui_improve/p2/` に置き、git管理しない。

### 静的検査

- 変更Pythonへの `ruff check`
- 関連unit tests、Mitsuba integration tests
- `git diff --check`

## 実施順序

```text
カタログmodule（unit test込み）
    ↓
StageCore session化（挙動不変refactor＋世代guard）
    ↓
transactional load/swap
    ↓
Inputタブ・CLI配線
    ↓
統合検証・文書
```

viser/Mitsuba非依存の契約（カタログ・containment・世代guard）を先に固定し、
GUIは最後に配線する。GUIを先に作って「切替はできるが失敗時に壊れる」状態を
中間成果としない。

## 非ゴール

- optical mappingの選択・再実行、`material.zarr` からの再生成（Phase 4）。
- stage presetのGUI読込、session manifest（Phase 3）。
- OpenVDB直接入力。
- 複数入力の同時比較・A/B表示。
- ブラウザからのファイルupload、リモート公開。
- Load/Rebuildのcancel機構、進行率バー（Phase 5で実測判断）。
- headless demoへの `--input-root` 導入（headlessは引数で入力を直接受ける）。
- stage-config schemaへの入力パス追加。
- `prepare_mitsuba_scene()` の成果物cache・再利用最適化（Phase 1のリスク項で
  引き継いだPLY再生成コストの一般解はsession設計の実測後に判断する）。

## 完了条件

- `--input-root`（既定: 初期入力の親）以下のcanonical bundleと単体
  `optical.zarr` がInputタブに列挙され、Refreshで再走査できる。
- nested_material_cubeとmarble相当の2入力をGUIを終了せず往復切替でき、
  それぞれのpreview/finalが正しくレンダーされる。
- 切替後もstage設定・render設定（`max_depth` 含む）が維持される。
- 壊れたZarr・非optical volume・root外パス・root外symlinkのloadが段階名付きの
  診断で拒否され、旧previewとsessionが維持される。
- 入力切替中・切替後に旧入力のpreview結果がpublishされない（世代guardが
  worker testで検証されている）。
- 入力ごとのwork directoryが分離され、PLY／scene summaryが衝突しない。
- 位置引数だけの従来起動が完全に従来どおり動く（bundle pathも受理）。
- stage-config契約・headless demo・canonical exporter・`src/vdbmat` に変更がない。
- unit/integration/static checksが通り、検証成果物が `.local` に隔離される。

## リスクと打ち切り条件

### `prepare_mitsuba_scene()` が長くGUIが固まって見える

構築はworker jobなのでGUI threadは固まらないが、その間previewも進まない。
Phase 2では段階statusの表示と、Load/Rebuild中のbutton disableで「動いている」
ことを可視化するに留める。実測で分単位の待ちが常態化する場合も、cancelや
並列prepareを本フェーズへ追加せず、測定結果をPhase 5へ引き継ぐ。

### session化refactorで既存挙動が変わる

Step 2を「UIなしの挙動不変refactor」として独立させ、Phase 1のunit/integration
テスト一式をそのまま合否基準にする。refactor段階で既存テストの修正が必要に
なった場合は、テストが実装詳細に依存していたのか挙動が変わったのかを区別し、
後者ならswap実装より先に解消する。

### カタログ走査が巨大treeで遅い

bundle/`.zarr` への非降下pruningで通常は軽い。それでも遅いrootを指定された
場合に備え、走査はGUI callback内の同期処理としては行うが、候補数・経過の
statusを出す。深さ制限や非同期走査は実測されるまで追加しない。

### 同一storeへの同時アクセス

旧sessionのvolumeはメモリ上のnumpy配列で、swap後のZarr storeアクセスは
発生しない。よって同じ入力の再loadや切替でstore lock問題は起きない。
新sessionのread中に旧sessionでrenderすることもない（worker直列のため）。

### 概要表示のためのmanifest読込が候補ごとに走る

概要はdropdown変更時に選択中の1候補だけ読む。全候補の一括metadata読込や
cacheは行わない。Refreshは候補列挙（軽量判定）のみで概要を読まない。

### root既定値（初期入力の親）が広すぎる／狭すぎる

既定はあくまで互換動作であり、意図的なカタログ運用では `--input-root` を明示
してもらう。READMEへその旨を書く。既定rootの走査が現実的でない配置が
見つかった場合は、既定を「初期入力のみ表示（走査なし）」へ弱める判断を
実装中に許容するが、その場合も `--input-root` 明示時の挙動は変えない。
