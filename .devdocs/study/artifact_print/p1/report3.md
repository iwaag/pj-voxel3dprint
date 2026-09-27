# artifact_print p1 step 3 report — 現行ツールチェーンとのギャップ分析(Q3)

## Done

- `study/3dprint_artifact/pipeline_feasibility.md`:
  - 「今すぐ可能か」への答えを 3 経路に分けた。**0. GrabCAD の通常フルカラー**(本システムを使わず、今すぐ可能。比較の基準になる)、
    **1. MVP ルート**(使い捨てスクリプトで数日)、**2. 本命ルート**(研究開発が必要)。
  - 段ごとのギャップ表(11 段。現状、必要なこと、選択肢、MVP と本命それぞれの難度、工数)。
  - 候補 A(水注)の縮尺別の規模の試算(粗格子のセル数、プリンタピッチのボクセル数、14 µm / 27 µm でのスライス数)。
  - MVP ルートのデータの流れの図と、本命ルートまでの 5 項目の距離。
- 根拠として読んだコード: `vdbmat-utils` の `mesh/voxelizer.py`(上限とトポロジ検査)、`printer/exporter.py` と `docs/print-slices.md`
  (最近傍アップサンプルのみ、スライス単位で書き出し、`max_total_pixels`)、batch1 の 3 つのエクスポータ
  (`work/{fur,agate,amber}/export_*_voxelprint.py`)、`work/resins/{km_surrogate,recipes_to_mapping}.py`、v3 ライブラリ。

## Commands

```bash
sed -n 46,160p vdbmat-utils/src/vdbmat_utils/printer/exporter.py
grep -o "halftone[^,]*\|recipe[a-z_]*" work/agate/export_menou_voxelprint.py work/amber/export_kohaku_tree_voxelprint.py
python3 -c "..."   # 縮尺別の規模の試算(60 / 100 / 251 mm)
```

## Learned

- **plan の MVP 案「(a) 6 材料以下へのパレット量子化」は成り立たない。** Voxel Print では PNG の 1 色が 1 つの物理樹脂に対応するので、
  6 色に量子化すると、白、黒、クリア、C、M、Y の純色に塗り分けることになる。染付の呉須の青のような色は作れない。
  **MVP でも、樹脂を混ぜるディザが必須**になる。ただし、batch1 の 3 部品はすべて「意味ラベル → 配合 → 3D ハッシュディザ」で刷られており、
  この方式はそのまま移植できる。意味ラベルの数は 6 に縛られない。
- 既存の `export-print-slices` は、ソースの最近傍アップサンプルしかしない。MVP には使えず、batch1 と同じく
  スライスを直接書き出すスクリプトが要る。本体への実装は次フェーズの候補にする。
- 60 mm に縮小した水注は、プリンタピッチで 21.6 億ボクセル(14 µm で 2,340 スライス)。粗格子(0.5 mm)なら 87 万セルで、
  `voxelize-mesh` の上限内に入る。100 mm にすると、1 軸 128 セルの上限も `max_total_pixels` も超える。
- 本システムにしか無い強み(半透明の配合設計と見え方の予測)は、GrabCAD の通常フルカラーでは代わりがきかない。
  一方、不透明な表面色だけなら GrabCAD が既に解いているので、**基準として 1 回刷って比べる**のが、次フェーズで最初にやるべきこと。

## Skipped

- 工数はすべて見積もり(実装はしていない)。Step 6 で、MVP ルートの一部(1、2、4、5、6、8、9 段)を実際に通して裏を取る。
