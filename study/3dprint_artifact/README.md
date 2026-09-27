# 3dprint_artifact — 骨董品・美術品 3D スキャンのカラー voxel print 事前調査

> artifact_print p1(2026-09-27)のまとめ。計画: [.devdocs/study/artifact_print/p1/plan.md](../../.devdocs/study/artifact_print/p1/plan.md)。
> ステップごとの報告: 同じフォルダの `report0.md`〜`report7.md`。人の作業が必要なこと: `manual_handout.md`。

## 一行の結論

**世界の美術品の色つきスキャンを CC0 で入手し、本システムで J850 の Voxel Print 用スライスまで作ることは、今すぐできる**
(染付の水注を 60 mm にして、実際に 3.5 分で通した)。**難しいのは「現物に近い色」の方**で、配合の補正と、樹脂の実測校正が次の本題になる。

## 推奨データ

| 用途 | データ | 入手先 | ライセンス | 状態 |
|---|---|---|---|---|
| **MVP 1**(不透明、支配色が少ない) | 染付の水注(Cooper Hewitt 1986-61-53) | Smithsonian 3D API(認証不要) | CC0(Smithsonian の方針。個別表示は要確認) | 取得済み。**水密で、修復が不要**。Step 6 で使用 |
| **MVP 2**(連続階調) | 塩釉の炻器の水差し(Thomas Commeraw、NMAAHC 2011.61) | Smithsonian 3D API | 同上 | 取得済み。小さな穴(境界辺 10)がある |
| **MVP 3**(半透明) | 玉璧(Mia `d763ec3d…`)。予備は雪花石膏の喪服像(CMA)、ヒスイ製勾玉(加曽利貝塚、CC BY) | Sketchfab | CC0 / CC BY | **未取得**(DL に API トークンが必要) |

データの入手先の全体像([sources.md](sources.md)、[license_notes.md](license_notes.md)):

- まとまった量で **色つき、DL 可、CC0** なのは、**Smithsonian 3D**(約 3,500 パッケージ。大半は自然史で、美術品は約 20 点)と、
  **Sketchfab 上の館の公式アカウント**(Minneapolis Institute of Art の CC0 が 207 件、Cleveland、Leiden RMO、Saint-Raymond、SMK、Hunt、Małopolska)。
- 大英博物館の Sketchfab は、DL 可の 95 % が BY-NC-SA で、**検討用のみ**。
- 国内では、中央のポータルに 3D がほとんど無く、自治体や研究所の Sketchfab(CC BY 4.0)が主な出どころ。
- 遺跡系(Open Heritage 3D)は大きすぎ(平均約 25 GB / サイト)。Scan the World は色なし(STL)。

## 推奨パイプライン

| 経路 | 内容 | 今の位置 |
|---|---|---|
| **0. 基準** | GrabCAD Print の通常フルカラー(テクスチャ付きの OBJ / 3MF を直接渡す) | 本システムを使わずに今すぐ刷れる。**比較の基準として最初に 1 回刷る** |
| **1. MVP ルート**(推奨) | 形状: STL をプリンタピッチで直接占有判定(Open3D)/ 色: 0.1 mm 格子のシェルにテクスチャ色 → k 個の意味ラベル / 配合: KM サロゲートで 6 樹脂を逆算 / 出力: batch1 と同じ 3D ハッシュディザ | **Step 6 でスライスまで通った**(`work/artifact_print/`)。21.6 億ボクセル、3,920 層を約 2 分 |
| **2. 本命ルート** | ボクセルごとの連続色、配合の 3D LUT、3D 誤差拡散、散乱補償、測色による校正 | 公開実装は無い。研究開発が必要(数週間〜月単位) |

詳細: [pipeline_feasibility.md](pipeline_feasibility.md)(段ごとのギャップと Step 6 の裏取り)、[methods_tools.md](methods_tools.md)(ツールと論文)、
[print_constraints.md](print_constraints.md)(J850 と Voxel Print の制約)。

**plan からの重要な修正**: 「6 色以下へのパレット量子化」は MVP にならない。Voxel Print では PNG の 1 色が 1 つの物理樹脂なので、
6 色に量子化すると純色の樹脂への塗り分けになる(Step 6 で ΔE 14〜16、地がガラス状)。MVP でも樹脂を混ぜるディザが必須だが、それは batch1 の方式で既に解けている。

## 本命ルートまでの距離

1. **色の正しさ**(最優先): KM で解いた配合は、Mitsuba では白が黄緑に寄った。配合を Mitsuba で補正するループ(p2 の `c_r` 方式)と、
   白、CMY、クリアのクーポンの実測校正が要る。v3 ライブラリは写真へのフィットで、未校正。
