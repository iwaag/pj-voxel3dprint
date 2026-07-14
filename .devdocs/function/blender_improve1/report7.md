# blender_improve1 追加修正報告 — Step 7

- **位置づけ**: Step 1〜6 完了後の実モデル差し替えで判明した欠陥の補正
- **ステータス**: 完了

## 判明した問題

`window_coupon` をカメラへ近づけたテンプレートに流し込んだところ、次の 3 点が
独立して描画を妨げていた。

1. `Studio` View Layer の `use` が `False` で、Cycles が実レンダーを行わず黒 PNG を
   保存していた。
2. Blender の material slots は object ではなく mesh data 側にあるため、
   `target.data = replacement.data` だけではテンプレート材質を保持できず、PLY が
   無材質の白い表面になった。
3. PLY は canonical world coordinates を頂点に持つため、モデルごとの
   local-to-world translation やbounds centreが異なる。プレースホルダーの object
   transform をそのまま使うだけでは、別モデルがカメラ外へ移動した。

## 修正

### 元テンプレート

`.local/local_demo/template_scene/cube_diorama.blend` を pinned Blender 4.5.11 LTS で
開き、`Studio` View Layer の `use=True` だけを設定して同じファイルへ保存した。
ユーザーが調整したカメラ位置 `(0.740499, -0.131400, -0.066436)` は維持されている。

### `blender_template_swap.py` / `blender_template_hybrid.py`

- 交換前の mesh material slots を退避し、交換後 mesh へ再割り当てする。
- 交換前プレースホルダーの world-space bounds centre を記録する。
- replacement PLY の local-space bounds centre を求める。
- target の scale/rotation を維持したままtranslationだけを補正し、replacement の
  world-space bounds centreを旧プレースホルダーcentreへ一致させる。
- hybridでは補正後の同じ `matrix_world` をVDB objectへ適用する。
- 有効なView Layerが0個なら、黒PNGを黙って保存せず明示エラーにする。
- 入力パスを絶対化し、samplesの正値検証と診断ログを強化する。

## 検証

手動の中心補正・材質再割り当て・作業用テンプレートを使わず、元テンプレートから
`window_coupon` のhybrid renderを実行した。

```text
HYBRID target=exterior-000 exterior=exterior-000.ply vdb=volume.vdb
scale=20 center=(0.227871, 0.349829, -0.43013)
materials=1 layers=Studio
grids=cycles_absorption,cycles_scattering,g,ior,
      sigma_a_b,sigma_a_g,sigma_a_r,sigma_s_b,sigma_s_g,sigma_s_r
mode=qualitative-uncalibrated

PIXELSTATS min=0.0039 max=0.9294 mean=0.2330 std=0.1450
```

保存 `.blend` の再確認:

- exterior material: `vbdmat-glass`
- exterior bounds centre: `(0.227871, 0.349829, -0.430130)`
- exterior と VDB の `matrix_world`: 一致
- enabled View Layer: `Studio`

外面のみの `blender_template_swap.py` も同じ `window_coupon` で完走した。

```text
SWAP target=exterior-000 exterior=exterior-000.ply
center=(0.227871, 0.349829, -0.43013) materials=1 layers=Studio
PIXELSTATS min=0.0000 max=0.9451 mean=0.2322 std=0.1444
```

静的検査:

```text
ruff check: pass
py_compile: pass
```

確認成果物:

- `.local/blender_improve1/window_coupon_hybrid-auto-fixed.png`
- `.local/blender_improve1/window_coupon_hybrid-auto-fixed.blend`
- `.local/blender_improve1/window_coupon_surface-auto-fixed.png`
