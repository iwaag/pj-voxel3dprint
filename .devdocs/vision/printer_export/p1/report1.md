# Step 1 報告 — config契約（`printer/types.py`）

## 実施内容

- `vdbmat-utils/src/vdbmat_utils/printer/__init__.py` を新規作成し、
  `PrintSlicesError`（field_path + message 形式、`PrimitiveArrayError` と同型）
  を定義した。
- `vdbmat-utils/src/vdbmat_utils/printer/types.py` を新規作成し、
  `PrintSlicesConfig(GeneratorConfig)` を frozen dataclass（`kw_only=True`）
  として実装した。plan記載のフィールド一式（`dpi_x`/`dpi_y`/
  `layer_thickness_m`/`max_materials`/`palette`/`background_rgb`/
  `printer_x_axis`/`printer_y_axis`/`flip_x`/`flip_y`/`flip_z`/
  `name_prefix`/`index_start`/`min_slices`/`max_total_pixels`）を持つ。
- `__post_init__` で以下を検証する:
  - `dpi_x`/`dpi_y`/`layer_thickness_m` は有限かつ正値。
  - `max_materials` は 1..6 の整数。
  - `printer_x_axis`/`printer_y_axis` は `"x"`/`"y"` のいずれかで、互いに相異。
  - `background_rgb` は各要素 0..255 の整数3要素。
  - `palette` は非空 dict。キーは10進文字列（material_id）で `"0"`（背景）
    禁止。値は各要素 0..255 の整数3要素。RGB重複（palette間・
    background_rgbとの衝突の両方）を明示エラー。
  - palette エントリ数 > `max_materials` を明示エラー。
  - `flip_*` は bool、`name_prefix` は非空文字列、`index_start`/
    `min_slices`/`max_total_pixels` は下限付き整数。
- 未知フィールド拒否・round-trip・digest 安定性は基底 `GeneratorConfig` の
  既存機構（`from_json`/`to_json`/`config_digest`）にそのまま乗っている
  （追加実装なし、契約を確認するテストのみ追加）。

## テスト

`vdbmat-utils/tests/unit/test_printer_types.py` を新規作成（34ケース）:

- 既定値の確認、canonical JSON round-trip、未知フィールド拒否。
- digest 安定性（同一config）、digest の seed 依存性。
- 境界値・不正値の一括拒否テスト（`dpi_x`/`layer_thickness_m` の非正値、
  `max_materials` の範囲外、軸対応の不正値・重複、`background_rgb` の
  範囲外・型不正、`palette` の空・背景id混入・キー型不正・RGB範囲外・
  RGB重複（palette間 / background_rgbとの衝突）・max_materials超過、
  `name_prefix`/`index_start`/`min_slices`/`max_total_pixels` の不正値）。
- 軸交換の受理、palette エントリ数がちょうど `max_materials` の場合の受理。

## 実行結果

```text
uv run pytest -q tests/unit/test_printer_types.py   # 34 passed
uv run pytest -q tests/unit tests/contract           # 389 passed（既存分含む、回帰なし）
uv run ruff check src/vdbmat_utils/printer/ tests/unit/test_printer_types.py
                                                      # All checks passed!
```

## 計画からの逸脱・判断

なし。plan記載のフィールド・検証項目をそのまま実装した。Pillow 非依存
（`image` extra 不要）であることを確認済み（本ステップのテストは
Pillow をimportしない）。

## 次ステップ

Step 2（`sampler.py`）: ピッチ導出・出力形状導出・最近傍index配列の
純関数実装に進む。
