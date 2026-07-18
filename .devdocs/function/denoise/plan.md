# denoise 実装計画 — stage viewer / stage demo のノイズ低減(OptiX デノイズ)

作成日: 2026-07-18

## この計画の位置づけ

`mitsuba_stage_viewer.py` / `mitsuba_stage_demo.py` のレンダリング結果は、
「誘電体殻(デルタ境界で NEE 無効)の中の散乱媒質」という volpath にとって
最悪クラスの被写体を扱うため、spp を 1024 まで上げても粒状ノイズが残る。
本計画は、Mitsuba 組み込みの `mi.OptixDenoiser` を **final render と settled
preview のオプション後処理**として組み込み、低い spp で実用画質を得られるように
する。カノニカルなエクスポータ(`prepare_mitsuba_scene()` / `render_mitsuba()` /
`MitsubaExportConfig`)には一切手を入れない — デノイズは demo トラックの
表示品質改善であり、光学係数の科学的評価には未加工画像を使い続ける。

参照した前提資料:

- `README_QUICK.md`(Use Case 8 の stage demo / viewer / session 節)
- `.local/local_env_memo.md`
- `.devdocs/vision/mitsubagui_improve/roadmap.md` と Phase 1〜5 の plan / report
- `mitsuba_stage.py` / `mitsuba_stage_core.py` / `mitsuba_stage_binder.py` /
  `mitsuba_stage_demo.py`

## 前提調査(確認済み事実)

### ノイズの発生源(2026-07-18 に実測)

primitive-array 10 倍スケール白バンドル
(`primitive-array-demo-10x-white-1b16d5b2975c`、white-resin: σs=1000/m,
アルベド ≈ 99.9%, 4mm キューブで τs=4)を `viewer.stage.json` の設定・
512²・spp 256・`cuda_ad_rgb` でレンダリングした結果:

| 設定 | mean | max | 所見 |
|---|---|---|---|
| max_depth 8 | 0.108 | 1.02 | キューブが暗く汚れた灰色。パス打ち切りでエネルギー約 1/3 損失 |
| max_depth 64 | 0.164 (+52%) | 13.2 | 明るさ回復。firefly が出るが粒状ノイズは残存 |
| max_depth 64 + `mi.OptixDenoiser` | — | — | **spp 256 でほぼノイズレス** |

- ノイズの主因は誘電体境界(exterior IOR 1.48 / interior 1.52)がデルタ BSDF で
  あるため光源への直接サンプリングが効かないこと。spp では 1/√N でしか収束しない。
- `mi.OptixDenoiser` は `cuda_ad_rgb` variant なら追加依存なしで動く
  (`denoiser = mi.OptixDenoiser(input_size=[W, H]); denoised = denoiser(image)`)。
  `llvm_ad_rgb`(CPU)には対応デノイザがない。

### 組み込みポイント

- final render は `mitsuba_stage_core.py` の `StageCore.render_final()` に一本化
  されており、`mi.render` の結果 `image` を `write_bitmap` する直前が挿入点。
  settled preview は `render_preview()`(`convert_to_bitmap` 前)が挿入点。
- ヘッドレス側は `mitsuba_stage_demo.py` の `render_stage()` が同じく一本化
  されている(legacy CLI 形式と `--session` replay の共用経路)。
- レンダー設定は `mitsuba_stage.py` の `RenderSettings`(stage-config の
  `render` 節)が持つ。現行 writer は stage-config **1.1.0**
  (`STAGE_CONFIG_FORMAT_VERSION`)、reader は 1.0.0 / 1.1.0 を受理し、
  1.0.0 文書には `max_depth=8` を補う前例がある(`max_depth` 追加時の
  1.0→1.1 と同じ拡張手順が使える)。
- viewer session(`vdbmat.viewer-session` 1.1.0)は effective stage config を
  丸ごと内包するため、`render` 節にフィールドを足せば session への記録・
  ヘッドレス replay への伝搬・`mitsuba_session_compat.py` の stage digest 比較は
  追加実装なしで追従する。
- GUI 側は `mitsuba_stage_binder.py` が Render タブの widget
  (`add_number` 群)と `StageConfig` の相互変換を持つ。

## ゴール

1. Render タブのチェックボックス(既定 off)で final render と settled preview に
   OptiX デノイズを適用でき、spp 256〜512 で従来の spp 1024 超の見た目品質を
   得られる。
2. デノイズ設定が stage preset / viewer session に記録され、
   `mitsuba_stage_demo.py`(`--denoise` / `--session` replay)で同一 GPU・
   同一ドライバなら final PNG を再現できる。
