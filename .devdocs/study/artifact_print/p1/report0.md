# artifact_print p1 step 0 report — 置き場と雛形

## Done

- `study/3dprint_artifact/`(git 管理)に plan の成果物対応表どおりの md を作成した:
  `README.md`, `sources.md`, `license_notes.md`, `candidates.md`,
  `pipeline_feasibility.md`, `methods_tools.md`, `print_constraints.md`,
  `open_questions.md`。README 以外は見出しだけの雛形。
- `README.md` に plan へのリンク、問い Q1〜Q5 と成果物の対応、運用ルール
  (一次資料は `.local` のみ、md には URL・ライセンス名・要約・sha256 のみ、
  ライセンス 4 欄必須、未確認は明記)を書いた。
- `.local/study/3dprint_artifact/{models,docs,shots}/` と取得ログ用の
  `README.md`(非管理、表の見出しのみ)を作成した。`git check-ignore` で
  `.local/` が無視されることを確認。
- 同じコミットで、未追跡だった `.devdocs/study/artifact_print/p1/`
  (braindump.md, advice.md, plan.md)も追加した。

## Commands

```bash
mkdir -p .local/study/3dprint_artifact/{models,docs,shots}
git check-ignore -v .local/x          # -> .gitignore:1:.local/
cd vdbmat-utils && uv run python -c "import trimesh; print(trimesh.__version__)"   # 4.12.2
curl -sI https://api.sketchfab.com/v3/models   # ネットワーク到達確認
```

## Learned

- `vdbmat-utils` の venv に trimesh 4.12.2 が既に入っている(`mesh` extra は空だが
  依存経由で解決済み)。Step 2 のメッシュ判定はこの venv で始められる。
- ホストは 32 コア / 123 GB RAM。ただし調査時点で約 96 GB が使用中で、
  Step 6 の dense 実験は 128 cells/axis 級に留めるのが無難。
- 外部 API(Sketchfab, Smithsonian)へは到達できる。

## Skipped

- なし。
