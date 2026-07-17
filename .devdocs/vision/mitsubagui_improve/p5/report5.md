# mitsubagui_improve Phase 5 実施報告 — Step 5（最終）

`plan.md` の Step 5（variant診断・文書・（採用時）cancel）まで完了し、
Phase 5計画全体（Step 1〜5）が完了した。CPU/GPUのscientific同一性を
判定する `mitsuba_session_compat.py` を追加し、README_QUICKへ運用小節を
追記、`.local` の `marble-like` bundleで切替往復・session保存・headless
再現・digest検証・variant比較の一巡を手動確認した。cancelはStep 1の判断
（worst-case 4.42秒 < 採用基準30秒）により非採用のためskipした。

## 変更内容

### 新規 `mitsuba_session_compat.py`（variant診断）

plan通り、viser／Mitsuba非依存のpure moduleとして追加した
（`vdbmat/examples/pipeline_run/demo/mitsuba_session_compat.py`）。

- `compare_sessions(a: Path, b: Path) -> SessionCompatReport`: 既存の
  `viewer_session_from_json()` reader経由で2つの `vdbmat.viewer-session`
  文書を読み、`mitsuba.variant` を除く次のfieldを突合する。
  - `input.kind` / `input.path` / `input.optical_sha256` /
    `input.run_manifest_sha256`
  - `mapping.path` / `mapping.digest` / `mapping.derived_optical_sha256`
    （mapping無しのsessionは全field `(none)` として比較され、片方だけ
    mapping有りなら差分として検出される）
  - `stage.effective_digest`（`ViewerSession.__post_init__` が
    `stage_config_digest(stage_config)` と一致することを既に保証している
    ため、この1 digestの比較だけでstage／render設定全体の差分を検出できる。
    field単位の再分解はしていない）
  - `mitsuba.seed`
  - `SessionCompatReport(scientifically_equal: bool, differences: tuple[(field, a, b), ...])`
    を返す。`variant` はどちらのfieldにも現れない
    （差分としても等価判定にも一切関与しない設計）。
- 壊れたsession文書は `viewer_session_from_json()` が投げる
  `ViewerSessionError` をそのまま伝播させる（この moduleは診断を
  再実装しない）。
- CLI: `python examples/pipeline_run/demo/mitsuba_session_compat.py
  A.session.json B.session.json`。両sessionのvariantを表示した後、
  `scientifically_equal` なら `SCIENTIFICALLY_EQUAL true` を出してexit 0、
  そうでなければ `SCIENTIFICALLY_EQUAL false` と `DIFF <field>: a=... b=...`
  を列挙してexit 1。`ViewerSessionError` はstageとmessageを添えて
  `SystemExit` にする。Mitsuba/viser importが無いため `uv run --group
  mitsuba` すら不要（`uv run python ...` で動く）。

### README_QUICKへの運用小節

`## Overall Workflow Summary` の直前、「Replay a Saved Session
Headlessly」の後に `#### Operations: Staying in Control During Day-to-Day
Use` を追加した。

- 段階語彙とroadmap名の対応表、経過表示（status suffixと総経過）と
  `STAGE <transaction> <stage> <elapsed_s>` stdout logの読み方。
- cancel非採用の理由（Step 1実測4.42秒 < 基準30秒）への言及とreport1.mdへの
  参照。
- cleanup規則4種（swap後の旧work directory破棄、起動時sweep対象限定、
  derived cacheの全削除安全性、`.tmp-*` の次回実行時除去）。
- `Render final` のsidecar session（`vdbmat.viewer-session` そのもの）と、
  構成できない場合の `session sidecar skipped` 挙動。
- Effective stateパネルとVerify digestsボタン（digest cacheの再利用と、
  明示操作でのみ再hashする設計）。
- `mitsuba_session_compat.py` によるvariant比較診断の手順とCLI例。
- `.local` の `marble-like` bundleでの手動確認手順（後述の実施結果への
  参照を含む）。

