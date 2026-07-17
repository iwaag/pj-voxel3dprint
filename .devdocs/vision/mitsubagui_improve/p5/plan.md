# mitsubagui_improve Phase 5 実装計画 — 運用性・診断・回帰検証の完成

作成日: 2026-07-17

## この計画の位置づけ

本計画は `.devdocs/vision/mitsubagui_improve/roadmap.md` の Phase 5 を、
Phase 4完了時点の実装へ接続するための実装計画である。

Phase 1〜4で、`max_depth` を含むrender契約、入力カタログとtransactionalな入力切替、
stage preset適用、`vdbmat.viewer-session/1.1.0` によるGUI／headless再現、
mapping選択と派生canonical bundleの非破壊生成・cache再利用が完成した。
機能面では roadmap の全体ゴールをほぼ満たしているが、日常的に入力とmappingを
切り替える運用ツールとしては次が残っている。

1. 実効設定とdigestをGUIから確認する手段がない（Save sessionを実行して
   JSONを読むしかない）。
2. 最終PNGが、それを生成した入力・mapping・stage・render条件と機械的に
   結び付いていない。
3. 成功swapで置き換えられた旧session work directoryが蓄積する。cache・残骸の
   cleanup規則が未定義。
4. 代表入力×mappingの組み合わせを一括で再生する自動回帰がない（Phase 4の
   integration testは個別機能の検証が中心）。
5. CPU/GPU variant間で「同じ科学入力・設定か」を確認する診断がない。
6. cancelの要否が実測で判断されていない。
7. 標準運用手順（編集→Refresh→Rebuild→session保存→headless再現→追跡）の
   文書が分散している。

Phase 5はこれらを埋める hardening フェーズであり、新しい科学ロジック・schema・
許可rootは追加しない。

参照した前提資料:

- `README_QUICK.md`
- `.local/local_env_memo.md`
- `.devdocs/vision/mitsubagui_improve/roadmap.md`
- Phase 1〜4の実装planとPhase 4の `report1.md`〜`report5.md`
- Phase 4完了時点の `mitsuba_stage_viewer.py`、`mitsuba_stage_demo.py`、
  `mitsuba_viewer_session.py`、`mitsuba_stage_inputs.py`、
  `mitsuba_stage_mappings.py`、`mitsuba_stage_regen.py` と関連テスト

## 前提調査（確認済み事実）

### 段階表示は既に存在する

- Load/Rebuildは `input load: <stage>…` としてstatusへ
  `validate → map → prepare → load → smoke → swap` を表示し、cache再利用時は
  `map: reused cache` を出す。session loadは `parse → … → verify → … → commit`
  を表示する。roadmapの段階列 `validate → map → persist → prepare preview →
  smoke render → swap` のうち `persist` は `map` 段階（`run_pipeline()` 内の
  atomic publish）に含まれる。
- `run_pipeline()` は進捗callbackを公開しない。`src/vdbmat` の変更は全フェーズ
  共通非ゴールなので、`map` 内部の細分表示は行えない（行わない）。
- 各段階の所要時間は計測・表示されていない。cancel要否の実測にはこれが要る。

### 失敗時保全とgeneration guardは実装・テスト済み

- swap前のどの段階の失敗でも現在のsession・preview・GUI値・commit済み
  derivationが維持されることは、Phase 2〜4のunit／integration testで固定済み。
- render workerは直列で、session generationにより旧世代のpublishは無効化される。

### work directoryとcache

- `--work-dir` 未指定時は `mkdtemp` の新規directory。入力swapごとに
  `work_dir/inputs/NNN-slug/` を作成し、失敗時は `_discard_session_dir()` で
  破棄するが、**成功swapで置き換えられた旧session directoryは残置され蓄積する**。
  docstringで `work_dir` の内部layoutはscratch側効果と宣言済み。
- 派生bundle cacheは `--mapping-work-root`（既定 `work_dir/derived`）以下の
  content-addressed path。再利用判定は `run.json` の宣言digest照合。
- `run_pipeline()` の一時directory（`.<name>.tmp-*`）残骸は、同一出力pathへの
  次回実行が除去する（既存動作、Phase 4テストで保証済み）。

### 最終PNGと実効状態の可視性

- `render_final()` はPNGだけを書く。`scene-summary.json` はsession work directory
  内の `final_scene/` に落ち、PNGの隣にはない。入力・mapping digestとPNGを
  結び付けるsidecarは存在しない。
