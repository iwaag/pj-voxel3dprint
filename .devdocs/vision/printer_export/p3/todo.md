# Phase 3 TODO — GrabCAD実機ソフト検証

目的: `export-print-slices` の出力PNG群を **GrabCAD Voxel Print Utility** に
読み込ませ、GCVF生成が通るかを確認する（親: `../roadmap.md` Phase 3）。
コーディング作業は無い。データ生成（開発機）→ 転送 → GrabCADで確認 →
結果記録、の4段。

## 前提

- [ ] 開発機（このリポジトリ、`vdbmat-utils` セットアップ済み: `README_QUICK.md`）
- [ ] GrabCAD Print + Voxel Print Utility が使えるWindows機
      （Stratasys公式ガイド:
      <https://support.stratasys.com/en/Software/GrabCAD-Print/Tips-Guides-and-FAQs/Guide-to-Voxel-Printing>）

## 1. テストデータ生成（開発機、リポジトリルートで実行）

- [ ] 作業ディレクトリと設定ファイル3つを作る（すべて `.local` 配下 = git非管理）:

```bash
mkdir -p .local/printer_export/p3
```

`.local/printer_export/p3/primarray.json` （3×2×1個の緑キューブ入りブロック）:

```json
{
  "voxel_size_xyz_m": [0.0001, 0.0001, 0.0001],
  "primitive": "cube",
  "counts_xyz": [3, 2, 1],
  "primitive_size_m": 0.0007,
  "gap_m": 0.0002,
  "margin_m": 0.0001,
  "base_material_name": "transparent-resin",
  "inclusion_material_name": "black-opaque-resin"
}
```

`.local/printer_export/p3/pad.pipeline.json` （検証B用: 周囲に背景=黒の余白を追加）:

```json
{
  "inputs": [{"id": "base", "manifest_path": "input/demo.voxels.json"}],
  "steps": [
    {"op": "pad", "from": "base",
     "before_zyx": [0, 5, 5], "after_zyx": [0, 5, 5], "as": "padded"}
  ],
  "output": {"ref": "padded"}
}
```

`.local/printer_export/p3/printslices.json` （High Quality構成、27µm層厚）:

```json
{
  "dpi_x": 600.0,
  "dpi_y": 300.0,
  "layer_thickness_m": 2.7e-05,
  "max_materials": 6,
  "palette": {
    "1": [255, 0, 0],
    "3": [0, 255, 0]
  },
  "background_rgb": [0, 0, 0],
  "printer_x_axis": "x",
  "printer_y_axis": "y",
  "flip_x": false,
  "flip_y": false,
  "flip_z": false,
  "name_prefix": "slice_",
  "index_start": 0,
  "min_slices": 30,
  "max_total_pixels": 4000000000
}
```

- [ ] 生成とエクスポートを実行:

```bash
cd vdbmat-utils

# ボクセル生成（検証A: 背景なし）
uv run vdbmat-utils generate-primitive-array \
  --config ../.local/printer_export/p3/primarray.json \
  --out ../.local/printer_export/p3/input --name demo

# 検証B: 周囲へ背景(黒)余白を追加した版
uv run vdbmat-utils apply-pipeline \
  --config ../.local/printer_export/p3/pad.pipeline.json \
  --out ../.local/printer_export/p3/input --name demo_pad

# スライスPNG群を出力（A・B両方）
uv run vdbmat-utils export-print-slices \
  ../.local/printer_export/p3/input/demo.voxels.json \
  --config ../.local/printer_export/p3/printslices.json \
  --out ../.local/printer_export/p3/out --name demo

uv run vdbmat-utils export-print-slices \
  ../.local/printer_export/p3/input/demo_pad.voxels.json \
  --config ../.local/printer_export/p3/printslices.json \
  --out ../.local/printer_export/p3/out --name demo_pad
```

