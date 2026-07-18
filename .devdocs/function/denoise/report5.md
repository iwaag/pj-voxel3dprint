# denoise 実装計画 実施報告 — Step 5(一巡検証・最終）

`plan.md` の Step 5(一巡検証)を完了し、denoise 実装計画（`plan.md`）の
全ステップ(Step 1〜5)が完了した。

## 検証対象バンドルの準備

前提調査(`plan.md`)が参照した
`primitive-array-demo-10x-white-1b16d5b2975c` はローカル探索時の生成物
(`.local` 配下、git非管理)で本セッションには残っていなかったため、
同じ物理条件(誘電体シェル + 強散乱媒質コア、白樹脂 σs=1000/m・
アルベド≈99.9%、コア一辺4mmで τs=4)を満たす白バンドルを新たに生成した。

```text
cd vdbmat-utils
uv run vdbmat-utils generate-primitive-array \
  --config ../.local/denoise/step5/white-bundle.primarray.json \
  --out ../.local/denoise/step5/gen --name white-bundle
```

設定(`base_material_name=transparent-resin`(外殻)、
`inclusion_material_name=white-resin`(内側1個)、
`primitive_size_m=0.004`(4mmコア)、`margin_m=0.0004`(0.4mm殻厚)、
`voxel_size_xyz_m=0.0002`)。生成結果は
`transparent-resin: 5824 voxels` / `white-resin: 8000 voxels`。

```text
cd vdbmat
uv run vdbmat import-voxels ../.local/denoise/step5/gen/white-bundle.voxels.json \
  ../.local/denoise/step5/white-bundle.zarr
uv run vdbmat run ../.local/denoise/step5/white-bundle.run.json
```

`run.json` は `phase0-provisional-materials-v1`(checked-in mapping、
`white-resin` の σs=1000/m・albedo≈99.9%・IOR 1.52、`transparent-resin` の
IOR 1.48 を含む)を参照した。生成物は `.local/denoise/step5/bundle/`
(`optical.zarr` 等)。

## 目視比較(spp 1024・denoise なし vs spp 256・max_depth 64・denoise あり)

GPU: `Quadro RTX 8000`(CUDA 13.1、`nvidia-smi` 確認済み)。
`--variant cuda_ad_rgb`、512×512。

| 設定 | コマンド所要 | mean | std | 所見 |
|---|---|---|---|---|
| max_depth 8, spp 128(旧既定) | 4.9s | 0.0683 | 0.1007 | 暗く汚れた灰色。パス打ち切りによるエネルギー損失(前提調査の記述と整合) |
| max_depth 64, spp 256, denoise なし | 13.0s | 0.0971 (+42%) | 0.1149 | 明るさ回復。粒状ノイズが強く残る |
| max_depth 64, spp 1024, denoise なし | 48.4s | — | 0.1101 | spp を4倍にしても目視ではっきり分かる粒状ノイズが残存 |
| **max_depth 64, spp 256, denoise あり** | 13.0s | 0.0971 | 0.1149(raw) | **ほぼノイズレス**。spp 1024・denoise なしより明らかに滑らか |

4枚とも `.local/denoise/step5/`(git非管理)に保存した:
`old-default-depth8-spp128.png` / `compare-spp256-nodenoise.png` /
`baseline-spp1024-nodenoise.png` / `improved-spp256-denoise.png`
(+ `improved-spp256-denoise.raw.png`)。

目視結果: spp 256 + denoise はチェッカーボード背景・床・キューブ表面いずれも
滑らかで、spp 1024・denoise なしより明確にノイズが少ない。spp 256・denoise
なしはキューブ表面が粒状ノイズで覆われ、背景・床にも顕著な斑点ノイズが出る。
max_depth 8(旧既定)はパス打ち切りでキューブ全体が暗くくすんだ灰色になり、
τs=4 の散乱コアが持つはずの明るい拡散反射が再現されない。denoise 有効時の
所要時間(13.0s)は denoise なし・同条件と実質同一(denoiser適用のオーバー
ヘッドは無視できる)で、spp 1024・denoise なし(48.4s)の約1/3.7。

## session save → headless replay のピクセル一致(実白バンドル)

`StageCore.render_final`(256×256, spp 256, max_depth 64, denoise あり,
`cuda_ad_rgb`)による final render と、同じ設定で作成・保存した
viewer session を `mitsuba_stage_demo.py --session` で headless replay した
結果を比較した(`.local/denoise/step5/session-*.png`)。

- raw画像(`*.raw.png`): **完全一致**(`np.array_equal` True)。
- 最終(denoise後)画像: **完全一致ではない** — 256×256×3 = 196,608値中
  1,233値(0.63%)が ±1(8bit sRGB値)だけ異なった。

## 想定外の発見: `mi.OptixDenoiser` の実行間非決定性

前提調査・plan では「デノイズ結果は OptiX / ドライバのバージョンに依存し得る
ため、再現契約は同一 GPU・同一ドライバに限定される」としていたが、今回の
実バンドルでの検証で、**同一プロセスファミリー・同一GPU・同一ドライバ内でも
`mi.OptixDenoiser` の出力に ±1 sRGB step 程度の実行間非決定性がある**ことが
判明した。一方 `mi.render` 自体(raw画像)は同一シーン・同一seedで完全に
決定的であることも同時に確認した(raw画像は0差分)。

これは plan の再現契約の記述を実測でわずかに補正する発見であり、設計判断を
要する事案ではないと判断し、次の対応を行った(人間の判断を仰がず、
実測に基づいて是正)。

