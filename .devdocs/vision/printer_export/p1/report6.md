# Step 6 報告 — docs と手動確認（最終ステップ）

## 実施内容

### docs

`vdbmat-utils/docs/print-slices.md` を新規作成した。構成:

- claims / non-claims（GCVF受理はPhase 3まで未確認、Phase 2往復契約は
  未実装である旨を明記）。
- `PrintSlicesConfig` の全フィールド表。
- 格子導出・サンプリング規則（ピッチ式、`ceil(extent/pitch - 1e-6)`、
  最近傍規則、flip の適用位置、軸交換時の転置）。
- PNGエンコード規則（byte表現がPillowバージョンに依存しうる旨、実色数
  再検査の説明）。
- 出力レイアウトとサイドカーマニフェストの全フィールド表
  （`palette` が GrabCAD GUI での色→材料対応付け手順書を兼ねる旨を明記）。
- worked example と実機ソフト確認（Phase 3）への申し送り。

`vdbmat-utils/README.md` は Step 4 で既に `docs/print-slices.md` への
参照と使用例を追加済み（本ステップで作成した docs ファイルとリンクが
揃った）。

### 手動 walkthrough

`.local/printer_export/p1/`（git非管理）に成果物を作成:

```bash
uv run vdbmat-utils generate-primitive-array \
  --config .local/printer_export/p1/primarray.json \
  --out .local/printer_export/p1/input --name demo
# counts_xyz=[3,2,1], primitive_size=0.4mm, gap=0.2mm, margin=0.1mm

uv run vdbmat-utils export-print-slices \
  .local/printer_export/p1/input/demo.voxels.json \
  --config .local/printer_export/p1/printslices.json \
  --out .local/printer_export/p1/out --name demo
# dpi_x=600 / dpi_y=300 / layer_thickness_m=27e-6 (High Speed) / max_materials=3
```

出力サマリ: `slices: 23  pixels: 43x15`、
`physical size (mm): x=1.8203 y=1.2700 z=0.6210`。

**手計算による寸法照合**（primitive-array の抽出式 + printer_export の
格子導出式、両方 plan/docs記載の式をそのまま使用）:

- 入力extent: `x = 2*0.1 + 3*0.4 + 2*0.2 = 1.8mm`,
  `y = 2*0.1 + 2*0.4 + 1*0.2 = 1.2mm`, `z = 2*0.1 + 1*0.4 + 0*0.2 = 0.6mm`
  （voxel_size 0.1mm → shape_zyx=(6,12,18)、既存 primitive-array 契約テストの
  既知値と一致）。
- printer pitch: `pitch_x = 25.4/600 = 0.042333mm`,
  `pitch_y = 25.4/300 = 0.084667mm`, `pitch_z = 0.027mm`。
- 導出値: `width = ceil(1.8/0.042333 - 1e-6) = 43`,
  `height = ceil(1.2/0.084667 - 1e-6) = 15`,
  `n_slices = ceil(0.6/0.027 - 1e-6) = 23`。
- 物理寸法: `43*0.042333=1.8203mm`, `15*0.084667=1.2700mm`,
  `23*0.027=0.6210mm`。

いずれもCLI出力・マニフェストの値と完全一致した。

**目視確認**: `slice_0010.png`（立方体本体の中央付近）を画像として開き、
green（黒不透明樹脂、パレット指定色）の正方形が3×2個並んでいることを
確認した（`counts_xyz=(3,2,1)` と一致）。600/300dpiの異方性により
正方形が横に間延びして見える（X:Yピクセル比が物理的に2:1になる設計と
整合）。サムネイル表示では解像度が低くY方向の2段目が見えにくかったため、
`read_indexed_png()` でピクセル値を直接ダンプし、次のASCII格子で
2段×3列（計6個）の材料インデックスであることを確認した:

```
1111111111111111111111111111111111111111111
1122222222221111122222222211111222222222111
1122222222221111122222222211111222222222111
1122222222221111122222222211111222222222111
1122222222221111122222222211111222222222111
1122222222221111122222222211111222222222111
1111111111111111111111111111111111111111111
1111111111111111111111111111111111111111111
1122222222221111122222222211111222222222111
...(2段目、6行分)...
1111111111111111111111111111111111111111111
```

（`1` = transparent-resin、`2` = black-opaque-resin のパレットindex。
`air` はprimitive-arrayの設計通りどのセルにも塗られないため出現しない。）

`slice_0000.png`（z方向のマージン内、立方体本体の外側）は全ピクセルが
`1`（base材料）のみであることも確認し、z方向マージンの扱いが期待通り
であることを確認した。

## 実行結果

```text
uv run pytest -q tests/unit tests/contract   # 431 passed（全ステップ累計、回帰なし）
uv run ruff check .                           # 本フェーズで変更したファイルはすべてクリーン
                                               # （既存の無関係な1件のみ: tests/integration/test_formation_workflows.py、
                                               #   本フェーズ対象外のため未修正）
```

## 完了条件の充足確認

- `export-print-slices` が config JSON 1枚で決定論的にスライスPNG群 +
  マニフェストをatomicに発行する: ✅（Step 3/4、本ステップの手動確認で再確認）。
- 出力格子導出・最近傍indexがunit testで全数固定されている: ✅（Step 2）。
- 契約テスト（digest pin、double-run、デコード検証、感度、seed非依存、
  色数制約）が通る: ✅（Step 5）。
- 制約違反が発行前の明示エラーになり、失敗時に `<out>` に何も残らない:
  ✅（Step 1/3のunit test、Step 5の色数制約契約テスト）。
- docs / READMEが更新され、既存契約・既存テストに変更がない: ✅（本ステップ、
  かつ全431テストが既存分を含め回帰なし）。
- 手動walkthroughがreportに記録され、検証成果物が `.local/printer_export/p1/`
  に隔離されている: ✅（本ステップ）。

## 次フェーズへの申し送り

Phase 1完了。Phase 2（往復契約テストとドキュメント統合）は
`convert-image-stack` 側のRGB/パレット対応拡張か往復専用読込かの決定を
要する（`.devdocs/vision/printer_export/p1/plan.md` のリスク節参照）。
Phase 3（実機ソフト検証）は本フェーズの出力に対する外部ソフトでの
GCVF生成確認が主目的で、本フェーズのdocsに記載した「未確認」事項
（軸対応の実際の解釈、背景色の扱い等）を検証する。
