# Step 6 報告 — 手動 walkthrough（最終ステップ）

## 実施内容

`.local/printer_export/p2/`（git 非管理）に成果物を作成し、README_QUICK
Use Case 4d の記載どおりに CLI を通した。Phase 1 walkthrough
（report6）と同じ 3×2×1 cube primitive array 入力を使い、往復検証
（`convert-image-stack` への読み戻し）まで追加で確認した。

```bash
uv run vdbmat-utils generate-primitive-array \
  --config .local/printer_export/p2/primarray.json \
  --out .local/printer_export/p2/input --name demo
# counts_xyz=[3,2,1], primitive_size=0.4mm, gap=0.2mm, margin=0.1mm
# 0 (air): 0px, 1 (transparent-resin): 912, 3 (black-opaque-resin): 384

uv run vdbmat-utils export-print-slices \
  .local/printer_export/p2/input/demo.voxels.json \
  --config .local/printer_export/p2/printslices.json \
  --out .local/printer_export/p2/slices --name demo
# slices: 23  pixels: 43x15
# physical size (mm): x=1.8203 y=1.2700 z=0.6210
# material 1: 10635 px, material 3: 4200 px
```

出力サマリは Phase 1 report6 の値と完全に一致した（同一入力・同一
プリンタプロファイルのため、期待どおり byte 単位の物理量が再現）。

### levels 導出（Step 3 のヘルパを使用）

手書きの対応表を書かず、サイドカーマニフェストから機械導出した:

```bash
uv run python3 -c "
import json
from vdbmat_utils.printer.roundtrip import image_stack_config_from_print_manifest

manifest = json.loads(open('.local/printer_export/p2/slices/demo/demo.printslices.json').read())
config = image_stack_config_from_print_manifest(manifest)
open('.local/printer_export/p2/roundtrip.json', 'w').write(config.to_json())
"
```

導出された `roundtrip.json`:

```json
{"format":"png","levels":[
  {"material_id":0,"name":"air","rgb":[0,0,0],"role":"background"},
  {"material_id":1,"name":"transparent-resin","rgb":[255,0,0],"role":"material"},
  {"material_id":3,"name":"black-opaque-resin","rgb":[0,255,0],"role":"material"}
],"local_to_world":null,"seed":0,
 "voxel_size_xyz_m":[4.233333333333333e-05,8.466666666666666e-05,2.7e-05]}
```

`voxel_size_xyz_m` はプリンタピッチ式（`0.0254/600`, `0.0254/300`,
`27e-6`）とそのまま bit 一致しており、mm 経由の逆算ではないことが値
そのものから確認できる。

### 往復読み戻し

```bash
uv run vdbmat-utils convert-image-stack .local/printer_export/p2/slices/demo \
  --config .local/printer_export/p2/roundtrip.json \
  --out .local/printer_export/p2/roundtrip_out --name demo
# 0 (air): 0, 1 (transparent-resin): 10635, 3 (black-opaque-resin): 4200
```

エクスポート時のサマリ（`material 1: 10635 px`, `material 3: 4200 px`）と
**完全一致**した。

### 照合

```bash
uv run vdbmat-utils material-counts .local/printer_export/p2/roundtrip_out/demo.voxels.json
# 0 (air, background): 0
# 1 (transparent-resin, material): 10635
# 3 (black-opaque-resin, material): 4200
```

エクスポート時のマテリアル別ピクセル数サマリと完全一致することを確認した。

### 目視確認（往復後ボクセル）

```bash
uv run vdbmat-utils preview-slices .local/printer_export/p2/roundtrip_out/demo.voxels.json --axis z
```

z=11（立方体本体の中央付近）で、Phase 1 report6 の ASCII 格子と**同一の
パターン**（3×2 個の `3`（black-opaque-resin）配置、600/300dpi 由来の
X:Y 異方性による横長の見た目）を確認した:

```
1111111111111111111111111111111111111111111
1133333333331111133333333311111333333333111
1133333333331111133333333311111333333333111
1133333333331111133333333311111333333333111
1133333333331111133333333311111333333333111
1133333333331111133333333311111333333333111
1111111111111111111111111111111111111111111
1111111111111111111111111111111111111111111
1133333333331111133333333311111333333333111
...(2段目、6行分)...
1111111111111111111111111111111111111111111
```

これは export 直後の生ボクセルではなく、**PNG に一度書き出してから
読み戻した**ボクセルであり、往復契約が実データでも成立していることを
目視でも確認した。

## README_QUICK との整合性

Use Case 4d に記載したコマンド列（`generate-primitive-array` →
`export-print-slices` → `preview-slices` → `convert-image-stack`
（導出 config）→ `preview-slices` → `material-counts`）を実際にこの順で
実行し、記載と実際の出力・手順にずれがないことを確認した。ドキュメントの
修正は不要だった。

## 実行結果

```text
uv run pytest -q tests/unit tests/contract   # 462 passed（Step 5 完了時から変更なし、回帰なし）
uv run ruff check .                          # 本フェーズ変更ファイルはすべてクリーン
                                              # （既存の無関係な1件のみ、p1 report6 記載のとおり本フェーズ対象外）
```

検証成果物はすべて `.local/printer_export/p2/` に隔離され、git 管理
ファイルへローカルパスや生成物は混入していない。

## 完了条件の充足確認（roadmap Phase 2 / p2 plan）

- 往復契約テスト（完全一致・軸/flip 変種・異方性感度・等倍恒等・
  double-run）が `uv run pytest tests/contract` で通る（Step 4）。
- levels config がサイドカーマニフェストから機械導出され、導出規則が
  docs に手書き再現可能な形で記載されている（Step 3、Step 5）。
- `convert-image-stack` が色 PNG スタックを受理し、既存グレースケール
  契約（unit / contract）が無変更で通っている（Step 2）。
- README_QUICK の新 Use Case どおりに、primitive array →
  スライス PNG 群 → 読み戻し → `preview-slices` 目視まで手動 CLI で
  通ることが本報告に記録されている（本ステップ）。
- 手動検証成果物が `.local/printer_export/p2/` に隔離され、git 管理
  ファイルにローカルパス・生成物が混入していない（本ステップ）。

Phase 2 の全ステップが完了した。往復で Phase 1 側の欠陥は一件も
見つからず、sampler / exporter への fix は発生しなかった（Step 4 報告に
記載済み）。
