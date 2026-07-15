# mitsubagui_improve ロードマップ — 入力・材料設定を選択できる Mitsuba GUI

## 背景

既存の `mitsuba_gui` vision により、`mitsuba_stage_viewer.py` では stage、照明、
カメラ、解像度、spp をブラウザから調整し、プリセット保存と確定レンダーを行える。
プレビューも固定ビューポートへ移され、設定はタブで整理されている。

一方、現在のビューアは起動時に CLI で渡した単一の `optical.zarr` を読み込み、
exterior/interior PLY と preview/final scene を一度構築する設計である。次の項目は
GUIから変更できない。

- 入力となるモデル／canonical run bundle／`optical.zarr`
- 材料から光学特性への mapping ファイル
- 吸収・散乱・IOR などの材料パラメータ
- Mitsuba integrator の `max_depth`（現在は既定値 8）
- 保存済み stage preset のGUIからの再読み込み

材料係数をGUIウィジェットとして網羅すると、mapping schema の変更とGUI変更が常に
連動し、材料実験よりGUI実装が開発を律速する。そこで初期段階は、材料値そのものを
GUI編集するのではなく、既存の入力ファイルと材料 mapping ファイルを選択して
明示的に再構築するワークフローを成立させる。細かな値はJSONを編集して反映できる
状態を先に作り、材料エディターは必要性が確認されてから検討する。

本ロードマップは改善全体のフェーズ境界を定める。各フェーズの具体的な変更箇所、
API、テストケース、移行手順は、そのフェーズ着手時に個別の実装 plan として作成する。
既存 `.devdocs/vision/mitsuba_gui/roadmap.md` の非ゴールを途中で変更するものではなく、
同vision完了後に入力境界を広げる後続visionとして扱う。

## 用語と入力境界

### 正規入力は OpenVDB ではなく canonical volume とする

会話上の「VBD/VDB入力」は、少なくとも初期フェーズでは次の2種類に分けて扱う。

1. **描画済み光学入力**: canonical run bundle 内の `optical.zarr`、または
   単体の `optical.zarr`
2. **材料から再生成する入力**: `vdbmat.pipeline-config` が参照する direct voxel
   manifest等、または canonical bundle 内の `material.zarr` と
   `*.optical-mapping.json`

OpenVDBは現状、Blender/Cycles等へ渡すconsumer-specificな派生出力であり、
Mitsubaに必要なRGB吸収・散乱、g、IOR、provenanceを正規契約として再構成する入力には
しない。OpenVDB直接入力が本当に必要になった場合は、保持できるgridと失われる意味を
定義する別フェーズ／別visionで扱う。

### 既存契約を再利用する

- 材料パラメータ: `vdbmat.optical-mapping` JSON
- 材料→光学変換: `map_material_volume_to_optical()` と既存pipeline
- 永続化された正規成果物: `material.zarr` / `optical.zarr`
- stage設定: `vdbmat.stage-config` JSON
- pipeline実行設定: `vdbmat.pipeline-config` JSON

GUI専用の材料ファイル形式や、同じ係数を別スキーマで重複定義しない。

## 全体ゴール

ローカル開発者がブラウザGUI上で次を行えるようにする。

1. 許可されたルート以下から入力bundleまたは `optical.zarr` を選ぶ。
2. 必要に応じて既存の optical mapping JSON を選ぶ。
3. `Load/Rebuild` を明示的に実行し、検証済みの新シーンへ安全に切り替える。
4. `max_depth` をGUIで比較調整する。
5. stage、render、入力、mappingの組み合わせを保存し、headlessでも再現する。
6. mappingの細かな変更は当面JSON編集で行い、GUI再起動なしで再読み込みする。

## 設計原則

### 1. 選択と適用を分離する

ファイルのドロップダウン変更だけでは再構築しない。Inputタブで候補を選んだ後、
`Load/Rebuild` を押した時だけ検証とシーン再構築を開始する。入力途中の状態や連続する
ファイルイベントによる重い再実行を避ける。

### 2. scene切替はtransactionalにする

新入力は別の一時work directoryで読み込み、変換、PLY生成、preview scene load、
最小スモークレンダーまで成功してから現在の `StageCore` と交換する。失敗時は現在の
画像と設定を維持し、どの段階で失敗したかをGUIへ表示する。中途半端なsceneをpublish
しない。

### 3. パスはserver-localな許可ルートから選ぶ

巨大なZarr/VDBをブラウザへuploadさせない。起動引数で指定した `--input-root`、
`--mapping-root`、`--preset-root` 以下を走査し、GUIでは相対パスのドロップダウンと
Refreshボタンを提供する。symlinkを解決した実体が許可ルート外へ出る候補は拒否する。
任意パス入力を設ける場合も、同じcontainment検証を必須とする。

