# Step 4 報告 — 契約テスト

## 実施内容

`tests/contract/test_primitive_array_contract.py` を既存契約テスト
（`test_mesh_contract.py`、`test_image_stack_contract.py`）と同水準で
追加した。代表 config は cube 3x2x1（size=4voxel, gap=2voxel,
margin=1voxel）と sphere 2x2x2（同じ寸法パラメータ）の2種。

- **double-run byte equality**: cube config を2回CLI実行し、manifest・
  payload とも byte 一致することを確認。
- **golden digest pin**: cube・sphere それぞれの payload/manifest
  SHA-256 を実行結果から採取してハードコードした。
- **ASCII preview pin**: cube 3x2x1 の中央 z-slice を固定し、
  3×2個の cube 断面（`3333` ブロック）が並んで見えることを確認。
  base 材が非 air（`transparent-resin`）なので背景セルも `1` で
  埋まる（air 宣言はあるが実際には voxel が存在しない、plan の
  `nested_material_cube` と同型の設計どおり）。
- **パラメータ感度**: `counts_xyz`、`primitive`、`primitive_size_m`
  それぞれを変更すると config digest / payload digest が変わることを
  確認。
- **seed 非依存**: `seed` を変えると config digest は変わるが、
  payload（`material_id.npy` のバイト列）は不変であることを確認
  （乱数を使わない契約の明文化）。

## 静的検査・テスト結果

```
uv run ruff check tests/contract/test_primitive_array_contract.py
→ All checks passed!

uv run pytest -q tests/unit tests/contract
→ 322 passed, 2 skipped (PIL 未導入によるスキップ、無関係)
```

## 想定外事項

なし。plan どおりに進行した。
