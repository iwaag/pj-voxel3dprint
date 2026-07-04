# Phase 0 実装計画 — リポジトリとコントラクト基盤

対象: `vdbmat-utils` リポジトリ（サブモジュール `vdbmat-utils/`）
参照: [roadmap_vdbmat-utils.md](../roadmap_vdbmat-utils.md) の Phase 0 節

## ゴール

すべてのジェネレータが共有する、小さくテスト可能な基盤を確立する。

**Exit criteria（ロードマップより）:** 合成インメモリボリュームを決定論的に書き出し、
`vdbmat import-voxels` で検証でき、CLI で inspect でき、オプション依存なしで CI が通ること。

## 前提と現状確認

- `vdbmat` は `pj-voxel3dprint` のサブモジュール。パッケージ名 `vdbmat`、`requires-python >= 3.11`、
  `uv` 管理（`uv.lock` あり）。PyPI 未公開。
- `vdbmat` 側で再利用できる公開 API（フォーク禁止、そのまま使う）:
  - 型: `vdbmat.core` — `MaterialLabelVolume`, `GridGeometry`, `MaterialPalette`,
    `MaterialDefinition`, `MaterialRole`, `Provenance`, `SchemaVersion`, `VolumeValidationError` など
  - マニフェスト I/O: `vdbmat.io.voxel_manifest` — `write_material_label_manifest`,
    `read_material_label_manifest`, `inspect_material_label_manifest`
  - CLI: `vdbmat import-voxels`（エンドツーエンド検証に使用）
  - スキーマ文書: `vdbmat/docs/schemas/volume-schema-v1.md`, `optical-mapping-v1.md`
- 現在の `vdbmat-utils/` サブモジュールはほぼ空（LICENSE、スキーマ文書コピー、`examples/`、
  ネストされた `vdbmat` ディレクトリ）。Python パッケージングは未整備。
- **命名の注意:** ロードマップ Decision Log は正準綴りを `vbdmat` としているが、実際のリポジトリ・
  パッケージ名は `vdbmat`。本計画はディスク上の実体 `vdbmat` / `vdbmat-utils` に従う。
  Decision Log 側の記述を実体に合わせて訂正するか、リネームするかを Step 0 で確定する。

## 設計方針（Phase 0 スコープでの解釈）

- 単一ディストリビューション `vdbmat-utils`（`src/vdbmat_utils/`）で開始する。
  ロードマップの「packages/ 分割は必要になってから」に従い、モジュール境界
  （`core` に依存が向く）だけを守る。
- `vdbmat.core` の型が正準。utils 側で競合する Volume 型は定義しない。utils の `core` は
  「vdbmat 型を組み立てる・書き出す・検証するためのヘルパーと規約」を担う。
- 必須依存は `numpy` + `vdbmat` のみ。mesh/image/vdb/preview は extras（Phase 0 では定義だけ、
  中身なし）。

## 実装ステップ

### Step 0 — 命名決定とリポジトリ骨格（0.5日）

1. `vbdmat` vs `vdbmat` の綴り問題を確定し、ロードマップ Decision Log に追記する。
2. `vdbmat-utils/` 直下を整理:
   - 迷い込んでいるネスト `vdbmat/` ディレクトリとスキーマ文書コピーの扱いを決める
     （スキーマは vdbmat 側が single source of truth。utils 内のコピーは削除し参照に置換）。
   - 骨格を作成: `pyproject.toml`, `src/vdbmat_utils/`, `tests/{unit,contract,integration}/`,
     `examples/`, `README.md`, `.gitignore`。

### Step 1 — パッケージング・依存ピン留め・ツールチェーン（1日）

1. `pyproject.toml`: 名前 `vdbmat-utils`、`requires-python >= 3.11`（vdbmat に合わせる）、
   ビルドバックエンドは hatchling、依存は `numpy` と `vdbmat`。
2. **vdbmat 依存メカニズムの決定（ADR として記録）:**
   推奨 — 親リポジトリのサブモジュール構成を活かし、`uv` の path 依存
   （`[tool.uv.sources] vdbmat = { path = "../vdbmat", editable = true }`）＋
   サブモジュールコミットをピンとして扱う。CI ではサブモジュールの記録コミットを checkout。
   代替案（git URL + commit ピン）との比較を ADR に残す。
3. ツールチェーン: `ruff`（lint + format）、`mypy`（strict、`src/` 対象）、`pytest`。
   `uv.lock` をコミット。
4. extras 枠を予約定義: `[project.optional-dependencies]` に `mesh`, `image`, `vdb`, `preview`
   （Phase 0 では空 or 最小）。

### Step 2 — CI（0.5日）

1. GitHub Actions ワークフロー: サブモジュール込み checkout → `uv sync`（extras なし最小構成）
   → `ruff check` → `mypy` → `pytest`。
2. ジョブを2系統: (a) 最小インストール（unit + contract）、(b) 統合（`vdbmat` CLI を呼ぶ
   integration テスト）。Phase 0 では両方同一環境で可、分離だけしておく。

### Step 3 — utils コアモジュール（2日）

`src/vdbmat_utils/core/` に以下を実装。いずれも `vdbmat.core` 型を返す薄い層:

1. `builder.py` — `VolumeBuilder`: shape (z,y,x)・voxel size・rigid transform・palette・
   provenance を受け取り、検証済み `MaterialLabelVolume` を構築するヘルパー。
   dtype は `uint16` 固定、軸順 `z,y,x` を型とdocstringで明示。
