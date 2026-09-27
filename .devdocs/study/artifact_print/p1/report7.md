# artifact_print p1 step 7 report — まとめと次フェーズ提案

## Done

- `study/3dprint_artifact/README.md` を最終版に書き換えた。
  - 一行の結論
  - 推奨データ(MVP 1〜3)とデータの入手先の全体像
  - 推奨パイプライン(経路 0 / 1 / 2)と、plan からの重要な修正
  - 本命ルートまでの距離(5 項目)、主要リスク(5 項目)、次フェーズの候補ステップ(5 項目)、運用ルール、ファイルの一覧
- `.devdocs/study/artifact_print/p1/manual_handout.md`: 人の作業が必要なことを 3 群にまとめた。
  A は利用者の作業(Sketchfab のトークン、任意で api.data.gov のキー、Step 6 のスライスの Utility への試し投入)。
  B はオペレータへの質問の要点 6 つ。C は次フェーズで人が判断すること。
  途中で利用者から「人の作業が必要な件は無理にやらず、最後に manual_handout.md に一括で書く」と指示があったので、その形にした。

## p1 の要約

| 問い | 答え | 成果物 |
|---|---|---|
| Q1 どこで入手できるか | Smithsonian 3D(API は認証不要、CC0)と、Sketchfab の館アカウント(Mia、CMA、RMO、Saint-Raymond、SMK、Hunt、Małopolska の CC0)が二本柱。大英博物館は 95 % が NC-SA。国内は自治体の Sketchfab(CC BY) | sources.md、license_notes.md |
| Q2 MVP に向くのはどれか | 染付の水注(水密、2 系統の色)、炻器の水差し(連続階調)、玉璧(半透明、未取得) | candidates.md |
| Q3 今すぐ可能か | GrabCAD の通常フルカラーなら今すぐ刷れる。本システムの MVP ルートも、Step 6 でスライスまで通した(60 mm、約 3.5 分)。本命ルート(連続色、誤差拡散、散乱補償)は研究開発が必要 | pipeline_feasibility.md、report6 |
| Q4 手法とツール | 部品は OSS で揃う(trimesh、Open3D、manifold3d、libigl)。研究の公開実装は無い。既存資産(batch1 のディザ、KM、Mitsuba)がそのまま効く | methods_tools.md |
| Q5 その他 | J850 の制約(6 樹脂 / スライス、7 スロット)、装填された樹脂が未確認、時間と費用はオペレータへの確認待ち | print_constraints.md、open_questions.md、manual_handout.md |

## plan からの逸脱

1. **MVP の定義を変えた**: plan の「(a) パレット量子化で 6 材料以下」は、Voxel Print では PNG の 1 色が 1 樹脂なので成り立たない(Step 3)。
   Step 6 で数値(ΔE 14〜16)と見た目(地がガラス状)でも確かめた。MVP を「意味ラベル(数は任意)+ ラベルごとの配合 + batch1 のディザ」に置き換えた。
2. **既存の `voxelize-mesh` と `export-print-slices` を主経路にしなかった**: `voxelize-mesh` は 57 分で終わらず、`export-print-slices` にはディザが無い。
   Open3D の占有判定と、batch1 方式の直接書き出しを、使い捨てスクリプトで組んだ。plan の手順(STL → `voxelize-mesh`、`export-print-slices` でマニフェスト確認、
   `preview-slices`)自体は実行して、結果を記録した。
3. **色の格子を 0.1 mm まで下げた**(plan は粗いピッチ、例えば 0.5 mm)。0.5 mm では絵付けがモザイクになったため。
4. **半透明の候補は未取得**(Sketchfab のトークンが無い)。Step 2 の「実データを落として計測」は、Smithsonian の 10 点だけで行った。
5. **Step 4 と Step 5 の調査を Step 1 と同時に起動した**(サブエージェントを並行で走らせるため)。報告と commit はステップ順に行った。
6. 計測用に、非管理の venv(`.local/study/3dprint_artifact/venv`: trimesh 5.1、Open3D 0.20、manifold3d、DracoPy ほか)を作った。
   `vdbmat` と `vdbmat-utils` の依存関係は変えていない。

## Learned(p1 全体)

- 「入手」と「スライス生成」は、どちらももう障害ではない。障害は **色の正しさ** で、KM で解いた配合は Mitsuba で白が黄緑に寄った。
  これは、v3 ライブラリが未校正であることと、KM と Mitsuba の食い違い(p2 で既知)が、白い陶磁器で表に出たもの。
  次フェーズは、Mitsuba での補正、クーポンによる校正、実機での比較が中心になる。
- 既存資産の価値が大きかった。batch1 の 3D ハッシュディザ、KM サロゲート、recipes → mapping、Mitsuba ステージが、ほぼ無改造で MVP に組み込めた。

## Skipped

- 実機での印刷、社外への問い合わせ(plan の範囲外)。
- 人の作業が必要なものは、すべて `manual_handout.md` に回した。
- Sketchfab 調査のサブエージェントが後から補足データ(173 モデルの面数とテクスチャ数)を返してきた。結論は変わらないので、
  `.local/study/3dprint_artifact/docs/api_snapshots/sketchfab/all_details.json` に保存するだけにした(次フェーズで候補を広げるときに使える)。