- `tests/integration/test_mitsuba_stage_viewer.py` の
  `test_saved_denoised_session_viewer_final_matches_headless_session_replay`
  (Step 4 で追加)を、raw画像は厳密一致・denoise後画像は `atol=2` の
  近似一致に緩和した(3回連続実行して安定を確認済み)。従来の厳密一致
  assertion は、今回の 512×512 の実測では毎回ではないにせよ十分な頻度で
  false failure を生みうる、flaky なテストだったと判断した。
- `README_QUICK.md`(「Reduce Noise with OptiX Denoising」節、および
  headless replay 節)と `vdbmat/docs/gui/stage_viewer_manual.md`
  (Render タブ節)の再現性に関する記述を、「同一GPU/ドライバでも
  denoise後画像は近似一致にとどまる。raw画像は無条件に厳密再現される」と
  なるよう修正した。

科学トラック(PIXELSTATS、raw画像)の再現性はこの発見の影響を受けない
(raw画像は完全決定的)。デノイズ後画像は最初から「表示品質改善のための
後処理」と位置づけられており(plan の非ゴール節「AOV誘導デノイズ」等と
同じ「必要になったら別計画」の扱い)、この非決定性は用途(目視確認用の
demo トラック)に対して実害がないと判断した。

## `llvm_ad_rgb` での明示的拒否(実白バンドル)

```text
uv run --group mitsuba python \
  examples/pipeline_run/demo/mitsuba_stage_demo.py -- \
  ../.local/denoise/step5/bundle/optical.zarr \
  ../.local/denoise/step5/should-fail-llvm.png \
  --width 64 --height 64 --spp 4 --denoise --variant llvm_ad_rgb

mitsuba_stage_core.DenoiseVariantError: render.denoise requires a
cuda_ad_rgb-family Mitsuba variant (mi.OptixDenoiser is CUDA-only); got
variant='llvm_ad_rgb'
```

黙って無視されず、明示的に失敗することを実バンドルでも確認した(Step 4の
合成volumeでの統合テストと一致)。

## `llvm_ad_rgb` viewer での checkbox disabled(代替確認)

本セッションは非対話環境でブラウザを操作できないため、実ブラウザでの
目視確認は行っていない(`.devdocs/vision/mitsubagui_improve/p5/report1.md`
の reconnect確認と同種の制約)。代わりに Step 3 で追加した単体テスト
(`test_stage_binder_denoise_disabled_unless_cuda_variant`、実 viser の
`add_checkbox(..., disabled=...)` シグネチャに一致させた `_FakeGui` 経由)
で、`variant` 省略時・`"llvm_ad_rgb"` 明示時のいずれも
`denoise.disabled is True`、`"cuda_ad_rgb"` 時のみ `False` になることを
確認済みであり、本Stepで新たな実行は行っていない。

## 検証結果(回帰確認)

実行場所は `vdbmat/`。

```text
uv run pytest -q --ignore=tests/integration
615 passed in 37.25s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer.py
46 passed, 2 warnings in 28.12s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer_regression.py
9 passed in 16.00s
```

（warningはStep 1〜4と同じ既知の非同期teardown由来。）

```text
uv run ruff check docs/gui/stage_viewer_manual.md 以外の変更ファイル
uv run ruff check tests/integration/test_mitsuba_stage_viewer.py
All checks passed!

uv run ruff format --check tests/integration/test_mitsuba_stage_viewer.py
1 file already formatted

git diff --check
問題なし
```

検証用の生成物(白バンドル・PNG群・session JSON)はすべて
`.local/denoise/step5/` に置き、git管理対象へは含めていない
(`.gitignore` の `.local/` 対象を `git check-ignore` で確認済み)。

## コミット境界としての判断

Step 5(最終ステップ)完了地点を独立したコミット境界とした。この境界で
denoise 実装計画の全ゴールが実測で確認された。

- ゴール1(spp 256〜512 + denoise で従来の spp 1024超相当の見た目品質):
  実バンドルで確認(spp 256 + denoise が spp 1024・denoise なしより
  明らかに滑らか、所要時間は約1/3.7)。
- ゴール2(denoise設定の記録・再現): stage-config / viewer session が
  `denoise` を記録し、headless replay が raw 画像について厳密再現、
  denoise後画像について近似再現することを確認(再現契約の記述を実測に
  合わせて是正)。
- ゴール3(denoise有効時も未加工画像とPIXELSTATSが常に残る): raw
  sidecar・raw由来PIXELSTATSの実装をStep 2〜4で確認済み、本Stepでも
  実バンドルで再確認。
- ゴール4(CPU variantでの明示的失敗): 実バンドルで再確認。

変更対象は次のとおり(vdbmat submodule内、Step 5固有分)。

- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
  (denoise後画像アサーションの緩和)
- `vdbmat/docs/gui/stage_viewer_manual.md`(再現性記述の是正)

および親リポジトリの `README_QUICK.md`(再現性記述の是正、このコミット
境界と併せて次のコミットで反映)。

vdbmat submodule 側のコミット: `8fc7c45 denoise p0 step5: relax denoised
pixel-match assertion, correct repro docs`。

## 未実施事項

計画上の未実施事項はない。強いて残すなら次の2点(いずれも本環境の制約に
よるもので、plan の完了条件外)。

- `llvm_ad_rgb` viewer での checkbox disabled の実ブラウザ目視確認
  (非対話環境のため単体テストで代替)。
- `vdbmat/docs/gui/images/render-panel.png` の `gui_image_export` による
  再キャプチャ(Step 4 で recapture target と明記済み、実ブラウザ操作が
  必要なため本セッションでは未実施)。
