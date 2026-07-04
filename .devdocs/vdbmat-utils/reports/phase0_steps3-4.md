# Phase 0 実行レポート — Steps 3–4

日付: 2026-07-05
対象計画: [plan.md](../plans/phase0/plan.md)
実行範囲: Step 3（utils コアモジュール）、Step 4（マニフェスト出力と決定論ルール）。
両ステップは密結合のため計画の許可に基づき連続実行した。

## 結果サマリ

両ステップ完了。`vdbmat_utils.core`（6モジュール）と `vdbmat_utils.io.writer`、
決定論ドキュメント、単体テスト16件＋コントラクトテスト3件を追加。
ローカルで `ruff` / `mypy --strict`（src + tests 16ファイル）/ `pytest` 20件すべてグリーン。
**コミット未実施**（前回同様、手動 push を想定）。

## Step 3 — utils コアモジュール（`src/vdbmat_utils/core/`）

計画どおり `vdbmat.core` の型を正準とし、utils 側は構築ヘルパーと規約のみを提供:

- `errors.py` — `VdbmatUtilsError` 基底に `ConfigError` / `GeometryError` / `PaletteError`、
  および計画外だが必要になった `CompatibilityError` を追加。vdbmat の
  `VolumeValidationError` はラップせず透過（テストで確認）。
- `compat.py` — `SUPPORTED_VOLUME_SCHEMA_MAJOR = 1`。`require_compatible_volume_schema()` が
  ピンされた `vdbmat.core.VOLUME_SCHEMA`（現在 1.0.0）と照合し、名前不一致・メジャー版
  範囲外なら `CompatibilityError`。builder が毎回呼ぶため、将来の非互換 bump は即検出される。
- `config.py` — `GeneratorConfig` 基底 dataclass（seed を必須フィールドとして含む）。
  正規化 JSON（キーソート・コンパクト区切り・非有限 float 拒否・UTF-8）と
  `config_digest()`（`sha256:<hex>`、vdbmat の `configuration_digest` 形式に一致）。
  `from_json` は未知フィールドを拒否。
- `seeds.py` — `rng_from_seed()`（非負 int → `np.random.default_rng`）と
  `spawn_rngs()`。spawn 方式により「消費者を増やしても既存ストリームがズレない」ことを
  テストで保証。
- `provenance.py` — `build_provenance()`。digest は常に config から導出、`created_utc` は
  決定論のため意図的に未設定。
- `builder.py` — `build_material_label_volume()`。3次元 uint16 / voxel size 3成分 / 4x4 行列を
  事前検証し、値レベルの検証（palette 参照整合・剛体性）は `vdbmat.core` に委譲。

## Step 4 — マニフェスト出力と決定論

- `io/writer.py` — `write_asset()`: `vdbmat.io.write_material_label_manifest` への薄い委譲。
  vdbmat のマニフェストにはタイムスタンプ等の可変フィールドが存在しないことをソースで確認
  したため、決定論ルールは計画より強く「**マニフェストもペイロードもバイト等価**」とした。
- `docs/determinism.md` — seed 規約・設定正規化・出力への時刻/環境情報禁止・チェックサムに
  よる回帰検出・バイト等価の適用範囲（同一プラットフォーム＋ピン済み依存、クロス
  プラットフォームは対象外）を文書化。
- `tests/contract/test_determinism.py` — 合成ジェネレータ（seed 付きランダムラベル）で
  2回書き出しバイト比較、seed 差分でペイロードが変わること、
  `read_material_label_manifest` によるラウンドトリップの3件。

## 検証ログ

```text
$ uv run ruff check .
All checks passed!
$ uv run mypy src tests
Success: no issues found in 16 source files
$ uv run pytest -q
20 passed
```

## 計画からの差分・メモ

- `CompatibilityError` を計画の例外一覧に追加（compat チェックの失敗は Config/Geometry の
  どれにも属さないため）。
- `builder.py` が `vdbmat.core.transforms.Matrix4` 型を直接 import している。
  アンダースコア無しの公開モジュールだが `vdbmat.core.__init__` には再エクスポートされて
  いない。上流に `Matrix4` の再エクスポートを提案するとよい（`py.typed` と合わせて
  フォローアップ候補）。
- コントラクトテストの合成ジェネレータは Step 5 のフィクスチャ生成、Step 6 の
  `generate-fixture` コマンドの土台として再利用予定。

## 次のステップ

Step 5（ゴールデンフィクスチャとコントラクトテスト: 異方性 voxel・非ゼロ origin・回転・
複数マテリアル・不正メタデータ、`vdbmat import-voxels` 統合テスト）。