- 実効状態のGUI表示は、入力概要（schema／shape／voxel size／run_id／provenance）
  とstatus行のmapping併記まで。stage・render・variant・seed・digestを一望する
  パネルはない。
- `Save session` は毎回 `zarr_store_sha256()` で全storeをhashする。digestの
  session内cacheはない。

### viser reconnect

- `on_client_connect` で新client接続時に現在のpreviewを再送する実装が既にあり、
  client別のviewport追随・disconnect時の後始末もある。ただし「Load/Rebuild
  進行中のreconnect」を対象にした検証はない。

### 代表入力とmapping

- checked-in fixtureは3つ: `nested_material_cube`（air／transparent-resin／
  black-opaque-resin、interior境界あり）、`stepped_wedge`（air／
  transparent-resin）、`window_coupon`（air／transparent-resin／white-resin／
  black-opaque-resin）。いずれも `examples/pipeline_run/inputs/` にmanifest＋
  payload、`configs/` にrun configがある。
- checked-in mappingは `phase0-provisional-materials-v1` と同 `-tinted` の2つで、
  materials一覧は全fixtureのpaletteの上位集合。palette coverage検証を通るため、
  **3 fixture × 2 mappingの全組み合わせが再生成可能**。
- `marble-like` はvdbmat-utils側の生成物であり、vdbmatのtest suiteからは生成
  できない。`.local` に既存bundleがあり、README_QUICKに生成手順がある。

### variant

- sessionは `llvm_ad_rgb`／`cuda_ad_rgb` のvariantとseedをpinし、explicit引数の
  不一致は拒否する。variant切替はプロセス再起動が必要（in-process切替なし）。
- ローカル環境にはCUDA GPUがあり `cuda_ad_rgb` を起動できる（README_QUICK記載）。

### テストの現状

- Phase 4完了時点で unit 557件、`tests/integration/test_mitsuba_stage_viewer.py`
  30件が通過。viewer final／headlessの画素完全一致、cache再利用、失敗時不変は
  個別機能として検証済み。代表入力を横断するparameterized回帰は未整備。

## 規模判定

**中規模**と判定する。

新しいschema・許可root・科学ロジックを追加せず、`src/vdbmat` は無変更。
変更はdemo-track（viewer／demo／新diagnostic module）、テスト、文書に閉じる。
ただし計測・cleanup・可視化・回帰suite・診断と領域が複数に跨るため、
Phase 3/4と同様にstep分割して進める。

## ゴール

- Load/Rebuild・session load・final renderの各段階の所要時間が観測でき、
  その実測に基づいてcancelの採否が判断・記録される。
- commit済みの入力・mapping・stage・render・variant・seed・digestをGUIの
  read-onlyパネルで確認でき、参照ファイルとのドリフトを明示診断できる。
- `Render final` のPNGから、それを生成した条件（session文書）へ機械的に
  たどれ、そのままheadless再現できる。
- 旧session directory・起動時残骸のcleanup規則が定義・実装され、derived cache
  は「全削除しても再生成で復旧する」ことが保証・文書化される。
- 代表入力（checked-in 3 fixture）×mapping（as-is／provisional／tinted）の
  session replayが自動回帰として一括実行される。
- rebuild失敗・連続切替・browser reconnectでも現在sceneとsession状態が
  破損しないことが、自動テスト（＋reconnectは手動確認併用）で固定される。
- 2つのsessionが「variant以外の科学入力・設定で一致するか」を判定する診断が
  あり、CPU/GPU比較の標準手順が文書化される。
- 標準運用手順がREADME_QUICKへ一本化され、ローカル成果物は
  `.local/mitsubagui_improve/p5/` に隔離される。

## 決定事項

### 段階表示は現行語彙を正とし、経過秒を追加する

roadmapの段階列に対し、現行の `validate → map → prepare → load → smoke → swap`
を正とする。`persist` は `map`（`run_pipeline()` のatomic publish）に、
`prepare preview`／`smoke render` は `prepare`／`smoke` に対応する。
`run_pipeline()` へ進捗callbackを追加する変更は非ゴール（core無変更）のため
`map` の細分はしない。

Phase 5で追加するのは各段階の経過秒である。

- statusには完了した直前段階の所要（例 `input load: prepare… (map 3.2s)`）、
  完了時に総所要を表示する。