3. デノイズ有効時も**未加工画像とその PIXELSTATS が常に残る**(科学的比較・
   回帰シグナルはデノイズの影響を受けない)。
4. CPU variant(`llvm_ad_rgb`)でデノイズを要求した場合は、黙って無視せず
   明示的に失敗する(本リポジトリの「approximate silently しない」原則)。

## 非ゴール

- カノニカルエクスポータ(`src/vdbmat`)への変更。`MitsubaExportConfig` に
  denoise フィールドは足さない。
- AOV(albedo / normal)誘導デノイズ。`OptixDenoiser(albedo=True, ...)` は
  aov 積分器のラッピングとセンサ変換の受け渡しが必要で、初版の効果
  (RGB のみで十分実用)に対して複雑さが釣り合わない。必要になったら別計画。
- volpath 側の分散低減(guiding、firefly クランプの積分器実装、MIS 改良など)。
  firefly はデノイザがほぼ吸収することを確認済み。
- interactive preview(ドラッグ中の低 spp 画像)へのデノイズ適用。設定変更の
  応答性を優先し、settled preview と final のみとする。
- CPU 用代替デノイザ(OIDN 等の新規依存追加)。

## 成果物と配置

| 成果物 | 配置 | git管理 |
|---|---|---|
| `RenderSettings.denoise`(stage-config 1.2.0) | `mitsuba_stage.py` | する |
| `StageCore` のデノイズ適用と raw/denoised 二重出力 | `mitsuba_stage_core.py` | する |
| Render タブ checkbox | `mitsuba_stage_binder.py` | する |
| `--denoise` CLI フラグ | `mitsuba_stage_demo.py` | する |
| unit / integration テスト | `vdbmat/tests/` 既存置き場 | する |
| README_QUICK / stage viewer manual の追記 | 各既存文書 | する |
| 検証用レンダリング画像 | `.local/denoise/` | しない |

## 実装ステップ

### Step 1 — stage-config 1.2.0: `render.denoise` フィールド

- `RenderSettings` に `denoise: bool = False` を追加する。
- `STAGE_CONFIG_FORMAT_VERSION` を `1.2.0` に上げ、受理集合に
  `{1.0.0, 1.1.0, 1.2.0}` を設定する。1.0.0 / 1.1.0 文書には
  `denoise=False` を補う(1.0→1.1 の `max_depth` と同じ規則。旧文書は
  新フィールドを含み得ないので黙補で安全)。
- 型・未知キー・バージョンの検証は既存の `render` 節検証に相乗りする
  (bool 以外は拒否)。
- `stage_config_to_dict` が `denoise` を常に書き出すことを確認する。

完了条件: 1.0.0 / 1.1.0 / 1.2.0 の読み込みと 1.2.0 の書き出しの unit テストが
通り、既存 preset(`stage-default` / `stage-highkey`)が無変更で読める。

### Step 2 — StageCore: デノイズ適用と raw 出力の保全

- `StageCore` にデノイザの遅延生成キャッシュを持たせる
  (`mi.OptixDenoiser(input_size=[W, H])` は解像度ごとに 1 個。解像度変更で
  作り直し)。
- `render_final()`: `config.render.denoise` が真なら
  1. 未加工画像を `<basename>.raw.png` として先に書く
  2. PIXELSTATS は**未加工画像から**計算する(回帰シグナル不変)
  3. デノイズ結果を従来のパス(`final.png`)へ書き、status 文字列に
     `denoise=optix` を追記する
  偽なら従来と完全同一(`.raw.png` は書かない)。
- `render_preview()`: settled preview(`spp=None` で呼ばれる側)のみ、
  `denoise` 真ならデノイズしてから `convert_to_bitmap` する。stats は
  未加工から計算。interactive(明示 spp 指定)には適用しない。
- **variant ガード**: `denoise=True` かつ variant が `cuda_ad_rgb` 系でない
  場合、final render / settled preview は例外を投げ、GUI の status line に
  「denoise には --variant cuda_ad_rgb が必要」の旨が出るようにする。
  チェックボックス操作時点での即時検証は Step 3 で行う。

完了条件: cuda ホストで、denoise on の final render が `.raw.png` と
デノイズ済み PNG の両方を出力し、PIXELSTATS が raw 側と一致する。off の
出力が従来と pixel-identical である。

### Step 3 — GUI(binder)と session の配線

- Render タブに `denoise (OptiX)` checkbox を追加し、既存の
  widget ⇄ `RenderSettings` 双方向バインドに載せる。
- viewer 起動時に variant が CUDA 系でなければ checkbox を disabled にする
  (viser の `disabled` 属性。理由をツールチップ/ラベルで示す)。これにより
  Step 2 の例外ガードは防御第二層になる。
