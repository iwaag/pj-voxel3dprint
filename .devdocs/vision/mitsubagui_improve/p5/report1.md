# mitsubagui_improve Phase 5 実施報告 — Step 1

`plan.md` の Step 1（段階経過の計測と採否判断の実測）まで完了した。この時点で、
Load/Rebuild・session load・final renderの各段階所要が経過秒付きでstatusへ表示され、
`STAGE <transaction> <stage> <elapsed_s>` としてstdoutへ記録される。実測に基づき、
**cancel機能は非採用**と判断した（根拠は後述）。Step 2以降のcleanup規則、
Effective stateパネル、sidecar session、代表入力回帰、variant診断、READMEは未着手である。

## 変更内容

### `_StageTimer`（`mitsuba_stage_viewer.py`）

`_LOAD_STAGES` の直後に新設した、1トランザクション分の段階経過を計測する
小さなクラス。

- `advance(stage)`: 直前段階が計測中であれば `STAGE <transaction> <stage>
  <elapsed_s>` をstdoutへ1行出し、次段階の計測を開始する。呼び出し元（statusの
  組み立て）へは直前段階の所要を表す `" (<stage> <elapsed>s)"` 形式のsuffixを
  返す（最初の段階では `""`）。
- `finish()`: 最終段階のSTAGE行を出し、トランザクション全体の経過秒を返す。

段階名・遷移順は呼び出し元がそのまま渡す値なので不変であり、`_StageTimer` は
計測とログ出力だけを追加する。既存の `_load_input_transaction` /
`_load_session_transaction` / `StageCore.render_final` のsignatureや内部の
`on_stage(...)` 呼び出し系列は一切変更していない。

### 配線した3箇所

- `_queue_load_input`（Load/Rebuild）: `on_stage` を `_StageTimer` でラップし、
  statusを `input load: <stage>…<suffix>` へ、成功時は
  `input loaded (<total>s)` へ変更した。
- `_queue_load_session`（Load session）: 同様に `session load: <stage>…<suffix>`
  → `session loaded (<total>s)`。
- `_queue_final`（Render final）: 単一段階 `"render"` として `_StageTimer` へ通す
  形にした（既存の `time.perf_counter()` 手書き計測を `_StageTimer` へ置き換え、
  STAGE行が追加された点のみが変更）。status表示（`final {elapsed:.1f}s → ...`）
  は変更していない。

`_load_input_transaction` / `_load_session_transaction` を直接呼ぶ既存の
integration test（`test_load_input_transaction_*` 等）は独自の
`on_stage=stages.append` を渡しており `_StageTimer` を経由しないため、無改修で
そのまま通ることを確認した。

### `mitsuba_stage_demo.py`

変更していない。headless session再生logへのsession path/digest追記はStep 3の
範囲（対象ファイルの主変更節に明記済み）であり、Step 1はviewer 3トランザクションの
経過計測に限定した。

## テスト

`tests/test_mitsuba_stage_viewer_worker.py` へ `_StageTimer` の単体テストを5件
追加した（Mitsuba不要）。

- 最初の `advance()` はSTAGE行を出さずsuffixが空であること。
- 2回目の `advance()` が直前段階のSTAGE行を1行だけ出し、
  `" (validate <n>s)"` 形式のsuffixを返すこと。
- `finish()` が最終段階のSTAGE行を出し、総経過秒を返すこと。
- 1度も `advance()` していない `finish()` はSTAGE行を出さないこと。
- `validate → map → prepare → load → smoke → swap` の全段階を流したとき、
  各段階につきちょうど1行のSTAGE行が出て、段階名がそのまま（順序も）ログへ
  反映されること。

既存の段階遷移テスト（`test_load_input_transaction_*`、
`test_load_session_transaction_*` など、`tests/integration/test_mitsuba_stage_viewer.py`
にある約20件）は `_load_input_transaction` / `_load_session_transaction` を
`_StageTimer` を経由しない生の `on_stage` コールバックで直接呼んでおり、無改修で
そのまま通ることを確認した（無回帰）。

## 実測

Mitsuba必須。実行場所は `vdbmat/`、variant `llvm_ad_rgb`（CPU、本機のCUDA
variantは別途Step 5で使う）。checked-in 3 fixtureは
`uv run vdbmat run examples/pipeline_run/configs/<fixture>.run.json` で
canonical run bundleを生成し（`nested_material_cube` は既存の
`.local/blender_improve1/nested_material_cube` を再利用、他2件は新規生成）、
`marble-like` は `.local/marble/bundle`（README_QUICK記載の既存生成物）を
使った。

