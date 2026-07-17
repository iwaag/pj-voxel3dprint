# Step 3 報告 — CLI 接続

## 実施内容

`vdbmat_utils/cli/main.py` に `generate-primitive-array` サブコマンドを
追加した。

- 引数: `--config CONFIG --out DIR --name NAME`
  （plan どおり、CLI フィールド上書きは設けていない）。
- `_cmd_generate_primitive_array()`: config を読み込み →
  `generate_primitive_array()` → `write_asset()` で出力し、manifest パスと
  材料別 voxel 数サマリを表示する（既存コマンドと同じ体裁）。
- `PrimitiveArrayError` は既存の `_EXPECTED_ERRORS`
  （`VdbmatUtilsError` 経由）でそのまま拾われ、exit code 1・
  `error: <field>: <message>` の1行エラーになる。

## テスト

`tests/unit/test_cli.py` に正常系・config エラー系を追加した。

- `test_generate_primitive_array`: 生成 → 出力に材料名が含まれる →
  `validate` が通ることを確認。
- `test_generate_primitive_array_bad_config_returns_1`: 不正な
  `primitive` 値で exit code 1、stderr に該当フィールド名が含まれること
  を確認。

## 手動スモークテスト

```
uv run vdbmat-utils generate-primitive-array --config /tmp/pa.json \
  --out /tmp/pa_out --name demo
uv run vdbmat-utils preview-slices /tmp/pa_out/demo.voxels.json --axis z
```

sphere 2x2x1 config で ASCII preview を目視し、2x2個の球断面が並んで
見えることを確認した（`.local` 外の `/tmp` で行った使い捨て確認であり、
git 管理下には残していない）。

## 静的検査・テスト結果

```
uv run ruff check src/vdbmat_utils/cli/main.py tests/unit/test_cli.py
→ All checks passed!

uv run pytest -q tests/unit
→ 275 passed, 2 skipped (PIL 未導入によるスキップ、無関係)
```

## 想定外事項

なし。