- stdoutへ `STAGE <transaction> <stage> <elapsed_s>` 形式の1行logを出す。
  これがcancel判断とPhase 5報告書の実測データ源になる。
- 段階名・遷移順は既存テストが参照するため変更しない（表示の追記のみ）。

### cancelは「実測→判断」とし、既定は非採用

計測手順: checked-in 3 fixtureのbundleと `.local` の `marble-like` bundleに
ついて、cache無しLoad/Rebuild（mapping適用あり）の総所要と段階別内訳、
session load、final renderの所要を上記STAGE logで採取し、Phase 5報告書へ記録
する。

採用基準: **明示的Load/Rebuild（final renderを除く）の代表worst-caseが約30秒を
超える場合のみ**、cancelを追加する。追加する場合も roadmap の方針どおり
「実行中の処理は中断せず、結果のpublish／commitだけを放棄する」abandon型とする。
generation guardが既にあるため、実装はUIボタン＋現行transactionの世代無効化に
閉じ、`run_pipeline()` の中断・非同期化は行わない。基準未満なら非採用とし、
経過表示とcache再利用で足りることを実測値とともに報告書へ明記する。

### 実効状態の可視化 — commit済み状態のread-onlyパネルと明示的digest検証

Inputタブへ「Effective state」セクション（read-only markdown）を追加し、
**commit済みsession**の実効状態を表示する。

- input: kind／root相対path／run_id
- derivation: mapping root相対path／mapping digest／derived bundle path／
  cache再利用の有無（derivation無しなら `as-is`）
- stage: 適用preset provenance（path＋digest、あれば）または `inline`
- render: width／height／spp／max_depth
- mitsuba: variant／seed
- digests: input optical digest、（derivation時）derived optical digest —
  計算済みの場合のみ表示、未計算は `not computed`

dropdownの未commit選択は反映しない（Phase 2以来の「選択と適用の分離」を維持）。
表示更新はswap／session load／preset適用／render設定変更のcommit時に行う。

digest計算は重いため、`InputSession` ごとに1回計算してcacheする
（`optical.zarr` digest、bundle時は `run.json` digestも）。計算タイミングは
(1) Save session、(2) final sidecar書き出し、(3) 新設の **Verify digests**
ボタン、のいずれか最初の要求時。Verify digestsはrender worker上でcacheの有無に
かかわらず現ファイルを再hashし、cache値・（derivation時）mapping fileの現在
digestと照合して、一致／ドリフトをstatusとEffective stateへ表示する。入力bundle
は運用上不変だが、外部からの改変を検出できる唯一の手段としてボタンを明示操作に
する。Save sessionはこのcacheを再利用する（毎回の全store再hashを解消）。ただし
Save session既存の入力再解決・root containment・mapping鮮度検査は従来どおり
維持する。

### 最終PNGからの追跡 — session文書のsidecar出力

`Render final` 成功時、出力PNGの隣へ `<basename>.session.json` を書く。内容は
既存 `vdbmat.viewer-session/1.1.0` 文書そのものであり、**新しいschemaは作らない**。
これにより「最終PNG→条件の追跡」と「最終PNGのheadless再現
（`mitsuba_stage_demo.py --session`）」が同じ1ファイルで成立する。

- digestはInputSessionのcacheを使う（未計算ならこの時点で計算しcacheする）。
- session文書を構成できない場合（現在入力が `--input-root` 外の初期sentinel、
  mapping鮮度不一致など、既存Save sessionが拒否する条件と同一）はsidecarを
  skipし、renderは成功のままstatusへ `final: session sidecar skipped: <理由>` を
  表示する。PNG生成をsidecar失敗で巻き込まない。
- headless `mitsuba_stage_demo.py --session` は入力session自体が追跡文書なので
  sidecarは書かず、`RENDER` logへsession pathとsession file digestを追記する
  だけとする。非session形（positional形）は対象外。

### cleanup規則

次を定義し実装する。

- **(a) swap後の旧session directory破棄**: 成功swapのcommit時、置き換えられた
  旧 `work_dir/inputs/NNN-slug/` を削除する。render workerが直列なため旧scene
  を参照するjobは残らない。preview scene loadがPLY等を即時読み込みで完了して
  いること（遅延file参照がないこと）を実装時に確認してから既定案とする
  （リスク節参照）。現在のsession directoryは保持する。
