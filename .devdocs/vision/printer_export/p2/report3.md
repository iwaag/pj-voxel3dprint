# Step 3 報告 — levels 導出ヘルパ（`printer/roundtrip.py`）

## 実施内容

`vdbmat_utils.printer.roundtrip.image_stack_config_from_print_manifest(manifest)`
を新規実装し、`vdbmat_utils.printer` の公開 API（`__init__.py` の
`__all__`）へ追加した。

- `format` / `format_version` を `"vdbmat.print-slices"` / `"1.0.0"` に
  厳密一致で検証する（不一致は明示エラー）。
- `voxel_size_xyz_m` は `printer.dpi_x` / `printer.dpi_y` /
  `printer.layer_thickness_m` の生値から `0.0254 / dpi` の式で再計算する
  （plan の決定事項どおり、`pitch_*_mm` からの mm 逆算はしない）。
- `levels` は `palette`（背景 material_id 0 を含む）から
  `{"rgb": [...], "material_id": ..., "name": ..., "role": ...}` を
  material_id 昇順で機械導出する。Step 2 で固定した rgb levels スキーマを
  そのまま利用する。
- `palette` 欠落・空・エントリのフィールド欠落・rgb 値域外はすべて
  `PrintSlicesError` の明示エラー（既存 `PrintSlicesConfig` の validation
  規約と対称なエラー文言）。

## テスト

`tests/unit/test_printer_roundtrip.py`。`generate-primitive-array` →
`export-print-slices` を実行して得た**実際のマニフェスト**（手書きでは
なく本物の出力）を主な入力にする:

1. `voxel_size_xyz_m` がピッチ式（`0.0254/600`, `0.0254/300`, `27e-6`）と
   bit 一致すること。
2. `levels` が palette の全材料（背景含む）・RGB・role を正しく反映する
   こと。
3. `levels` が material_id 昇順であること。
4. `format` / `format_version` 不一致の拒否。
5. `palette` 欠落、palette エントリの `rgb` 欠落、`printer.dpi_x` 欠落の
   拒否。

## 実行結果

```text
uv run pytest -q tests/unit/test_printer_roundtrip.py   # 8 passed
uv run pytest -q tests/unit tests/contract              # 457 passed（p2 step2完了時 449 + 8、回帰なし）
uv run ruff check src/vdbmat_utils/printer/roundtrip.py src/vdbmat_utils/printer/__init__.py \
  tests/unit/test_printer_roundtrip.py                   # clean
```

## 次ステップへの申し送り

Step 4（往復契約テスト）は `export_print_slices()` →
`image_stack_config_from_print_manifest()` → `convert_image_stack()` を
連結し、`sample_slice()` 出力配列との完全一致を固定する。本ステップの
ヘルパはその両端を繋ぐ部品として想定どおり独立に固定できた。
