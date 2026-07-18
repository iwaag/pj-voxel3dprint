# Step 4 報告 — CLI接続

## 実施内容

- `vdbmat-utils/src/vdbmat_utils/cli/main.py`:
  - `export-print-slices` サブコマンドを追加（位置引数 `MANIFEST`、
    `--config`/`--out`/`--name` — 既存 `convert-image-stack` と同型）。
  - `_cmd_export_print_slices()` を追加。`PrintSlicesConfig.from_json()` →
    `export_print_slices()` → 成功サマリ（発行パス、スライス数、
    ピクセル数、物理寸法mm、材料別ピクセル数）を出力する。
  - CLIフィールド上書きオプションは設けていない（plan通り、config
    ファイルが唯一の入力）。
  - `PrintSlicesError`/`ImageStackError` はいずれも既存の
    `VdbmatUtilsError` 系なので、既存の `_EXPECTED_ERRORS` catch節に
    そのまま乗り、exit code 1 で処理される（追加のtry/except不要）。
- `vdbmat-utils/README.md`: Status文言とコマンド一覧に
  `export-print-slices`（`docs/print-slices.md` 参照、Step 6で追加予定）
  を1行追加し、他の generator と同水準の使用例セクションを追記した。

## テスト

`vdbmat-utils/tests/unit/test_cli.py` に3ケース追加:

- 正常系: `generate-primitive-array` → `export-print-slices` で
  `demo.printslices.json` が発行されることと標準出力のサマリ文言を確認。
- config エラー系: palette の material_id を入力に存在しない値に
  すり替え、exit code 1 と stderr の `palette` 文言を確認。
- 入力欠落系: 存在しないmanifestパスを渡し、exit code 1 を確認。

## 実行結果

```text
uv run pytest -q tests/unit/test_cli.py                # 21 passed（既存18 + 新規3）
uv run pytest -q tests/unit tests/contract             # 421 passed（回帰なし）
uv run ruff check src/vdbmat_utils tests/unit/test_cli.py
                                                          # All checks passed!
```

手動 walkthrough（CLI経由、`.local` 配下に成果物、git管理なし）:

```bash
uv run vdbmat-utils generate-primitive-array --config primarray.json \
  --out input/ --name demo   # counts_xyz=[3,2,1]
uv run vdbmat-utils export-print-slices input/demo.voxels.json \
  --config printslices.json --out out/ --name demo
```

- サマリ出力: `slices: 23  pixels: 43x15`、
  `physical size (mm): x=1.8203 y=1.2700 z=0.6210`。
- `slice_0010.png`（立方体本体の中央スライス）を画像として目視し、
  緑の立方体3個が横一列に並んでいることを確認した
  （`counts_xyz=(3,2,1)` の3個と一致）。600/300dpiの異方性により
  X方向がY方向よりも密なピッチになるため、正方形の立方体が横に
  間延びして見える（ピクセル比 X:Y = 2:1 のとおり）。
  この目視確認は Step 6 の walkthrough の前倒し的な動作確認であり、
  Step 6 では正式な report として記録・再実施する。

## 計画からの逸脱・判断

なし。

## 次ステップ

Step 5（契約テスト）: `tests/contract/test_print_slices_contract.py` に
digest pin・double-run・デコード検証・パラメータ感度・seed非依存・
色数制約テストを追加する。