- **(b) 起動時sweep**: viewer起動時、自分の `--work-dir` 直下の `inputs/` の
  残骸（前回プロセスの遺物）を削除する。sweep対象は `work_dir/inputs/` のみ
  とし、`derived/` やその他のユーザーファイルには触れない。削除前にresolve済み
  pathが `work_dir` 内であることを検証する。`--work-dir` 未指定（毎回mkdtemp）
  では実質no-op。
- **(c) derived cacheは自動削除しない**: content-addressedで再利用されるため、
  「viewer／headless replayが動いていない時に `--mapping-work-root` 以下を
  丸ごと削除して安全（次回Load/Rebuildが再生成する）」を規則として文書化し、
  「cache全削除後のLoad/Rebuildが再生成で成功する」ことをintegration testで
  固定する。サイズ上限GC・自動失効は非ゴール。
- **(d) `.tmp-*` 残骸**: 同一出力pathへの次回 `run_pipeline` 実行が除去する
  既存動作を規則として文書化する。viewerとheadless replayがmapping work root
  を共有して並行し得るため、root全体を跨ぐ一括sweepは行わない。

### 代表入力のsession replay回帰

新しいintegration test module
`tests/integration/test_mitsuba_stage_viewer_regression.py` を追加し、
checked-in資産だけで次をparameterizeして一括実行する。

- 対象入力: `nested_material_cube`／`stepped_wedge`／`window_coupon`
  （それぞれ checked-in manifest＋configから `run_pipeline` でbundle生成）
- 対象mapping: `(bundle optical as-is)`／`provisional`／`tinted`
- 各代表対について: viewer core（GUIなしの `StageCore`＋transaction API）で
  load → mapping適用 → session保存 → headless resolve・再生成・derived digest
  照合 → render → **viewer finalとheadless PNGの画素完全一致**（同一variant・
  seed）と、派生bundleのprovenance（mapping digest）をassertする。

実行時間を抑えるため、解像度・sppは既存integration testと同水準の小値にし、
組み合わせは3×3の全積ではなく代表対（全入力×as-is、
nested_material_cube×全mapping、window_coupon×tinted 等）へ絞る。

堅牢性ケースを同moduleへ含める。

- 成功session確立後、壊れた入力・材料不足mapping・壊れmappingのLoad/Rebuildを
  挟み、commit済みsession・preview・実効状態が不変であること。
- 連続するLoad/Rebuild要求で最後の世代だけがpublishされること
  （既存generation guardの代表入力横断回帰）。
- reconnect相当: 新client接続時に現在のpreviewが配信されること
  （`_connect_preview` 経路）。viser実clientのprogrammaticな再接続が
  テスト困難な場合は、接続callback単位のunit検証＋実ブラウザでの手動確認
  （Load/Rebuild進行中にタブを閉じて開き直す）へ切り分け、手順と結果を
  報告書へ記す。

`marble-like` はvdbmat単体テストから生成できないため自動回帰へは含めず、
`.local` の既存bundle（＋ローカルmapping）に対する手動確認手順をREADMEへ記載
し、実施結果は報告書に結果のみ記す（roadmapの検証方針どおり成果物は
`.local/mitsubagui_improve/p5/` へ隔離）。

### CPU/GPU variant診断 — session互換diff

新しいpure module `mitsuba_session_compat.py`（demo directory、viser／Mitsuba
非依存）を追加する。

```text
compare_sessions(a: Path, b: Path) -> SessionCompatReport
├── scientifically_equal: bool   # variant以外が全一致
└── differences: [(field, a_value, b_value), ...]
```

- 2つの `vdbmat.viewer-session` JSONを既存readerで読み、input参照とdigest、
  run manifest digest、mapping参照とdigest、derived optical digest、実効
  stage／render設定、seedを突合する。variantのみ異なる場合は
  `scientifically_equal=True`。
- CLI（`python .../mitsuba_session_compat.py A.session.json B.session.json`）
  はexit 0＝variantのみ差、exit 非0＝差分列挙、とする。
- 標準手順として文書化: 同一入力・mapping・stage・seedで `llvm_ad_rgb` と
  `cuda_ad_rgb` それぞれのsessionを保存 → compatで科学同一性を確認 → 双方を
  headless renderしPIXELSTATSを並記する。**variant間に画素完全一致は要求しない**
  （roadmapどおり）。
