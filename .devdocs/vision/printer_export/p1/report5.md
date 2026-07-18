# Step 5 報告 — 契約テスト（`test_print_slices_contract.py`）

## 実施内容

`vdbmat-utils/tests/contract/test_print_slices_contract.py` を新規作成
（10ケース）。既存 fixture（`generate-fixture` の `anisotropic`
（1非背景材料）/ `multimaterial`（3非背景材料）プリセット）を代表入力2種、
HQ 14µm / HS 27µm + `max_materials=3` プロファイルを代表configとした。

- **digest pin**: デコード済みピクセル配列（palette index 配列を
  スライス順に連結した sha256）を固定。plan記載のリスク（PNG byte表現が
  Pillowバージョンに依存しうる）に従い、ファイルbyte equalityではなく
  デコード後の配列に対して digest pin した。
- **double-run byte equality**: 同一環境での2回実行（PNGファイル・
  マニフェスト双方）がbyte-identicalであることを確認。
- **デコード検証（往復可能性の先行担保）**: 全スライスを
  `read_indexed_png()` で読み戻し、config から導出した
  palette index → material_id 逆引きテーブルで material_id 配列へ復元し、
  `sampler.build_sampling_plan()`/`sample_slice()` が返す配列と
  完全一致することを確認した。
- **パラメータ感度**: `dpi_x`/`layer_thickness_m`/`flip_z`/palette RGB の
  変更でそれぞれ出力が変わることを確認。
- **seed非依存**: `seed` 変更で config digest は変わるがピクセル digest は
  不変であることを確認。
- **色数制約**: 7材料（0..7の8材料、うち非背景7）の入力に対し、
  `max_materials=6`（既定）の palette 構築自体が発行前に明示エラーになる
  ことを確認し、`out` ディレクトリが作られていないことも確認した。

## 実装中に判明した事実（テスト設計上の調整）

- `flip_z` の感度テストは、当初 `anisotropic` fixture（材料ラベル式が
  z について周期2）で書いたが、導出スライス数がその周期に対して対称
  （z=0とz=2のスラブが偶然ピクセル同一）になり、反転が実質no-opになって
  失敗した。`multimaterial` fixture（周期4、非対称スライス数）に切り替えて
  解消した。これは実装のバグではなくテストフィクスチャの選び方の問題。
- `palette` RGB の感度テストは、当初「デコード後のピクセル digest」で
  差分を見ようとしたが、pixel値は palette **index**（材料同一性）であり
  RGBは別テーブル（パレット）にあるため、index配列はRGB変更で変化しない
  （設計上正しい——中間色が生じない保証と表裏）。plan の記載
  「ピクセル digest（**または** palette テーブル）が変わる」を踏まえ、
  index digestが不変であることを確認した上で、`read_indexed_png()` が
  返すパレットテーブルの該当エントリが変わることを確認する形に直した。

## 実行結果

```text
uv run pytest -q tests/contract/test_print_slices_contract.py   # 10 passed
uv run pytest -q tests/unit tests/contract                       # 431 passed（回帰なし）
uv run ruff check tests/contract/test_print_slices_contract.py   # All checks passed!
```

## 計画からの逸脱・判断

上記「実装中に判明した事実」の2点はテスト設計の調整であり、実装
（`sampler.py`/`exporter.py`/`png.py`）への変更は伴わない。契約テストが
検証する性質（感度・往復可能性・色数制約）はplan通りすべて満たしている。

## 次ステップ

Step 6（docs・手動確認）: `docs/print-slices.md` を作成し、
`generate-primitive-array` → `export-print-slices` → 目視 + 寸法照合の
walkthrough を実施して report6 に記録する。
