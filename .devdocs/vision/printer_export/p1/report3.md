# Step 3 報告 — PNG writer と exporter（`png.py` / `exporter.py`）

## 実施内容

### `image/png.py`

- `write_indexed_png()` を追加した。mode "P" のインデックスパレット PNG を
  書く。パレットテーブルは呼び出し側が渡す `palette_rgb`（index 0 =
  background、以降 material_id 昇順）をそのまま使い、256エントリ未満は
  黒でパディングする。アンチエイリアス・リサイズ・ICC変換は一切通さない。
  圧縮パラメータ（`compress_level=6`、`optimize=False`）を固定し、
  同一入力の複数回書き出しがbyte-equalであることをテストで確認した。
  256エントリ超のパレットは明示エラー。
- `read_indexed_png()` をテスト/デコード検証用ヘルパとして追加した
  （mode "P" 以外は明示エラー、常に256エントリのパレットを返す）。
- 両関数とも既存 `read_png()` と同型の lazy import + `image` extra 未導入
  時の actionable エラーに揃えた。

### `printer/exporter.py`

- `export_print_slices(manifest_path, config, out_dir, name)` を実装。
  1. 出力先 `<out>/<name>/` が既に存在する場合は最初に明示エラー。
  2. `read_material_label_manifest()` で入力を読込（payload sha256照合含む
     既存経路）。
  3. 入力の非背景 material_id 集合と config `palette` のキー集合が完全
     一致することを検証（片方向ずつ別エラーメッセージ）。
  4. `build_sampling_plan()` で出力格子を導出（`max_materials`超過や
     ガード違反は既に Step 1/2 の契約で拒否済み）。
  5. material_id → palette index の lookup テーブルを構築し、z方向に
     ストリーミングしながら `sample_slice()` → PNG書き出し →
     デコード再検証（実使用色が宣言集合の部分集合か）→ sha256蓄積 →
     材料別ピクセル数集計、を1スライスずつ行う（全出力を同時に保持しない）。
  6. サイドカーマニフェスト `<name>.printslices.json` を書く
     （`format`/`source`(manifest sha256 + payload sha256)/`config_digest`/
     `printer`(dpi・レイヤー厚・ピッチmm)/`grid`(スライス数・ピクセル数・
     物理寸法mm)/`palette`(材料名・role・rgb転記)/`background_rgb`/
     `slices`(name_prefix・index_start・桁数・各PNGのsha256)）。
  7. 一時ディレクトリ `<out>/.<name>.tmp-<uuid>` で組み立て、
     成功後に `Path.rename()` で atomic に発行。途中で例外が出た場合は
     tmp を削除し `<out>` に何も残さない。
- 連番の桁数は `max(4, len(str(index_start + n_slices - 1)))` で導出
  （最低4桁）。

## テスト

- `tests/unit/test_printer_png.py`（6ケース）: round-trip、パディング、
  256超パレット拒否、double-run byte equality、`image` extra 未導入時の
  エラー、非インデックスPNG読込拒否。
- `tests/unit/test_printer_exporter.py`（8ケース、`generate-primitive-array`
  の小さい立方体1個フィクスチャを入力に使用）: 出力レイアウト、桁数既定値
  （4桁）、既存出力先の拒否、palette欠落での非発行確認（`<out>`が汚れない）、
  palette過多エントリの拒否、マニフェストの物理寸法を手計算値と照合、
  double-run byte equality、材料別ピクセル数の合計が総ピクセル数と一致。

## 実行結果

```text
uv run pytest -q tests/unit/test_printer_png.py tests/unit/test_printer_exporter.py
                                                      # 14 passed
uv run pytest -q tests/unit tests/contract           # 418 passed（回帰なし）
uv run ruff check src/vdbmat_utils/printer/ src/vdbmat_utils/image/png.py \
  tests/unit/test_printer_*.py                       # All checks passed!
```

## 計画からの逸脱・判断

- Step 2 report に記載の通り、パレットindex変換（material_id →
  palette index の lookup 構築）は `exporter.py` 側に実装した
  （`sampler.py` は material_id 配列を返すところまで）。
- atomic発行は plan記載の「`<out>/.<name>.tmp-*`」規則に従うが、識別子は
  `vdbmat` pipeline runner の `run_id` のような科学的な値ではなく
  `uuid4` を使った（本ステップの一時ディレクトリ名は最終成果物に一切
  現れないため、一意性だけで十分と判断）。
- 出力先の既存チェックは関数冒頭1箇所のみとした（重複チェックを発行直前にも
  入れる案は、単一プロセス・ローカルCLIというこのツールの前提に対して
  過剰と判断し見送った）。

## 次ステップ

Step 4（CLI接続）: `export-print-slices` サブコマンドと
`_cmd_export_print_slices()` を `cli/main.py` に追加する。
