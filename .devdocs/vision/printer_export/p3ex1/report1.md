# Step 1 報告 — RGBA reader/writer

## 実施内容

- `image/png.py` に `write_rgba_png()` を追加した。Pillow の mode `"RGBA"`
  で固定圧縮パラメータを使って書き出し、リサイズ・アンチエイリアス・ICC
  変換を経由しない。
- `read_png_rgb()` が mode `"RGBA"` を受理するようにした。全ピクセルの
  alpha が `255` であることを検証し、RGB のみを既存どおり `(H, W, 3)`
  `uint8` 配列で返す。alpha が一つでも `255` 以外なら明示エラーにする。
- 既存の indexed-palette (`"P"`) と `"RGB"` の読込、および
  `write_indexed_png()` / `read_indexed_png()` は変更していない。

## テスト

```text
uv run pytest -q tests/unit/test_printer_png.py
# 12 passed

uv run ruff check src/vdbmat_utils/image/png.py tests/unit/test_printer_png.py
# All checks passed!
```

追加したテストは、RGBA writer→reader の RGB 恒等性、非不透明 alpha の明示的な
拒否を対象とする。既存の `"P"` / `"RGB"` 受理とグレースケール拒否も同じ
テストファイルで引き続き通過している。

## 次ステップ

Step 2 で exporter の最終エンコードを indexed-palette から RGBA へ差し替え、
実色数再検査を RGB 値集合で行うよう更新する。
