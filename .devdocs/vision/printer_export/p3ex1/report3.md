# Step 3 報告 — 契約テストの RGBA 再固定

## 実施内容

- `test_print_slices_contract.py` の slice 復号を `read_indexed_png()` から
  `read_png_rgb()` へ変更し、RGBA 出力を RGB 値として検査するようにした。
- golden pixel digest を再生成して固定した。
  - anisotropic / HQ: `2a46ca26381f384e86ef330f5a22455b4b75e41d774dbe212fc40e818f181cf7`
  - multimaterial / HS: `c0dc5520f0f3bba8fbab0e18c3c17b33e01d138881f58fd0e0752fe338a0cca3`
- sampler との復元比較は RGB→material ID の対応表で行うよう変更した。
  palette RGB を変更した場合は PNG の RGB digest が変わり、材料IDサンプリング
  自体は変わらないという新しいエンコード表現に合う契約へ更新した。

digest の変更は indexed の index 配列から RGB 配列へと検査対象の表現が変わった
ことによるもので、`printer/sampler.py` のサンプリングロジック変更によるものでは
ない。同ファイルは未変更である。

## テスト

```text
uv run pytest -q tests/contract/test_print_slices_contract.py \
  tests/contract/test_print_slices_roundtrip.py
# 15 passed

uv run ruff check tests/contract/test_print_slices_contract.py
# All checks passed!

git diff --check
# clean
```

round-trip contract の5基準（完全一致、軸交換/flip、異方性感度、等倍恒等、
double-run）は、RGBA PNG を `read_png_rgb()` が RGB として読む経路で無変更の
まま通過した。

## 次ステップ

Step 4 で `docs/print-slices.md` の PNG encoding と claims を RGBA(32-bit)
出力・実機検証で判明した制約に合わせて更新する。
