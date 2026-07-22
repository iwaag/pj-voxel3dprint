# Step 2 報告 — exporter の RGBA 差し替え

## 実施内容

- `export_print_slices()` のサンプリングと material ID→palette index の
  lookup はそのまま維持し、書き出し直前だけで index を RGB へ展開した。
  alpha は全ピクセル `255` の `(H, W, 4)` `uint8` 配列として
  `write_rgba_png()` に渡す。
- `_recheck_actual_colors()` は indexed PNG の index 集合ではなく、
  `read_png_rgb()` で復号した RGB 値集合が宣言パレットの部分集合であることを
  検査する方式へ更新した。
- 出力レイアウトテストで、実際の slice PNG が mode `"RGBA"` であることを
  固定した。さらに writer をテスト用に差し替えて宣言外 RGB を混入させ、
  実色数再検査が `PrintSlicesError` と atomic publish の未公開状態を保つことを
  確認した。

`printer/sampler.py`、物理格子導出、材料カウント、sidecar manifest は変更して
いない。材料IDの最近傍サンプリングという契約への変更はない。

## テスト

```text
uv run pytest -q tests/unit/test_printer_png.py tests/unit/test_printer_exporter.py
# 21 passed

uv run ruff check src/vdbmat_utils/printer/exporter.py tests/unit/test_printer_exporter.py
# All checks passed!
```

## 次ステップ

Step 3 で exporter 契約テストの復号を RGB ベースへ変更し、RGBA のピクセル配列に
対する golden digest を再固定する。Phase 2 の往復契約も同時に実行する。
