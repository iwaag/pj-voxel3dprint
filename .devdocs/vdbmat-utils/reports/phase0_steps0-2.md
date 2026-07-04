# Phase 0 実行レポート — Steps 0–2

日付: 2026-07-05
対象計画: [plan.md](../plans/phase0/plan.md)
実行範囲: Step 0（命名決定と骨格）、Step 1（パッケージング・依存ピン・ツールチェーン）、
Step 2（CI）。Step 0–1 は切りが悪いため計画の許可に基づき Step 2 まで続行した。

## 結果サマリ

3ステップとも完了。`vdbmat-utils` サブモジュールに動作するパッケージ骨格が入り、
ローカルで `ruff` / `mypy --strict` / `pytest`（unit + integration）がすべてグリーン。
CI ワークフローは superproject に追加済みだが、push していないため GitHub 上では未検証。
**コミットはまだ行っていない**（指示があれば実施）。

## Step 0 — 命名決定とリポジトリ骨格

- **命名決定:** 正準綴りは `vdbmat` / `vdbmat-utils`。ロードマップ Decision Log の旧エントリ
  （`vbdmat` を正準とする記述）はそれ自体がタイポであり、GitHub リポジトリ名・Python パッケージ名・
  サブモジュールパスのすべてが `vdbmat` であることから、実体に合わせて確定。
  - ロードマップの Decision Log に訂正エントリを追記（旧エントリは superseded として保持）。
  - ADR 化: `vdbmat-utils/docs/adr/0002-canonical-naming.md`
- **骨格整理:** 計画時点で懸念していた「迷い込んだネスト `vdbmat/` ディレクトリとスキーマ文書コピー」は
  実行時には存在せず（サブモジュールは LICENSE のみの初期コミット状態）、整理作業は不要だった。
- 作成した骨格: `src/vdbmat_utils/`（`py.typed` 付き）、`tests/{unit,contract,integration}/`、
  `docs/adr/`、`examples/`、`README.md`、`.gitignore`。

## Step 1 — パッケージング・依存ピン・ツールチェーン

- `pyproject.toml`: 名前 `vdbmat-utils` 0.1.0、`requires-python >= 3.11`、ライセンス CC0-1.0、
  ビルドバックエンドは vdbmat と同じ `uv_build`。必須依存は `numpy>=1.26` と `vdbmat` のみ。
- **依存ピン方式（ADR 0001 として記録・採択）:** uv の path 依存
  `vdbmat = { path = "../vdbmat", editable = true }` ＋ superproject のサブモジュールコミットを
  実効ピンとする方式。git URL + commit ピン案はピンの二重管理によるドリフトリスクで不採択。
  詳細: `vdbmat-utils/docs/adr/0001-vdbmat-dependency-pinning.md`
- ツールチェーン: `ruff`（vdbmat と同じルールセット B/E/F/I/RUF/SIM/UP、88桁）、
  `mypy --strict`（vdbmat が `py.typed` 未同梱のため `follow_untyped_imports` override で
  ソースを直接解析。上流に `py.typed` を追加するのが本筋 — フォローアップ候補）、`pytest`。
  `uv.lock` 生成済み。
- extras 枠を予約: `mesh` / `image` / `vdb` / `preview`（Phase 0 では空）。
- CLI スタブ: `vdbmat-utils --version` のみ動作（本体は Step 6）。

## Step 2 — CI

- `pj-voxel3dprint/.github/workflows/ci.yml` を新規作成（ピンが superproject のサブモジュール
  gitlink にあるため、ワークフローは utils リポジトリではなく superproject 側に配置）。
- ジョブ2系統: 最小インストール（lint + typecheck + `pytest -m "not integration"`）と
  統合（`pytest -m integration`）。`integration` マーカーを pytest 設定に登録。
- 統合ジョブが空にならないよう、ピンされた `vdbmat` CLI（`--help` に `import-voxels` が
  含まれること）を確認するスモークテストを追加。

## 検証ログ

`vdbmat-utils/` にて:

```text
$ uv sync           # numpy 2.4.6, vdbmat 0.1.0 (path), dev tools 導入
$ uv run ruff check .
All checks passed!
$ uv run mypy src tests
Success: no issues found in 5 source files
$ uv run pytest -q
4 passed
$ uv run pytest -m "not integration" -q   # CI 最小ジョブ相当
3 passed
$ uv run pytest -m integration -q         # CI 統合ジョブ相当
1 passed, 3 deselected
$ uv run vdbmat-utils --version
vdbmat-utils 0.1.0
```

## 未完了・フォローアップ

- **コミット未実施:** 変更は `vdbmat-utils` サブモジュール（新規ファイル一式）、
  superproject（ci.yml、ロードマップ訂正、本レポート）の作業ツリーにある。
  サブモジュール → superproject の順でコミットが必要。
- **CI は GitHub 上で未検証:** push 後に初回実行の確認が必要。
- **vdbmat への `py.typed` 追加**を上流フォローアップとして提案（mypy override を撤去できる）。
- 次のステップ: Step 3（utils コアモジュール: builder / provenance / config / seeds /
  errors / compat）。
