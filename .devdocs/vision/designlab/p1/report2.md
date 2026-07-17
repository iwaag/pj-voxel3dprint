# Step 2 報告 — 生成本体

## 実施内容

`vdbmat_utils/primitives/generator.py` に `generate_primitive_array()` を
実装した。

- グリッド導出（`_grid_shape`）: 軸ごとの extent を
  `2*margin + counts*size + (counts-1)*gap` とし、
  `ceil(extent/voxel_size - 1e-6)`（voxelize-mesh と同じ epsilon）で
  セル数を求める。`max_axis_cells`/`max_total_cells` を超えたら
  「粗い voxel size を使え」という具体的な提案付きエラーにする
  （`voxelize-mesh` の `_domain()` と同型）。
- セル分類（`_inside_mask`）: cell-centre サンプリング。
  - cube: 軸ごとに独立な「いずれかのプリミティブの半径窓内か」の
    bool 配列を作り、3軸の AND を取る。gap や margin が非負である限り
    軸ごとの窓は重複しないため、この分離可能な per-cell 述語には
    順序依存・二重塗りの余地がない（plan の risk 節どおり）。
  - sphere: 軸ごとの「最近接プリミティブ中心への距離二乗」を求め、
    3軸分を加算してから半径二乗と比較する。距離二乗の和は軸ごとに
    分離可能なので、軸ごとの最近接中心を組み合わせた点が常に
    大域最小距離を与える（別候補の探索は不要、という数学的事実を
    利用して実装を単純化した）。
- palette: `air`(0, background) + base + inclusion の3エントリ。
  provenance: generator id `vdbmat-utils.primitives.array` v0.1.0、
  `sources=()`（入力ファイルなし）。

## テスト

`tests/unit/test_primitives.py` に生成本体のテストを追加した:

- 整数倍ケースでの厳密 shape・inclusion voxel 数（cube:
  `A*B*C*(size/voxel)^3` に一致）。
- sphere の3軸 flip 対称性（payload 不変）。
- 縮退ケース: `counts=[1,1,1]` かつ `gap=0`/`margin=0`。
- `gap=0` で cube が密着するケース（隙間もオーバーラップも出ないことを
  厳密 voxel 数で確認）。
- 境界 tie（`size == voxel_size` で全セル中心が境界/内部に一致する
  ケース）が閉境界規則で正しく分類されることを確認。
- ガード超過（軸方向・総数方向）が提案文言つきエラーになることを確認。
- dtype（uint16）・3次元配列であること・palette 名の妥当性。
- `seed` を変えても payload（`material_id` 配列）が不変であることを確認
  （config digest が変わることは Step 1 のテストで別途確認済み）。

## 静的検査・テスト結果

```
uv run ruff check src/vdbmat_utils/primitives tests/unit/test_primitives.py
→ All checks passed!

uv run pytest -q tests/unit
→ 273 passed, 2 skipped (既存の PIL 未導入によるスキップ、無関係)
```

## 想定外事項

なし。plan どおりに進行した。