- session save / load / replay は effective stage config 経由で自動追従する
  はずなので、**変更なしで**次を確認する: denoise on の session を save →
  viewer `--session` 起動と `mitsuba_stage_demo.py --session` replay の両方で
  denoise が再適用されること。`mitsuba_session_compat.py` が denoise 差を
  stage digest の DIFF として報告すること。
- `_final_render_key` / preview の rebuild 判定に `denoise` を含める必要が
  ないこと(scene には影響せず後処理のみ)を確認し、含めない。

完了条件: GUI で on/off を切り替えて final render し、`final.session.json`
に `denoise` が記録され、headless replay が同一 GPU で pixel-identical に
再現する。

### Step 4 — `mitsuba_stage_demo.py` と文書

- legacy CLI 形式に `--denoise` フラグを追加する(preset の値を上書きする、
  `--max-depth` 等と同じ優先規則)。`--session` 形式では新規フラグを受けず、
  session 内の値のみを使う(既存の「session replay に上書きを混ぜない」原則)。
- `render_stage()` に Step 2 と同じ raw 保全・PIXELSTATS 規則・variant
  ガードを実装する(viewer と demo で挙動が分岐しないよう、デノイズ適用
  ヘルパは `mitsuba_stage.py` か core の関数として 1 箇所に置く)。
- README_QUICK の stage demo / viewer 節に、ノイズの構造的原因(デルタ誘電体
  境界 + 散乱媒質)、max_depth の推奨(散乱材を含む被写体では 32〜64)、
  denoise の使い方と再現性の但し書きを追記する。
  `vdbmat/docs/gui/stage_viewer_manual.md` の Render タブ節にも checkbox を
  追記する(GUI 変更なので gui_image_export の再キャプチャ対象)。

完了条件: `--denoise` 付き demo 実行が raw / denoised を出力し、README の
コマンド例がそのまま動く。

### Step 5 — 一巡検証

- 白バンドル(前提調査と同じ入力)で spp 256 + max_depth 64 + denoise の
  final render を GUI から実行し、従来の spp 1024・denoise なしと目視比較して
  改善を確認する。結果 PNG と PIXELSTATS を `.local/denoise/` に残し、
  report1.md に記録する。
- session save → headless replay の pixel-identical 確認(同一 GPU)。
- `llvm_ad_rgb` viewer で checkbox が disabled であること、demo で
  `--denoise --variant llvm_ad_rgb` が明示エラーになることを確認する。

完了条件: report1.md に測定値・画像パス・確認項目の結果が揃う。

## 検証方針

- unit: stage-config 1.2.0 の読み書き・旧版黙補・型検証(`mitsuba_stage.py`
  の既存テストの隣)。デノイズ適用ヘルパは Mitsuba 依存を関数境界で切り、
  「raw を先に書く」「stats は raw から」の規則を numpy スタブで検証する。
- integration: 既存
  `test_mitsuba_stage_viewer_regression.py` の枠組みに denoise on の
  final render ケースを追加する。ただし OptiX は GPU 必須のため
  `cuda_ad_rgb` が初期化できない環境では skip する(既存の variant 選択
  ヘルパに準じる)。デノイズ出力の pixel 回帰は行わない(ドライバ依存のため)
  — 検証するのは「raw が従来と一致」「denoised が生成され raw と異なる」
  「stats が raw 由来」まで。
- 手動: Step 5 の一巡。

## リスクと方針

### OptiX デノイズ出力のドライバ依存性

デノイズ結果は OptiX / ドライバのバージョンに依存し得るため、
「同一入力 → pixel-identical」の再現契約は**同一 GPU・同一ドライバに限定**
される。raw PNG と PIXELSTATS を常に残すことで、環境をまたぐ比較は raw 側で
行える。この限定を README_QUICK と session 節の但し書きに明記する。

### CPU variant との非対称

denoise は CUDA 専用機能になる。GUI は disabled 表示、headless は明示エラーで
「黙って無視」を避ける。CPU 用デノイザの追加は依存が増えるため見送り
(必要になったら別計画で OIDN を検討)。

### settled preview の応答性

デノイザ生成は解像度ごとに 1 回、適用は 256px で数十 ms オーダーの見込みだが、
初回生成が遅い場合は settled preview への適用を checkbox とは別の
開発時判断で final のみに縮退できるよう、適用箇所を 1 ヘルパに集約しておく。

### firefly の残留

max_depth を上げると firefly(実測 max 13.2)が出るが、デノイザがほぼ吸収する
ことを確認済み。吸収しきれないケースが出たら、クランプはデノイズ前の
後処理として同じヘルパに足せる設計にしておく(本計画では実装しない)。