2. **ボクセルごとの連続色**: ラベル k 個 → 3D LUT に置き換える。1 週間程度。
3. **3D 誤差拡散**: Brunton ら 2015 を自前で実装する。2〜4 週間。
4. **散乱補償、半透明の目標値**: Elek ら 2017、Sumin ら 2019、Urban ら 2019。研究課題。
5. **本体への取り込み**: 既存の `voxelize-mesh` は、15 万面のスキャンで 57 分以上かかって実用にならない(Open3D なら 0.3 s)。
   `export-print-slices` にもディザが無い。MVP ルートを `vdbmat-utils` に入れるなら、この 2 つの置き換えが必要。

## 主要リスク

| リスク | 内容 | 対策 |
|---|---|---|
| ライセンス | 同じ館でも、モデルごとにライセンスが混在する。NC / ND の見落とし。Smithsonian は API でライセンスが分からない | DL した時点の license を記録する。社外に出すものは CC0 / CC BY に限る。法務の確認 |
| 規模 | 実寸(25 cm)だとプリンタピッチで 1,577 億ボクセル | スライス単位のストリーミング(Step 6 の方式)で、メモリはスライス 1 枚分。時間はボクセル数に比例する(60 mm で約 2 分 → 実寸は 73 倍で約 2〜3 時間の見込み)。ただし、0.1 mm のラベル格子は、60 mm で 1.1 億セル(ピークのメモリ 6〜10 GB)。実寸では約 80 億セルになり、密な配列では持てない → ラベルもシェルだけの疎な形式か、タイル単位にする |
| 色再現 | 配合のモデル誤差(KM と Mitsuba の食い違い)、ライブラリが未校正、装填された樹脂が未確認(Vivid か旧 Vero か) | Mitsuba での補正、クーポン、オペレータへの確認 |
| 形状 | 開いた器、薄い壁、複数の成分。縮小で壁が薄くなる | 修復(manifold3d、巻き数判定)。縮尺の下限を壁厚で決める |
| 半透明 | KM は半透明の配合が苦手。実データも未取得 | Mitsuba とクーポン。トークンを得てから玉璧で試す |

## 次フェーズ(実装)の候補ステップ

1. **実機での比較**: 水注(60 mm)を、(a) GrabCAD の通常フルカラーと、(b) 本システムの MVP スライス(`ewer60-0p1-k8-km-mesh`)で刷り、写真で比べる。
   刷る前に、オペレータへの確認事項(`manual_handout.md`)を片付ける。
2. **配合の Mitsuba 補正**: ラベルごとの補正係数で配合を再フィットし、白が中立に出ることをレンダで確かめる。
3. **白、CMY、クリアのクーポン**(配合 × 厚さ)を刷って測り、v3 を実測で校正する(v4)。
4. **半透明の MVP**: Sketchfab のトークンで玉璧と勾玉を取得し、クリア + 少量の白 + 色の深さ方向の分布を Mitsuba で設計する。
5. **本体への取り込み**: `vdbmat-utils` に、glTF の読み込み、Embree 系の占有判定、テクスチャのシェル、配合ディザの書き出しを入れる
   (`work/artifact_print/` を下敷きにする)。

## 運用ルール

- 一次資料(ダウンロードしたモデル、テクスチャ、PDF、スクリーンショット)は、`.local/study/3dprint_artifact/{models,docs,shots}/` にのみ置く
  (`.local/` は `.gitignore` 済み)。取得ログ(URL、sha256)は `.local/study/3dprint_artifact/README.md`(非管理)。
- このフォルダの md には、URL、ライセンス名、自分の言葉での要約、ファイルの sha256 だけを書く。一次資料の本文、ライセンス条文、画像は転記しない。
- ソースごとに、ライセンス / 商用 / 改変 / クレジットの 4 欄を埋める。分からないものは「未確認」と書く。
- 使い捨てスクリプトは `work/artifact_print/`、計測用の venv と中間生成物は `.local/study/3dprint_artifact/`(非管理)。

## ファイル

| ファイル | 内容 |
|---|---|
| [sources.md](sources.md) | データソース約 40(Q1) |
| [license_notes.md](license_notes.md) | ライセンス別の可否、注意点、クレジットのひな形 |
| [candidates.md](candidates.md) | 選定基準、計測した 10 点 + Sketchfab の 9 点、最終 3 点(Q2) |
| [pipeline_feasibility.md](pipeline_feasibility.md) | 経路 0 / 1 / 2、段ごとのギャップ、規模、Step 6 の裏取り(Q3) |
| [methods_tools.md](methods_tools.md) | ツール、論文、色管理、取得の自動化、既存資産の流用判断(Q4) |
| [print_constraints.md](print_constraints.md) | J850、材料、Voxel Print の制約、後処理、コスト(Q5) |
| [open_questions.md](open_questions.md) | 未解決の問い(オペレータへの質問を含む) |
