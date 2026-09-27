# 3dprint_artifact — 骨董品・美術品 3D スキャンのカラー voxel print 事前調査

> 状態: 雛形(Step 0)。Step 7 で「推奨データ + 推奨パイプライン + リスク + 次フェーズ提案」に置き換える。

計画: [.devdocs/study/artifact_print/p1/plan.md](../../.devdocs/study/artifact_print/p1/plan.md)
(要望: `braindump.md`、当たり: `advice.md`、ステップ報告: `report0..7.md`)

## 問いと成果物

| # | 問い | 成果物 |
|---|---|---|
| Q1 | データはどこで入手できるか | [sources.md](sources.md), [license_notes.md](license_notes.md) |
| Q2 | 最初の MVP に向くデータはどれか | [candidates.md](candidates.md) |
| Q3 | 現時点で 3D プリント可能な形にできるか | [pipeline_feasibility.md](pipeline_feasibility.md) |
| Q4 | 使えそうな手法・計算・ツール | [methods_tools.md](methods_tools.md) |
| Q5 | プリンタ制約・材料・法的条件・コスト | [print_constraints.md](print_constraints.md), [license_notes.md](license_notes.md), [open_questions.md](open_questions.md) |

## 運用ルール

- 一次資料(ダウンロードしたモデル、テクスチャ、PDF、スクリーンショット)は
  `.local/study/3dprint_artifact/{models,docs,shots}/` にのみ置く(`.local/` は `.gitignore` 済み)。
  何をどこから落としたかは `.local/study/3dprint_artifact/README.md`(非管理)に記録する。
- このフォルダの md には URL・ライセンス名・自分の言葉での要約・ファイルの sha256 だけを書く。
  一次資料の本文、ライセンス条文、画像は転記しない。引用は 1 文以内 + リンク。
- ソースごとに license / 商用利用可否 / 改変可否 / クレジット表記要否 の 4 欄を埋める。
  分からないものは「未確認」と書く。
- 使い捨てスクリプトは `work/artifact_print/`、中間生成物は `.local` か `outputs/`(非管理)。