執筆中に、checked-in `phase0-provisional-materials-v1*` mappingを
`marble-like` へ適用しようとすると `map` 段階の
`InputLoadError`（palette coverageがmaterial *名* も突き合わせるため、
`calcite-matrix` 等と `transparent-resin` 等が一致せず失敗）になることを
実際の手動確認中に発見した。README原稿は当初checked-inのmappingを流用する
想定で書いていたが、`marble-like` 自身の
`.local/marble/marble-like.optical-mapping.json` を使う手順に修正した
（詳細は次節）。

### 変更なし

`mitsuba_stage_viewer.py`、`mitsuba_stage_demo.py`、
`mitsuba_viewer_session.py`、`mitsuba_stage_regen.py`、
`mitsuba_stage_inputs.py`、`mitsuba_stage_mappings.py`、`src/vdbmat` は
本Stepで一切変更していない。cancel（abandon型）はStep 1の判断により
非採用のため実装していない。

## cancel: 非採用のためskip

Step 1報告書の判断（採用基準「明示的Load/Rebuildの代表worst-caseが約30秒を
超える場合」に対し実測worst-caseはmarble-like coldの4.42秒）に従い、
本Stepでもabandon型cancelの実装は行っていない。plan通りこの項目をskipし、
ここに明記する。

## `.local` marble-likeでの手動確認

本セッションは実ブラウザを操作できない非対話環境のため、GUIではなく
viewer core（`ViewerApp.__new__` ＋ 実 `StageCore`）を直接駆動する
使い捨てscriptで一巡した（Step 1のtiming計測、Step 4のtest moduleと同じ
組み立て方）。実行場所は `vdbmat/`、成果物は
`.local/mitsubagui_improve/p5/marble-manual/` にのみ置き、gitには含めて
いない。

### 発見: checked-inマッピングはmarble-likeに適用できない

`vdbmat.optics.mapping._require_palette_coverage()` はmaterial IDだけでなく
**名前**も突き合わせる。`marble-like` の材料は `calcite-matrix` /
`dolomite-vein` / `dark-fracture-fill`（IDは0/1/2/3でchecked-inマッピングと
重なる）だが、名前が `phase0-provisional-materials-v1*` の
`transparent-resin` 等と一致しないため、適用は
`InputLoadError`（`map`段階、`OpticalMappingError` 由来）で失敗する。
README運用小節はこれを踏まえ、`marble-like` 自身の
`.local/marble/marble-like.optical-mapping.json` を使う手順に修正した
（このことはPhase 5の他Stepでは表面化しなかった — checked-in3
fixtureはすべてchecked-inマッピングと材料名が揃っているため）。

### 実施内容と結果

`marble-like.optical-mapping.json`（元のまま）と、`material_id=1` の
`sigma_a_rgb_per_m` を変えたローカルの「tinted」派生版を用意し、
`llvm_ad_rgb` と `cuda_ad_rgb` それぞれで次を実施した。

1. as-is → own-mapping → tinted → as-is の順にLoad/Rebuildを4回連続実行
   （切替往復）。全て成功、`derivation` はmapping適用時のみ設定される
   ことを確認。
2. tinted mappingを適用した状態で `Render final`
   （128×128, spp 16）→ sidecar session書き出し（skipなし）。
3. `Verify digests` 相当の `_verify_digests()` 呼び出し →
   `ok — matches cached digests`。
4. sidecar sessionを `mitsuba_stage_demo.py --session` でheadless再生 →
   `MAPPING marble-like-tinted.optical-mapping.json digest=... cache=reused`
   → viewer finalとheadless PNGが画素完全一致。
5. 上記1〜4をvariant違い（`llvm_ad_rgb`／`cuda_ad_rgb`）で独立に実施し、
   両方のsidecar sessionを `mitsuba_session_compat.py` で比較。

結果:

```text
=== variant=llvm_ad_rgb ===
switch -> as-is: 0.90s derivation=no
switch -> provisional(own-mapping): 4.47s derivation=yes
switch -> tinted: 4.42s derivation=yes
switch -> as-is again: 1.06s derivation=no
final sidecar note: None
verify digests: verify digests: ok — matches cached digests
MAPPING marble-like-tinted.optical-mapping.json digest=sha256:8ee2078... cache=reused
pixel-exact match: True
PIXELSTATS variant=llvm_ad_rgb seed=42 max_depth=8 min=0 max=1.21534 mean=0.0741581 std=0.119814

=== variant=cuda_ad_rgb ===
switch -> as-is: 1.96s derivation=no
switch -> provisional(own-mapping): 4.57s derivation=yes
switch -> tinted: 3.94s derivation=yes
switch -> as-is again: 0.79s derivation=no
final sidecar note: None
verify digests: verify digests: ok — matches cached digests
MAPPING marble-like-tinted.optical-mapping.json digest=sha256:8ee2078... cache=reused
pixel-exact match: True
PIXELSTATS variant=cuda_ad_rgb seed=42 max_depth=8 min=0 max=1.21534 mean=0.0741581 std=0.119814

=== mitsuba_session_compat ===
scientifically_equal=True
SCIENTIFICALLY_EQUAL true — variant is the only possible difference (CLI exit code: 0)
```

- 切替往復4回（as-is→own-mapping→tinted→as-is）はいずれも成功し、
  Load/Rebuild時間はStep 1計測（cold 4.42秒台、`map` 段階が支配的）と
  同水準で新たな遅延は見られない。
- sidecar sessionは両variantともskipされず書かれ、`Verify digests`は
  外部改変が無い状態で期待通り `ok`。
- viewer finalとheadless再生PNGは両variantでそれぞれ画素完全一致
  （`mitsuba_stage_demo.py --session` によるsidecar再現が
  `marble-like` でも成立することを確認）。
- `mitsuba_session_compat.py` は2 sessionを `scientifically_equal=True`
  と正しく判定した（実際に同一input/mapping/stage/seedで異なるvariantに
  設定して保存したペア）。
- 参考情報として、今回の設定（128×128, spp 16, seed 42, max_depth 8）では
  `llvm_ad_rgb` と `cuda_ad_rgb` のPIXELSTATS（min/max/mean/std）が
  偶然一致した。plan・README双方に明記した通り、variant間の画素完全一致は
  要求も期待もしておらず、`mitsuba_session_compat.py` の役割は
  「同じ条件を指定したことの確認」であって画素比較そのものではない。

成果物（sidecar session、mapping copy、final/headless PNG、derived
bundle）は `.local/mitsubagui_improve/p5/marble-manual/` にのみ置き、
`git status` で追跡対象への混入が無いことを確認した（`.local/` は
`.gitignore` 対象）。

## テスト

### Mitsuba不要unit test（新規）

`tests/test_mitsuba_session_compat.py`（11件）:

- variantのみ差 → `scientifically_equal=True`、`differences=()`。
- 完全一致 → 同上。
- `input.optical_sha256` / `input.run_manifest_sha256` 差の個別検出。
- `mapping.digest` / `mapping.derived_optical_sha256` 差の個別検出
  （両方mapping有りのケース）。
- mapping有無の非対称（片方のみmapping） → `mapping.path` 差として検出。
- stage/render差（widthのみ変更） → `stage.effective_digest` の1 field
  差としてのみ検出されること（field分解をしていない設計の固定）。
- `mitsuba.seed` 差の検出。
- 壊れたsession文書（digest形式違反）→ `ViewerSessionError` がそのまま
  伝播すること。
- CLI: 等価時にexit 0で `SCIENTIFICALLY_EQUAL true` を出力、差分時に
  exit 1で `SCIENTIFICALLY_EQUAL false` と `DIFF ...` 行を出力すること。

既存の `tests/test_mitsuba_viewer_session.py` 等が持つsession構築helper
（`_bundle_session` 相当）と同型の最小helperをこのtest fileに用意し、
`vdbmat.fixtures` 等の重い依存は使っていない（Mitsuba不要、0.4秒台）。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run ruff check \
  examples/pipeline_run/demo/mitsuba_session_compat.py \
  tests/test_mitsuba_session_compat.py \
  tests/integration/test_mitsuba_stage_viewer_regression.py