計測は `ViewerApp.__new__` ＋ 実 `StageCore` で、GUIやviserサーバーを起動せず
`_load_input_transaction` / `_load_session_transaction` /
`core.render_final()` を直接呼ぶ方式を採った（既存integration testの
`test_load_input_transaction_applies_mapping_and_records_derivation` と同型の
組み立て）。mapping適用ありのLoad/Rebuildを初回（derived bundle cache無し）と
2回目（cache再利用）で連続実行し、続けてsession保存→session load、
final render（512×512, spp 128 — 実運用既定値）を計測した。checked-in
3 fixtureには `phase0-provisional-materials-v1` を、`marble-like` には
`.local/marble/marble-like.optical-mapping.json` を適用した。

計測生データ・生成PNG・derived bundleは
`.local/mitsubagui_improve/p5/measure/` に置き、gitには含めていない
（`.local/` は既存 `.gitignore` 対象）。以下は結果の要約のみ。

### Load/Rebuild（mapping適用、final renderを除く）— 秒

| fixture | cold 総計 | 内訳（cold） | warm 総計 | 内訳（warm、map以外は近似不変） |
|---|---|---|---|---|
| nested_material_cube | 1.16 | validate 0.00 / map 1.04 / prepare 0.04 / load 0.01 / smoke 0.02 / swap 0.06 | 0.27 | map: reused cache 0.16 |
| stepped_wedge | 0.61 | validate 0.00 / map 0.35 / prepare 0.03 / load 0.01 / smoke 0.22 / swap 0.01 | 0.13 | map: reused cache 0.07 |
| window_coupon | 1.25 | validate 0.00 / map 0.96 / prepare 0.03 / load 0.01 / smoke 0.22 / swap 0.03 | 0.27 | map: reused cache 0.18 |
| marble-like（`.local`） | 4.42 | validate 0.00 / map 4.00 / prepare 0.14 / load 0.03 / smoke 0.23 / swap 0.02 | 0.88 | map: reused cache 0.64 |

`map` 段階（`regenerate_optical()` によるderived canonical bundle生成、
`run_pipeline()` のatomic publishを含む）が全fixtureで支配的。marble-likeが
突出するのはvoxel数が桁違いに多いため。cache再利用時も `map: reused cache` に
digest照合・bundle検証のコストが残るが、初回に比べ大幅に短い。

### session load（as-is、mapping無し）— 秒

| fixture | 総計 | 内訳 |
|---|---|---|
| nested_material_cube | 0.30 | parse 0.00 / resolve 0.00 / verify 0.19 / prepare 0.04 / load 0.01 / smoke 0.02 / commit 0.05 |
| stepped_wedge | 0.14 | parse 0.00 / resolve 0.00 / verify 0.08 / prepare 0.03 / load 0.01 / smoke 0.02 / commit 0.01 |
| window_coupon | 0.28 | parse 0.00 / resolve 0.00 / verify 0.19 / prepare 0.04 / load 0.01 / smoke 0.02 / commit 0.03 |
| marble-like | 1.01 | parse 0.00 / resolve 0.00 / verify 0.78 / prepare 0.17 / load 0.02 / smoke 0.02 / commit 0.02 |

`verify`（`optical.zarr` の再hash）がここでの支配段階。Verify digestsボタンや
digest cache（Step 3）が効いてくる領域だが、Step 1時点でも全fixtureが1秒程度に
収まる。

### final render（512×512, spp 128）— 秒

| fixture | 経過 |
|---|---|
| nested_material_cube | 5.64 |
| stepped_wedge | 0.94 |
| window_coupon | 2.49 |
| marble-like | 1.47 |

final renderはLoad/Rebuild・session loadの対象外（plan通りcancel判断からは除外）
だが、参考値として記録した。nested_material_cubeが最も長いのは内部境界
（interior mesh）の追加ジオメトリのため。

## cancel採否の判断

**非採用**とする。

採用基準は「明示的Load/Rebuild（final renderを除く）の代表worst-caseが約30秒を
超える場合」。実測worst-caseは marble-like cold の **4.42秒**（checked-in
3 fixtureはいずれも1.3秒未満）であり、基準の1/6程度に収まる。session loadの
worst-caseも1.01秒。abandon型cancelを追加する動機となる「体感の長い待ち」は
現状のfixture規模では発生していない。