2. `provenance.py` — ジェネレータ名・バージョン・設定ダイジェスト・seed・ソース識別子から
   `Provenance` を組み立てる規約関数。設定ダイジェストは正規化JSON の SHA-256。
3. `config.py` — ジェネレータ設定の直列化規約: dataclass ベース、`to_json()/from_json()`、
   キー順序固定・浮動小数の正規化ルールを文書化（決定論の基礎）。
4. `seeds.py` — seed ハンドリング: 単一の整数 seed から `numpy.random.Generator` を派生させる
   規約（`np.random.default_rng(seed)`、サブストリームは `spawn`）。
5. `errors.py` — utils の例外階層: `VdbmatUtilsError` を基底に `ConfigError`, `GeometryError`,
   `PaletteError`。vdbmat の `VolumeValidationError` はラップせず透過。
6. `compat.py` — サポートする vdbmat コントラクトバージョン範囲
   （`SUPPORTED_VOLUME_SCHEMA = ">=1,<2"` 相当）を定数化し、実行時に
   `vdbmat.core.VOLUME_SCHEMA` と照合、範囲外なら明確に失敗。

### Step 4 — マニフェスト出力と決定論ルール（1日）

1. `src/vdbmat_utils/io/writer.py` — `write_asset(volume, out_dir, name)`:
   `vdbmat.io.voxel_manifest.write_material_label_manifest` に委譲し、
   `<name>.voxels.json` + `<name>.material_id.npy` を出力。
2. **決定論ルールを文書化**（`docs/determinism.md`）: 同一入力・設定・seed →
   NPY ペイロードはバイト等価、マニフェストはタイムスタンプ等の可変フィールドを除き等価。
   チェックサム（マニフェスト記載の digest）で回帰検出。
3. テスト: 同一入力で2回書き出してバイト比較。

### Step 5 — ゴールデンフィクスチャとコントラクトテスト（1.5日）

`tests/contract/` + `tests/fixtures/`:

1. フィクスチャ生成スクリプト（seed 固定・チェックサム記録）で以下をカバー:
   - 異方性 voxel size（例 0.1×0.2×0.4 mm）
   - 非ゼロ origin を持つ rigid transform
   - 回転を含む transform
   - 3 種以上のマテリアルを含む palette（vdbmat 組み込みテーブル外の名前を1つ含め、
     optical-mapping が必要になるケースを用意）
   - 非対称な軸方向パターン（z/y/x の取り違え検出用）
2. 不正メタデータのネガティブテスト: 軸順不一致、dtype 違反、palette 参照切れ、
   単位欠落 — それぞれ `VolumeValidationError`（または utils 例外）で失敗することを確認。
3. コントラクトテスト: 各ゴールデンフィクスチャを `read_material_label_manifest` /
   `inspect_material_label_manifest` で読み戻しラウンドトリップ検証。
4. 統合テスト: フィクスチャを `vdbmat import-voxels` CLI（subprocess）に通し成功を確認。

### Step 6 — 最小 CLI（1日）

`src/vdbmat_utils/cli/`、エントリポイント `vdbmat-utils`:

1. `vdbmat-utils inspect <manifest>` — `inspect_material_label_manifest` の結果
   （shape、voxel size、transform、palette、provenance、checksums）を人間可読 + `--json` で表示。
2. `vdbmat-utils validate <manifest>` — 読み戻し検証 + compat 範囲チェック。終了コード規約
   （0=OK, 1=検証失敗, 2=使用法エラー）を `cli/errors.py` に定義。
3. `vdbmat-utils generate-fixture <preset> -o <dir>` — Step 5 の合成ボリュームを CLI から
   再生成できるデモコマンド（seed/preset 指定）。Exit criteria の実演に使う。

### Step 7 — ドキュメントと締め（1日）

1. `README.md`: インストール（サブモジュール + uv）、CLI 使用例、決定論・seed・設定規約への
   リンク。
2. `docs/adr/`: 依存ピン方式（Step 1）、命名決定（Step 0）、コントラクト互換範囲（Step 3-6）を
   ADR 化。
3. Exit criteria チェックの実行ログを残す:
   `generate-fixture → vdbmat import-voxels → vdbmat-utils inspect` が CI 上で通ること。
4. ロードマップの Phase 0 節に完了状態と差分（あれば）を追記。

## ステップ依存関係

```text
Step 0 → Step 1 → Step 2
              └→ Step 3 → Step 4 → Step 5 → Step 6 → Step 7
```

Step 2（CI）は Step 3 以降と並行可。目安合計: 約 8.5 人日。

## Phase 0 でやらないこと

- mesh / image / procedural / OpenVDB / service / ML（Phase 1 以降）
- optical-mapping ドキュメントの**生成ロジック**（Phase 3 で必須化。Phase 0 では
  「組み込み外マテリアル名を含むフィクスチャ」で必要性をテストに刻むところまで）
- `packages/` へのワークスペース分割（第2の独立配布物が必要になるまで単一パッケージ）
- スパース表現・チャンク処理・性能最適化

## リスクと対応

- **綴り不一致（vbdmat/vdbmat）:** Step 0 で決着させないと全成果物に波及。最初に処理。
- **vdbmat API の非公開部分への依存:** `vdbmat.core` と `vdbmat.io.voxel_manifest` の
  公開シンボルのみ import する。プライベート関数（`_` 接頭辞）使用は lint で禁止。
- **コントラクトドリフト:** サブモジュールコミット更新時に contract テストが必ず走るよう、
  CI はピンされたサブモジュールで実行し、更新は意図的な PR でのみ行う。
