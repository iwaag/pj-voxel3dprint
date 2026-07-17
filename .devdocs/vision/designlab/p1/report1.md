# Step 1 報告 — config 契約

## 実施内容

`vdbmat-utils/src/vdbmat_utils/primitives/` を新設し、`PrimitiveArrayConfig`
（`types.py`）を frozen dataclass として実装した。

- フィールドは plan の決定事項どおり: `voxel_size_xyz_m`、`primitive`、
  `counts_xyz`、`primitive_size_m`、`gap_m`（必須・既定値なし）、
  `margin_m`（必須・既定値なし）、`base_material_name`（既定
  `transparent-resin`）、`inclusion_material_name`（既定
  `black-opaque-resin`）、`max_axis_cells`（既定256）、
  `max_total_cells`（既定8,000,000）、`seed`（基底クラス継承）。
- `__post_init__` で全 validation を行う: 各数値の正値/非負値、
  `counts_xyz` の各成分が整数かつ `>= 1`、`primitive` が
  `"cube"`/`"sphere"`、材料名が built-in（`air` を除く）に限定、
  base/inclusion の相異、ガード値の正当性。
- `BUILTIN_MATERIAL_IDS` を primitives モジュール内の1定数として定義
  （`transparent-resin`=1、`white-resin`=2、`black-opaque-resin`=3）。
  `vdbmat.optics.config.phase0_provisional_mapping()` の built-in id と
  一致することを確認済み（plan の risk 節どおり、乖離時は本定数側を
  同一フェーズで更新する方針）。
- JSON 由来の list を tuple に正規化し（`object.__setattr__`）、
  `to_json()` → `from_json()` の round-trip で dataclass 等価性が
  成立するようにした。
- 未知フィールド拒否・canonical JSON・digest 安定性は基底クラス
  `GeneratorConfig` の既存機構にそのまま乗る（新規コードなし）。
- 独自例外 `PrimitiveArrayError`（`primitives/__init__.py`）を
  `mesh/__init__.py` の既存パターンと同型で追加した。

## テスト

`tests/unit/test_primitives.py` に config 契約のテストを追加した
（受理境界値、拒否境界値16パターン、round-trip、digest 安定性、
seed 変更で digest が変わることの確認）。実行結果は Step 2 と合わせて
下記のとおり。

## 静的検査・テスト結果

```
uv run ruff check src/vdbmat_utils/primitives tests/unit/test_primitives.py
→ All checks passed!

uv run pytest -q tests/unit
→ 273 passed, 2 skipped (既存の PIL 未導入によるスキップ、無関係)
```

## メモ

Step 2（生成本体）の実装・テストと合わせて1回のコミットにまとめた
（`generator.py` は `types.py` の `PrimitiveArrayConfig` を直接消費し、
config 契約単体では実行可能な生成パスがなく、分離コミットの実益が
薄いと判断したため）。詳細は `report2.md` を参照。