- 判定ロジックはMitsuba不要のunit testで固定する。CUDA実renderを含む比較は
  CUDA可用時のみの手動確認とし、結果を報告書へ記す。

### 文書

- README_QUICKのGUI節へ「運用（operations）」小節を追加する。
  - 段階語彙（roadmap名との対応）と経過表示・STAGE logの読み方
  - cleanup規則: `work_dir/inputs/` は使い捨て、derived cacheは停止中なら
    全削除安全、`.tmp-*` は次回実行が除去
  - `Render final` のsidecar sessionと、そこからのheadless再現・条件追跡手順
  - Verify digestsによるドリフト検査
  - variant比較診断の手順
  - marble-like等 `.local` 入力での手動確認手順
- 標準ループ（mapping編集→Refresh→Load/Rebuild→session保存→headless再現）は
  Phase 4で記載済みの節を参照で一本化し、重複記述を増やさない。
- 実測値・cancel採否判断・reconnect確認結果は
  `.devdocs/vision/mitsubagui_improve/p5/report*.md` へ残す。

### 変更しないもの

- `src/vdbmat` core（pipeline、optics、exporters、CLI）。
- `vdbmat.viewer-session`（1.1のまま。sidecarは既存schemaの再利用）、
  `vdbmat.stage-config`、`vdbmat.optical-mapping`、bundle形式。
- Phase 2〜4のtransaction・catalog・containment・generation guardの公開挙動
  （cleanupとdigest cacheは内部変更、段階名・遷移順も不変）。
- Blender／OpenVDB経路。

## 対象ファイル

### 主変更

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
  - 段階経過秒のstatus／STAGE log
  - InputSessionのdigest cacheとSave sessionの再利用
  - Effective stateパネル、Verify digestsボタン
  - final sidecar session書き出しとskip診断
  - swap後の旧session directory破棄、起動時 `inputs/` sweep
  - （実測で採用した場合のみ）abandon型cancel
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`
  - session再生logへのsession path／digest追記
- `vdbmat/examples/pipeline_run/demo/mitsuba_session_compat.py`（新規）
  - session互換diff（pure）
- `README_QUICK.md`
  - 運用小節（段階・cleanup・追跡・ドリフト検査・variant比較・手動確認）

### テスト

- `vdbmat/tests/test_mitsuba_session_compat.py`（新規、Mitsuba不要）
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`
  - digest cache、cleanup規則（swap後破棄・startup sweepの対象限定）、
    sidecar skip条件、Effective state内容
- `vdbmat/tests/integration/test_mitsuba_stage_viewer_regression.py`（新規）
  - 代表入力×mappingのsession replay回帰、堅牢性ケース
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
  - final sidecarのheadless再現一致、cache全削除後の再生成成功

## 実装ステップ

### Step 1 — 段階経過の計測と採否判断の実測

1. Load/Rebuild・session load・final renderへ段階経過秒のstatus表示と
   `STAGE` stdout logを追加する（段階名・遷移順は不変）。
2. checked-in 3 fixtureのbundle（cache無し初回＋cache有り2回目）と `.local` の
   `marble-like` bundleで所要時間を採取し、cancel採否を判断する。
   結果と判断根拠を報告書へ記録する。
3. 実ブラウザでLoad/Rebuild進行中のreconnect挙動を確認し、問題の有無を
   記録する（修正が必要ならStep 4で対応）。
4. unit test: 段階logの形式、既存段階遷移テストの無回帰。

### Step 2 — cleanup規則

1. 成功swap時の旧session directory破棄を実装する。事前にpreview scene load後の
   遅延file参照がないこと（旧PLY削除後もpreview／finalが動作すること）を
   integration testで確認する。
2. 起動時 `work_dir/inputs/` sweepを実装する（対象限定・containment検証付き）。
3. cache全削除後のLoad/Rebuildが再生成で成功するintegration testを追加する。
4. unit test: sweepが `derived/` と無関係ファイルに触れないこと、失敗時破棄の
   既存挙動の無回帰。

### Step 3 — 可視化と追跡

1. InputSessionへdigest cacheを追加し、Save sessionを再利用側へ切り替える
   （既存のSave session検証・拒否条件は無変更で通ることを回帰確認）。
2. Effective stateパネルとVerify digestsボタンを追加する。commit時のみ更新、
   未commit選択の非反映をテストで固定する。