### 4. 科学入力と表示設定を混同しない

- optical mappingは科学入力であり、digestとcalibration statusを保持する。
- stage presetは背景、照明、カメラ等の表示設定である。
- `max_depth`、解像度、spp等はrender transport設定である。

最終的なsession manifestではこれらを関連付けるが、既存の各設定ファイルを
埋め込んで複製しない。

### 5. 重い操作は明示的、軽い操作はinteractive

- 入力/mapping変更: 明示的 `Load/Rebuild`
- `max_depth`: GUI数値入力。ただし適用時はintegratorを含むscene rebuildを許容する
- stageの連続値: 現行どおりtraverse更新とcoarse/settled preview

## フェーズ構成

### Phase 1 — Render契約の拡張と `max_depth` GUI対応

#### 目的

入力切替より先に、render transport設定をGUI・preset・headlessで一貫して扱える
契約を作り、今回のガラス描画を比較するための `max_depth` を調整可能にする。

#### スコープ

- 現在の `RenderSettings` に `max_depth` を追加する。
- stage JSONのformat versionと後方互換規則を定める。旧presetに
  `max_depth` が無い場合は既定値8で補完する。
- viewerのRenderタブに整数入力を追加する。範囲は実装planで決めるが、0や負数は
  拒否する。
- preview/final双方の `MitsubaExportConfig.max_depth` へ反映する。
- max depth変更時の更新分類を明示する。traverse不能ならpreview scene rebuildを
  正規経路とし、silent fallbackにしない。
- `mitsuba_stage_demo.py --stage-config` でも同値を使用し、GUI finalとheadlessの
  再現性を保つ。
- scene summaryまたはviewer statusへ実効 `max_depth` を表示する。

#### 非ゴール

- BSDF roughness、IOR、吸収、散乱のGUI編集。
- 入力ファイル切替。
- exporter既定値そのものの変更。未指定時は従来の8を維持する。

#### 完了条件

- GUIで `max_depth` を変更するとpreview/finalへ反映される。
- 保存presetをheadlessで再生すると同じ `max_depth` になる。
- 旧stage presetが既定値8として読み込める。
- 同一入力・stage・seed・max depthでGUI finalとheadless結果が一致する。

### Phase 2 — 入力カタログと既存 `optical.zarr` の安全な切替

#### 目的

既に生成済みのcanonical bundle／`optical.zarr` を、GUIを終了せず選択・検証・
再構築できるようにする。材料再mappingはまだ行わない。

#### スコープ

- `--input-root` と必要な既定値／未指定時の互換動作を定義する。
- root以下から次を検出する入力カタログを実装する。
  - canonical run bundle（`optical.zarr` を含むもの）
  - 単体の `optical.zarr`
- Inputタブを追加する。
  - 入力ドロップダウン
  - Refresh
  - 選択内容のschema、shape、voxel size、provenance概要
  - `Load/Rebuild`
- `StageCore` を起動時固定オブジェクトから交換可能なsession coreへ整理する。
- 現在のrender workerを入力切替と直列化し、古いgenerationのpreviewが新sceneへ
  publishされないようにする。
- 新入力のscene構築をtransactionalに行い、失敗時は旧sceneを保持する。
- 入力切替後も現在のstage設定とrender設定を維持する。ただし不正な組み合わせは
  診断付きで拒否する。
- work directoryを入力ごとに分離し、PLYやsummaryの衝突を防ぐ。

#### 非ゴール

- optical mappingの選択・再実行。
- OpenVDB直接読み込み。
- 複数入力の同時比較表示。
- ブラウザからのファイルupload。

#### 完了条件

- 少なくとも `nested_material_cube` と `marble-like` の既存bundleをGUIから往復
  切替できる。
- 読み込み失敗、壊れたZarr、非optical volumeを選んでも旧previewが残る。
- root外パスとroot外を指すsymlinkが候補／直接入力の双方で拒否される。
- 入力切替中の連続GUI操作でstale画像や異なるsceneの成果物が混在しない。

### Phase 3 — Stage presetの読込とviewer session manifest

#### 目的

入力、stage、render設定の組み合わせを再現可能な単位として保存・再読込できるように
する。材料mapping導入前に、ファイル選択と再現性の基盤を完成させる。

#### スコープ

- `--preset-root` 以下の `*.stage.json` カタログとGUI読込を追加する。
- preset選択と `Apply stage preset` を分離し、読込失敗時は現在値を維持する。
- viewer session manifestの小さなversioned schemaを定義する。最低限、次への参照と
  digest／実効値を記録する。
  - canonical input bundleまたは `optical.zarr`
  - stage presetまたはinlineの実効StageConfig
  - render設定（`max_depth`を含む）
  - Mitsuba variantとseed
