# Step 2 報告 — サンプリング純関数（`printer/sampler.py`）

## 実施内容

`vdbmat-utils/src/vdbmat_utils/printer/sampler.py` を新規作成した。PNG・
ファイルIOに一切依存しない純関数のみで構成する（`numpy` のみ依存）。

- `derive_output_grid()`: 物理ピッチ（`pitch_x = 0.0254/dpi_x`、
  `pitch_y = 0.0254/dpi_y`、`pitch_z = layer_thickness_m`）を導出し、
  `ceil(extent/pitch - 1e-6)` で出力セル数（`width`/`height`/`n_slices`）を
  導出する。`min_slices` 未満、`max_total_pixels` 超過をこの時点で明示
  エラーにする（後者は入力を粗くする/縮小する旨の提案付き）。
- `build_sampling_plan()`: 軸対応（`printer_x_axis`/`printer_y_axis`）に
  従いソース x/y 軸それぞれの最近傍 index 配列を1次元ずつ事前計算し、
  `flip_x`/`flip_y`/`flip_z` を index 配列の反転として適用する
  （ピクセル中心の物理座標規則そのものは不変、反転は事後適用）。
- `sample_slice()`: 1スライス分の material_id 2次元配列
  （`shape (height, width)`）を `np.take` の2段適用で返す。
  `printer_x_axis == "y"`（軸交換）の場合は、y 軸を先に width 方向で
  `take` し、x 軸を height 方向で `take` してから転置することで、
  「転置」を素直に表現した。
- パレット変換（material_id → パレットindex）はこのモジュールに含めない
  （plan通り、sampler は material_id 配列を返すところまでが責務。
  Phase 2 の往復契約が参照する共通点は「この material_id 配列」になる）。

## テスト

`vdbmat-utils/tests/unit/test_printer_sampler.py` を新規作成（15ケース、
うち軸交換×flip_x×flip_yの全8通りをparametrize）:

- 整数比ケース（`voxel_size_y == pitch_y` ちょうど）の厳密 shape。
- 非整数比（等方100µmソース → 600/300dpi + 27µmプロファイル）で
  手計算値と一致することを確認。
- `min_slices` 未達、`max_total_pixels` 超過それぞれの明示エラー
  （後者はメッセージに `max_total_pixels` を含み提案文言を確認）。
- 境界 tie（中心がソースセル境界に厳密一致）で `floor` 規則が一貫する
  ことを直接計算したケースで確認。
- `ceil` によるはみ出しを `clip` が防ぐケース。
- 軸交換（`printer_x_axis`/`printer_y_axis` の入替）と
  `flip_x`/`flip_y` の全組み合わせ（3×2×1 相当の非対称最小入力、
  identity ピッチ）で、手計算した期待配列と全数一致することを確認。

## 実行結果

```text
uv run pytest -q tests/unit/test_printer_sampler.py   # 15 passed
uv run pytest -q tests/unit tests/contract              # 404 passed（回帰なし）
uv run ruff check src/vdbmat_utils/printer/ tests/unit/test_printer_sampler.py
                                                          # All checks passed!
```

## 計画からの逸脱・判断

- plan は「z スライス1枚分の palette-index 配列を返す関数」を
  `sampler.py` に置くと書いていたが、実装では material_id 配列を返す
  ところまでを `sampler.py` の責務とし、パレットindexへの変換は
  Step 3 の `exporter.py`（PNG書き出しの直前）に置く判断をした。
  理由: sampler.py 冒頭のコメントに書いた通り「Phase 2 往復契約の
  共通参照点」は material_id 配列であるべきで、パレット変換を混ぜると
  純粋な物理サンプリングとパレット規約（Phase 4で拡張されうる）が
  1関数に同居してしまう。パレット変換自体は数行の単純なlookupであり、
  分離してもテスト容易性・PNG非依存性は変わらない。plan の非ゴール・
  完了条件のいずれとも矛盾しないと判断し、そのまま進めた（設計判断で
  あり人間確認が必要な逸脱ではないと判断）。

## 次ステップ

Step 3（`png.py` の `write_indexed_png()` と `exporter.py`）: パレット
index 変換、PNG書き出し、atomic発行、マニフェスト生成に進む。