3. `Render final` のsidecar session書き出しとskip診断を実装する。
4. `mitsuba_stage_demo.py` のsession再生logへsession path／digestを追記する。
5. integration test: sidecar sessionをそのまま `--session` でheadless再生し、
   final PNGと画素完全一致すること。

### Step 4 — 代表入力のsession replay回帰と堅牢性

1. `test_mitsuba_stage_viewer_regression.py` を追加する（代表対のparameterize、
   viewer final／headless一致、provenance assertion）。
2. 堅牢性ケース（失敗介在で状態不変、連続要求で最終世代のみpublish、
   接続callback経路）を追加する。
3. Step 1で問題が見つかった場合のreconnect修正をここで行う。
4. 全体の実行時間を計測し、既存integrationと合わせてローカル数分以内に
   収まるよう組み合わせ・解像度を調整する。

### Step 5 — variant診断・文書・（採用時）cancel

1. `mitsuba_session_compat.py` とunit testを追加する。
2. Step 1で採用と判断した場合のみ、abandon型cancelを実装しテストする
   （現scene不破壊・publish抑止のみ）。非採用ならこの項はskipし報告書へ明記。
3. README_QUICKへ運用小節を追記する。
4. `.local` の `marble-like` で手動確認（切替往復・session保存・headless再現・
   variant比較）を一巡し、結果を報告書へ記す。成果物は
   `.local/mitsubagui_improve/p5/` のみに置く。

## テスト計画

### Mitsuba不要のunit test

- `mitsuba_session_compat.py`: variantのみ差→equal、input digest／mapping
  digest／derived digest／stage／render／seedの各差分検出、壊れたsession文書の
  既存reader診断の透過。
- STAGE logの形式と、既存段階遷移（fake GUI）の無回帰。
- digest cache: 同一sessionで2回目のSave sessionが再hashしないこと（hash関数
  呼び出しの計数）、cacheがsession単位で分離されること。
- cleanup: swap後破棄の対象選定、startup sweepの対象限定（`inputs/` のみ、
  `derived/` 不触）、containment検証。
- sidecar: skip条件（sentinel入力、mapping鮮度不一致）でPNGは成功しsidecarのみ
  skipされること。
- Effective state: commit時のみ更新、未commit選択の非反映。

### Mitsuba integration test

- 代表入力×mappingのsession replay回帰（viewer final／headless画素完全一致、
  provenance、cache再利用）。
- 旧session directory破棄後もpreview／final renderが動作する。
- derived cache全削除→Load/Rebuild再生成成功。
- final sidecarのheadless再生一致。
- 堅牢性: 失敗介在・連続要求・接続callback。
- Phase 2〜4の既存integration回帰が全て通る。

### 手動確認

- Load/Rebuild進行中を含むbrowser reconnect（タブ閉→再接続でstatusとpreviewが
  回復し、世代混在がないこと）。
- `.local` marble-like bundleでの切替・session・headless・追跡の一巡。
- CUDA可用環境でのllvm／cuda session保存→compat診断→PIXELSTATS並記。

### 静的検査

- 変更Pythonへの `ruff check` ／ `ruff format --check`
- Mitsuba不要unit tests（`uv run pytest`）
- `uv run --group mitsuba-viewer` のintegration tests
- `git diff --check`
- git管理対象に `.local`、ローカル絶対path、計測生データ、成果物PNGが
  混入していないことの確認

## 実施順序

```text
段階経過の計測とcancel採否・reconnect実測（Step 1）
    ↓
cleanup規則（Step 2）
    ↓
可視化と追跡: digest cache → Effective state → sidecar（Step 3）
    ↓
代表入力session replay回帰と堅牢性（Step 4）
    ↓
variant診断・文書・（採用時）cancel（Step 5）
```

Step 1の実測が cancel採否（Step 5）と回帰suiteの規模調整（Step 4）の判断材料に
なるため先行させる。Step 3のdigest cacheはsidecarとSave session高速化の共通
基盤なので、パネル・sidecarより先に固定する。

## 非ゴール

- リモート公開、認証、複数ユーザーの編集競合。
- GUI内コード／JSONエディタ。
- Blender/Cycles入力との同時比較。
- `run_pipeline()` への進捗callback追加、中断、非同期化（`src/vdbmat` 無変更）。
- derived cacheのサイズ上限GC・自動失効・世代管理。
- variant間の画素一致保証、in-processのvariant切替。
- viewer-session／stage-config／optical-mapping schemaの拡張・version bump。
- marble-like等の大きな成果物・fixtureのgit管理への追加。
- 複数sessionのギャラリーUI、A/B比較ビュー（Phase 6候補）。