経過表示（`_StageTimer` によるstatus suffixと総経過）と、mapping map段階の
cache再利用（cold 4.42s → warm 0.88s、約80%減）で、現状の待ち時間は十分説明可能・
許容範囲と判断する。generation guard（Phase 2〜4で既存）はそのまま将来のcancel
実装の土台として温存されており、将来もっと大きい入力を扱うようになった場合は
このSTAGE logが再判断の実測データになる。

Step 5では、本判断に従い abandon型cancelの実装は行わない（項目をskipし、
plan通りその旨をStep 5報告書へ明記する）。

## reconnect実測

**未実施**（本セッションはブラウザを操作できない非対話環境のため）。

事前調査（plan「前提調査」節）で確認済みの通り、`on_client_connect`
（`mitsuba_stage_viewer.py:1784`）が新client接続時に現在のpreviewを再送する
実装は既に存在する。今回のLoad/Rebuild経過表示の追加はstatus文字列の内容と
STAGE stdout行のみを変えるものであり、`on_client_connect` の配線やclient別
viewport管理には触れていない。したがってLoad/Rebuild進行中のreconnectで新たに
壊れる経路があるとは考えにくいが、実ブラウザでの確認は行っていない。

plan通り、この確認はStep 4（堅牢性ケース）で実ブラウザ手動確認として改めて
実施し、結果をStep 4報告書へ記録する。問題が見つかった場合の修正もStep 4で
行う。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q tests/test_mitsuba_stage_viewer_worker.py -k stage_timer
5 passed in 0.05s

uv run pytest -q --ignore=tests/integration
562 passed in 39.55s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer.py
30 passed, 1 warning in 24.70s
```

（warningはテスト末尾でのviserサーバー停止時 `RuntimeError: Event loop is
closed` という既存の非同期teardown由来のもので、失敗ではなく本Stepの変更に
起因するものではない。全30件は成功している。）

```text
uv run ruff check \
  examples/pipeline_run/demo/mitsuba_stage_viewer.py \
  tests/test_mitsuba_stage_viewer_worker.py
All checks passed!

uv run ruff format --check \
  examples/pipeline_run/demo/mitsuba_stage_viewer.py \
  tests/test_mitsuba_stage_viewer_worker.py
2 files already formatted

git diff --check
問題なし
```

計測生データ・生成PNG・derived bundleは `.local/mitsubagui_improve/p5/measure/`
に置き、git管理対象へ混入していないことを `git status` で確認した
（変更は `mitsuba_stage_viewer.py` と `tests/test_mitsuba_stage_viewer_worker.py`
の2fileのみ）。

## コミット境界としての判断

Step 1完了地点を独立したコミット境界として適切と判断する。

この境界で次が単独で成立する。

- Load/Rebuild・session load・final renderの各段階所要がstatusとSTAGE stdout
  logで観測できる。段階名・遷移順・既存API signatureは無変更。
- 既存のstage-transitionを検証するintegration testは無改修で全通過する
  （`_StageTimer` は `_queue_*` レベルの追加であり、`_load_input_transaction`
  等のsignatureに触れていないため）。
- cancel採否が実測（4 fixture、worst-case 4.42秒 < 基準30秒）に基づき
  「非採用」と判断・記録された。

変更対象は次の2fileだけである。

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`

## 未実施事項

以下は計画どおり次のコミット境界以降に残している。

- Step 2: cleanup規則（swap後の旧session directory破棄、起動時sweep、
  derived cache全削除後の再生成保証）。
- Step 3: InputSessionのdigest cache、Effective stateパネル、
  Verify digestsボタン、final sidecar session、`mitsuba_stage_demo.py`
  のsession再生logへのpath/digest追記。
- Step 4: 代表入力session replay回帰、堅牢性ケース（失敗介在・連続要求・
  接続callback）、**reconnectの実ブラウザ手動確認**（Step 1で未実施のもの）。
- Step 5: `mitsuba_session_compat.py`、README_QUICK運用小節、
  marble-likeでの手動確認一巡。cancelは本Stepの判断により非採用のためskip。

`mitsuba_stage_demo.py`、`mitsuba_viewer_session.py`、`mitsuba_stage_inputs.py`、
`mitsuba_stage_mappings.py`、`mitsuba_stage_regen.py`、`src/vdbmat` は変更して
いない。