All checks passed!

uv run ruff format --check (同上)
3 files already formatted

uv run pytest -q --ignore=tests/integration
585 passed in 40.03s

uv run --group mitsuba-viewer pytest -q tests/integration/
64 passed, 2 skipped, 2 warnings in 48.87s

git diff --check
問題なし
```

（skip・warningの内容はStep 1〜4報告書に記載済みのものと同じで、本Stepの
変更に起因するものではない。）

`git status`（`vdbmat` submodule内）は新規2fileのみを示し、リポジトリ
ルートでは `README_QUICK.md` の変更1fileのみを示す。`.local` 配下の
成果物混入は無い。

## Phase 5全体の完了条件との対応

plan「完了条件」節の各項目に対して:

- 代表入力×mappingのsession replay自動回帰（画素完全一致・provenance）:
  Step 4で固定済み（6代表対、9 test）。
- 失敗介在・連続切替後もcommit済み状態不変、reconnect後の回復: Step 4で
  自動回帰固定（失敗介在・連続切替）。reconnectは実ブラウザでの目視確認が
  非対話環境の制約で最後まで未実施のまま（Step 1・4・5いずれの報告書にも
  明記済み）、代わりにcode経路レベルのunit検証（Step 4）で根拠を固定した。
- `Render final` のsidecar sessionとheadless再現一致: Step 3で実装、
  Step 4・本Stepの手動確認で代表入力／marble-likeとも確認済み。
- Effective stateパネルとVerify digests: Step 3で実装済み。
- cleanup規則（swap後破棄・起動時sweep・cache削除安全性・`.tmp-*`）:
  Step 2で実装・文書化済み、本Stepでmarble-likeに対しても
  Load/Rebuildの複数回実行が問題なく動作することを確認。
- 段階所要の観測とcancel採否判断: Step 1で実測・記録済み（非採用）。
- `mitsuba_session_compat` によるCPU/GPU科学同一性判定と標準手順の文書化:
  本Stepで完了。
- README_QUICKの運用小節: 本Stepで追記完了。
- 既存回帰の無回帰、動作確認成果物の `.local` 隔離: 本Stepで確認済み。

**実ブラウザでのreconnect目視確認のみ**が、この非対話環境の制約により
Phase 5全体を通して未実施のまま残っている。plan「リスクと打ち切り条件」の
reconnect節が明記する代替（「再接続後にstatusとpreviewが回復すること」を
code経路レベルで固定し、完了条件をそこまでに限定する）を、Step 4の
`test_client_connect_callback_resends_current_preview_pixels` で既に
適用済みであり、本Stepで新たに講じる対応はない。

## コミット境界としての判断

Step 5完了地点、すなわちPhase 5計画全体の完了地点として適切と判断する。

この境界で次が単独で成立する。

- `mitsuba_session_compat.py` が2 sessionの科学同一性（variant除く）を
  判定し、CLIとしても使える。
- README_QUICKの運用小節が、段階語彙・cleanup・追跡・ドリフト検査・
  variant比較・`marble-like` 手動確認の6項目を一箇所にまとめている。
- `marble-like` での切替往復・sidecar・digest検証・headless再現・
  variant比較の一巡が実測済みで、結果が本報告書に残っている。
- 既存585件のunit testと64件のintegration testに無回帰。

変更対象は次の3fileである。

- `vdbmat/examples/pipeline_run/demo/mitsuba_session_compat.py`（新規）
- `vdbmat/tests/test_mitsuba_session_compat.py`（新規）
- `README_QUICK.md`（運用小節の追記）

## 未実施事項（Phase 5全体を通じて）

- 実ブラウザでのLoad/Rebuild進行中reconnect目視確認。非対話環境の制約に
  よりPhase 5を通じて未実施。plan既定の代替方針（code経路レベルの
  unit検証への限定）を適用済み。
- cancel（abandon型）はStep 1の実測判断により非採用。

以上でPhase 5計画（`.devdocs/vision/mitsubagui_improve/p5/plan.md`）の
Step 1〜5すべてが完了した。