## 完了条件

- 代表入力（checked-in 3 fixture）×mapping（as-is／provisional／tinted）の
  代表対でsession replay自動回帰が通り、viewer finalとheadless PNGが
  画素完全一致し、provenanceのmapping digestが検証される。
- rebuild失敗・材料不足mapping・連続切替を挟んでもcommit済みsession・preview・
  実効状態が不変であることが自動回帰で固定される。browser reconnect後に
  statusとpreviewが回復することが確認される（自動または手動＋報告書記録）。
- `Render final` がsidecar session（既存 `vdbmat.viewer-session` 文書）を書き、
  それをheadless再生すると同一variant・seedで画素完全一致する。ユーザーは
  最終PNGから入力・mapping・stage・render条件を機械的に追跡できる。
- GUIのEffective stateパネルでcommit済みの入力・mapping・stage・render・
  variant・seed・digestを確認でき、Verify digestsが参照ファイルとのドリフトを
  明示診断する。
- cleanup規則（swap後破棄・起動時sweep・cache削除安全性・`.tmp-*`）が実装・
  文書化され、derived cache全削除後もLoad/Rebuildが再生成で復旧する。
- Load/Rebuild・session load・final renderの段階所要が観測でき、実測値と
  cancel採否の判断が報告書に記録される（採用時はabandon型が実装され、
  現sceneを破壊しない）。
- `mitsuba_session_compat` が2 sessionの科学同一性（variant以外）を判定し、
  CPU/GPU比較の標準手順が文書化される。
- README_QUICKに運用小節（段階語彙・cleanup・追跡・ドリフト検査・variant比較・
  `.local` 入力の手動確認）が追記される。
- Phase 1〜4の既存unit／integration回帰が全て通り、動作確認成果物は
  `.local/mitsubagui_improve/p5/` のみに置かれる。

## リスクと打ち切り条件

### digest計算が大入力で重く、sidecar／パネルが体感を損なう

digestはInputSessionごとに1回のcacheとし、明示操作（Save session／final render／
Verify digests）でのみ計算する。marble-like実測でfinal renderのsidecar書き出しが
render本体に対して支配的（目安: 数十秒級）になる場合は、sidecarのdigest欄を
「cache済みの場合のみ埋める」仕様へ弱め、完全なdigest付き文書はSave session／
Verify digests経由とする判断を報告書に明記する（黙って遅くしない・黙って
省略しない）。

### 旧session directory破棄がsceneの遅延file参照と衝突する

preview／final sceneがPLY等をload時に読み切っていることをStep 2の先頭で
integration testにより確認する。遅延参照が見つかった場合は、破棄を1世代遅らせる
（swap時にN-2世代を破棄する）代替へ切り替え、規則の変更を文書と報告書へ反映する。

### 回帰suiteの実行時間が膨らむ

fixture×mappingの全積ではなく代表対に絞り、解像度・sppは既存integrationと同水準
の小値にする。既存30件＋新suiteでローカル数分以内を目安とし、超える場合は
組み合わせをさらに削って報告書に選定理由を残す。

### reconnectにviser API起因の制約が見つかる

preview配信はclient別viewport管理と `on_client_connect` 再送が既にあるため、
修正が必要でもviewer内に閉じる見込み。viser側の制約で解決できない場合は、既知の
制約として文書化し、完了条件のreconnect項を「再接続後にstatusとpreviewが回復する
こと」までへ限定する判断を報告書に明記する（黙って完了条件を満たしたことに
しない）。

### cancel採否の判断が割れる／後から要件化する

採用基準（明示的Load/Rebuildのworst-case約30秒）と実測値を報告書に明記し、
どちらの判断でも計測データを残す。採用時もabandon型（publish抑止のみ）に限定し、
`run_pipeline()` の中断は行わない。将来必要になった場合もSTAGE logとgeneration
guardがそのまま土台になる。

### 計測・確認の成果物がgit管理へ混入する

計測生データ、PNG、`.blend`、session JSON等の動作確認成果物は
`.local/mitsubagui_improve/p5/` のみに置き、報告書には結果と数値だけを記す
（`.local/local_env_memo.md` の規則に従う）。