- `Save session` / `Load session` をOutput/Inputタブへ追加する。
- portableな相対パスの基準を明示し、ローカル絶対パスをgit管理用サンプルへ
  書き出さない。
- headless CLIがsession manifestを受け取れる経路、または同等の引数展開手段を
  用意する。

#### 非ゴール

- material mapping適用。
- session内へのZarrやmapping本文の埋め込み。
- 複数sessionのギャラリーUI。

#### 完了条件

- session保存→GUI再起動→session読込で、入力、stage、max depth、variant、seedが
  復元される。
- sessionからのGUI finalとheadless renderが同一条件で再現できる。
- 参照先のdigest不一致や欠落を明示的に検出し、黙って別データを描画しない。

### Phase 4 — Optical mappingファイル選択とcanonical再生成

#### 目的

材料係数をGUIで個別編集せず、既存の `*.optical-mapping.json` を編集・選択・再読込
することで材料実験を行えるようにする。

#### スコープ

- `--mapping-root` 以下の `vdbmat.optical-mapping` JSONをカタログ化する。
- Inputタブにmappingドロップダウン、Refresh、概要表示を追加する。
  - configuration id / version
  - digest
  - calibration status
  - 対象material IDと名前
- 材料再生成の入力契約を次のいずれかに限定し、実装planで選定する。
  - 既存 `vdbmat.pipeline-config` を選び `run_pipeline()` を実行する経路
  - canonical bundleの `material.zarr` に選択mappingを適用して、新しい派生bundleを
    transactionally発行する専用経路
- 既存pipelineのmapping loader、validation、digest、provenanceを再利用する。
- 選択mappingが入力material IDsを網羅するか、scene構築前に検証する。
- mapping適用結果を `.local` の明示されたcache/work rootへ書き、入力bundleを
  上書きしない。
- mapping digestとmaterial input digestに基づく再利用方針を定め、同じ組み合わせの
  無駄な再生成を避ける。
- mapping JSONを外部エディタで変更後、Refresh→Load/Rebuildで反映できるようにする。
- 成功後はPhase 2と同じtransactional scene swapを使用する。
- session manifestへmapping参照とdigestを追加する。

#### 非ゴール

- GUI上の材料係数テーブル編集。
- mapping schemaの拡張。
- pipelineと異なる簡易混合則の導入。
- source material volumeや既存canonical bundleの破壊的上書き。

#### 完了条件

- 同一material inputへ2種類以上のmappingを適用し、GUIを再起動せず描画比較できる。
- mappingの未知フィールド、material不足、digest不整合が明瞭なエラーになる。
- 生成された `optical.zarr` のprovenanceにmapping digestが残る。
- 保存sessionから同じmaterial input＋mapping＋stage＋render条件を再構成できる。

### Phase 5 — 運用性・診断・回帰検証の完成

#### 目的

入力とmappingを日常的に切り替えるツールとして、長時間利用時の安全性、観測性、
再現性を固める。

#### スコープ

- Input/Rebuildの進行段階をstatusへ表示する。
  `validate → map → persist → prepare preview → smoke render → swap`
- cancelの必要性を実測で判断する。採用する場合も現在sceneを壊さず、処理結果の
  publish抑止を第一とする。
- 入力、mapping、stage、renderの実効設定とdigestをGUIから確認できるようにする。
- staleなcache、途中で失敗した一時directory、古いPLY成果物のcleanup規則を定める。
- `nested_material_cube`、`window_coupon`、`marble-like` 等でsession replay回帰を作る。
- CPU/GPU variant間で「同じ科学入力・設定」を確認できる診断を残す。画素完全一致を
  variant間には要求しない。
- README_QUICKと開発文書へ、ファイル編集→Refresh→Rebuild→session保存→headless
  再現の標準手順を記載する。

#### 非ゴール

- リモート公開、認証、複数ユーザーの編集競合。
- GUI内コードエディタ。
- Blender/Cycles入力との同時比較。

#### 完了条件

- 代表入力とmappingの組み合わせが自動回帰で再生される。
- rebuild失敗、連続切替、ブラウザ再接続でも現在sceneとsession状態が破損しない。
- ユーザーが最終PNGから入力・mapping・stage・render条件を追跡できる。
- 標準ワークフローが文書化され、ローカル成果物は `.local` に隔離される。

### Phase 6（オプション） — GUI材料エディターと外表面モデル

Phase 1〜5の運用で必要性が確認されたものだけを個別に計画する。

候補:

- mapping材料一覧と係数のread-only表
- mapping JSONの限定的なフォーム編集と別名保存
- absorption/scatteringの診断用倍率（科学入力を書き換えない一時override）
- exterior限定の `roughdielectric` / roughness選択
- IOR変更時の境界mesh再生成
- 入力間のA/B比較ビュー
- OpenVDB直接入力adapter（意味論と欠落fieldを別途定義できる場合のみ）

このフェーズは一括実装しない。たとえばroughnessはstageでもbulk mappingでもなく
surface modelの契約であり、科学的意味と保存先を決める独立planが必要である。

## フェーズ間の依存関係

```text
Phase 1: max_depthとrender契約
    ↓
Phase 2: 既存optical入力の切替
    ↓
Phase 3: preset/session再現
    ↓
Phase 4: mapping選択とcanonical再生成
    ↓
Phase 5: 運用・診断・回帰の完成
    ↓
Phase 6: 必要な編集機能だけを選択実装
```

Phase 1〜3で、材料再計算を伴わない複数入力比較と再現可能なsessionを先に完成させる。
Phase 4は既存pipelineとの統合を伴うため、入力切替のtransaction境界とsession契約が
安定してから着手する。Phase 6は必須フェーズではない。

## 全フェーズ共通の非ゴール

- canonical volume schemaやoptical mapping schemaをGUI都合で変更すること。
- `src/vdbmat` coreへviserやMitsuba GUI依存を追加すること。
- OpenVDBをcanonical scientific inputとして扱うこと。
- source、canonical bundle、mappingファイルの破壊的な上書き。
- GUI操作だけに存在し、preset/session/headlessで再現できない永続設定。
- `.local` の入力・出力やローカル絶対パスをgit管理成果物へ混入させること。

## 検証方針

各フェーズの個別planで詳細化するが、共通して次を守る。

- 純粋なcatalog、path containment、config round-trip、worker generation管理は
  Mitsubaなしのunit testを優先する。
- scene生成やtraverse/rebuild一致は小解像度・低sppのMitsuba integration testで
  確認する。
- GUI finalとheadlessは同一variant・seed・設定で比較する。
- 入力／mapping切替は成功ケースだけでなく、壊れたファイル、schema違い、root外、
  material不足、処理中の再要求を検証する。
- `PIXELSTATS`だけで科学入力の一致を判断せず、digest、実効config、provenance、
  必要な場合はHDR配列を確認する。
- 動作確認の入出力は `.local/mitsubagui_improve/pN/` に置き、git管理しない。

## 主要リスクと方針

### 再構築時間が長くGUIが固まって見える

重い処理はrender workerと直列化したbackground jobで行い、段階表示を出す。
値変更ごとの自動再構築は行わない。cancelより先にgeneration guardとtransactional
swapで安全性を確保する。

### 入力切替中に旧previewが新sceneを上書きする

scene/input generationをpreview generationより上位の識別子として導入し、入力が
変わった時点で旧世代のpublishを無効化する。単にqueueを空にするだけで済ませない。

### mapping実行がpipelineロジックを二重化する

GUI独自のmapping処理を作らず、既存loader、validation、mapping、provenance、atomic
publishを再利用する。既存APIがGUI利用に不足する場合は、まずviser非依存のapplication
serviceとして抽出し、GUIはそれを呼ぶだけにする。

### sessionがローカルパス依存で再現できない

参照は明示されたbase directoryからの相対パスを基本とし、digestを併記する。
絶対パスを許すローカルsessionと、portableなサンプルsessionを区別する。

### `max_depth`変更で応答性が落ちる

integratorが安全にtraverse更新できない場合はscene rebuildを正規動作とする。
`max_depth`は連続sliderではなく整数入力にし、必要ならApplyまたはdebounceを設ける。

### 材料GUI編集の要求が早期に膨らむ

Phase 4まではファイル選択とread-only概要に限定する。JSON編集で実験可能な間は、
GUI field editorを完了条件に入れない。

## ロードマップ全体の完了条件

- GUIから既存canonical入力を安全に切り替えられる。
- GUIからmapping JSONを選択し、元材料入力から新しいcanonical optical volumeを
  非破壊かつtransactionalに生成して描画できる。
- `max_depth`をGUIで変更し、preset/session/headlessで再現できる。
- 入力、mapping、stage、renderの組み合わせがversioned sessionとして保存され、
  digestとprovenanceで追跡できる。
- mapping係数をGUI実装なしにJSON編集→Refresh→Rebuildで反映でき、GUI開発が材料
  実験を律速しない。
- 失敗したload/rebuildが現在sceneを破壊せず、古いレンダー結果が新sceneへ混入しない。
- renderer依存とローカル成果物が既存のoptional／`.local`境界内に保たれる。
