# Step 1 報告 — 色 PNG reader（`image/png.py`）

## 実施内容

`read_png_rgb(path) -> NDArray[uint8]`（shape `(H, W, 3)`）を
`vdbmat-utils/src/vdbmat_utils/image/png.py` に追加した。

- 受理モード: `"P"`（`getpalette()` のテーブル直引きで展開。`read_indexed_png()`
  と同じ経路を再利用し、Pillow の `convert("RGB")` には依存しない）と `"RGB"`
  （そのまま `np.asarray`）。
- 拒否モード: `"L"` / `"RGBA"` / その他すべて明示エラー
  （`{path.name}: only indexed-palette ('P') or 'RGB' PNG is supported, got
  mode {mode!r}`）。
- lazy import + `image` extra 未導入時の actionable エラーは既存
  `read_png()` / `write_indexed_png()` と同一規約。

## テスト

`tests/unit/test_printer_png.py`（既存の write/read indexed PNG テストが
置かれているファイル。plan 記載の `test_image_png.py` 相当ファイルはこちら）
へ追加:

1. `write_indexed_png()` → `read_png_rgb()` の恒等性（パレット展開込み、
   plan Step 1 の狙いどおり）。
2. mode "RGB" の読込一致。
3. mode "L"（グレースケール）拒否。
4. mode "RGBA" 拒否。
5. `image` extra 未導入時のエラー型。

## 実行結果

```text
uv run pytest -q tests/unit/test_printer_png.py   # 11 passed（新規5件含む）
uv run pytest -q tests/unit tests/contract        # 436 passed（回帰なし、p1完了時 431 + 5）
uv run ruff check src/vdbmat_utils/image/png.py tests/unit/test_printer_png.py  # clean
```

## 次ステップへの申し送り

Step 2（`image/stack.py` の levels rgb 対応）はこの `read_png_rgb()` を
使って色スタックを読み込む。