- [ ] エクスポート成功サマリを控える（後でGrabCADの表示と照合する）。
      検証Aの目安: **34スライス、64×22px、
      物理寸法 x≈2.709mm / y≈1.863mm / z=0.918mm**。
      30スライス未満エラーが出たらこのtodoの設定ミス（`primitive_size_m`
      を確認）。
- [ ] 中間スライス（例 `out/demo/slice_0017.png`）を画像ビューアで開き、
      **赤地に緑の四角が3×2個**（横長に見えるのは600/300dpi異方性のため正常）
      であることを確認。`demo_pad` は同じ絵の周囲に黒縁が付く。

## 2. Windows機へ転送

- [ ] `out/demo/` と `out/demo_pad/` の2フォルダをzipしてWindows機へコピー。
      各フォルダの中身: `slice_0000.png`〜 と `<name>.printslices.json`
      （JSONはGrabCADには読ませない。人間用の対応表 + 検算資料）。

## 3. GrabCAD Voxel Print Utility で GCVF 生成

まず `demo`（検証A）で実施。通ったら `demo_pad`（検証B）も同様に。

- [ ] Voxel Print Utility を起動し、スライスフォルダとして `demo` を指定
      （プレフィックス `slice_`、連番0始まり）。
- [ ] パラメータをエクスポート設定と一致させる:
      **X = 600 dpi / Y = 300 dpi / スライス厚 = 0.027 mm (27 µm)**。
- [ ] 色→材料の割り当て。対応表（`demo.printslices.json` の `palette`）:
      - 赤 `[255, 0, 0]` = transparent-resin（透明系材料を割り当て）
      - 緑 `[0, 255, 0]` = black-opaque-resin（不透明系材料を割り当て）
      - 黒 `[0, 0, 0]` = 背景（材料なし・空領域のつもりで出力している）
- [ ] GCVF生成を実行。**成否にかかわらず、画面のエラー/警告は全文控える**
      （スクリーンショット推奨）。

## 4. 確認ポイント（結果と一緒に必ずメモ）

1. **受理可否**: GCVF生成が通ったか。エラー時は全文と、どの段階
   （読み込み/色検出/生成）か。
2. **色検出数**: GrabCADが検出した色数（Aは2色のはず。3色以上 =
   中間色混入でこちらのバグ、要報告）。
3. **背景の扱い**（検証Bが本命）: 黒 `[0,0,0]` が「材料なし」と解釈される
   のか、黒にも材料割り当てを要求されるのか。
4. **寸法表示**: GrabCAD側に表示されるモデル寸法が、サイドカー
   `demo.printslices.json` の `grid.physical_mm`
   （x≈2.709 / y≈1.863 / z=0.918 mm）と一致するか。
   **どれか1軸が約2倍ずれていたら軸対応（600/300dpi）の解釈違い** —
   最重要の確認項目。
5. **命名規則**: プレフィックス・連番・4桁ゼロ埋めがそのまま受理されたか、
   何か変更を要求されたか。

## 5. 結果の記録と反映

- [ ] 結果を `.devdocs/vision/printer_export/p3/report1.md` に記録する
      （確認ポイント1〜5への回答 + 実行したGrabCAD側の設定値）。
      スクリーンショット等の生データは `.local/printer_export/p3/` に置き、
      **commitしない**（ローカル環境情報を含むファイルのgit管理は厳禁）。
- [ ] 齟齬が見つかった場合: 修正はPhase 1実装へのfixとして扱う。report1.md
      の記録を渡して開発側（Claude）に依頼すればよい。修正不要だった場合も
      「実機確認済みの解釈」として `vdbmat-utils/docs/print-slices.md` の
      non-claims更新を開発側に依頼する（これでPhase 3完了）。

## 注意

- 本フェーズの範囲は **GCVF生成の受理まで**。実プリント（物理造形）は
  行わない（roadmap参照）。
- GrabCAD側の設定を上記から変えて通した場合（dpi、命名等）、その変更内容
  こそが本フェーズの成果。必ず記録する。
