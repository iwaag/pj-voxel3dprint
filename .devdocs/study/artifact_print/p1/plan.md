# artifact_print Phase 1 — 骨董品・美術品 3D スキャンのカラー voxel print 事前調査

Parent: `braindump.md`(要望)、`advice.md`(データソースの当たり)。
Scope: **調査のみ**。実装はフィジビリティ確認用の使い捨てスクリプトまで、
実機プリントはしない。成果は `study/3dprint_artifact/`(git 管理)と
`.local/study/3dprint_artifact/`(一次資料、非管理)に分けて置く。

## 要望の分解

braindump を、答えるべき問いに分けると次の 5 つになる。

| # | 問い | 成果物 |
|---|---|---|
| Q1 | データはどこで入手できるか | `sources.md` |
| Q2 | 最初の MVP に向くデータはどれか | `candidates.md` |
| Q3 | 現時点でそれを 3D プリント可能な形にできるか(現行ツールチェーンとのギャップ) | `pipeline_feasibility.md` |
| Q4 | どんな手法・計算・ツールが使えそうか | `methods_tools.md` |
| Q5 | その他必要な情報(プリンタ制約、材料、法的条件、コスト) | `print_constraints.md`, `license_notes.md`, `open_questions.md` |

最後に `README.md` で「推奨データ + 推奨パイプライン + リスク + 次フェーズ提案」を
1 ページにまとめる。

## 運用ルール(braindump の制約)

- **一次資料は `.local/study/3dprint_artifact/` にのみ置く。** ダウンロードした
  モデル、テクスチャ、PDF、スクリーンショットは git に入れない(`.local/` は
  既に `.gitignore` 済み)。
- git 管理する md には **URL・ライセンス名・自分の言葉での要約・ファイルの
  sha256** だけを書く。一次資料の本文やライセンス条文、画像の転記はしない。
  引用が必要なときも 1 文以内にとどめ、リンクを添える。
- ソースごとに必ず **license / 商用利用可否 / 改変可否 / クレジット表記要否**
  の 4 欄を埋める。空欄は「未確認」と明記する。
- 各ステップの終わりに `reportN.md` をこのフォルダに書く(done / commands /
  learned / skipped)。既存 episode と同じ形式。

## 再利用する事実(現行ツールチェーン)

調査の基準になるので先に固定しておく。

- **入力ルート**: `vdbmat-utils voxelize-mesh` は **STL 1 個 → 単一 material ID**
  のみ。watertight・一貫向き付け・単一連結が前提。dense 法で
  `max_axis_cells=128`, `max_total_cells=2_000_000` のガードあり
  (`vdbmat-utils/src/vdbmat_utils/mesh/voxelizer.py`)。
  glTF / OBJ / テクスチャ / 頂点色は一切読めない。
- **出力ルート**: `export-print-slices` は GrabCAD PNG 方式。1 画像あたり
  背景を除き **最大 6 色(High Speed は 3 色)**、材料 ID の補間禁止、
  X 600 dpi / Y 300 dpi / 層厚 14 or 27 µm
  (`.devdocs/vision/printer_export/roadmap.md`)。
- **実機**: Stratasys J850、クリアは VeroUltraClear
  (`casestudy/real_print/batch1/printer_info/memo.txt`)。batch1 で
  agate / amber / fur の 60×30×5 mm スラブを印刷済み。
- **見た目予測**: `vdbmat` に印刷配合ベースの光学ライブラリ
  `vero-j850-provisional-v3` と Kubelka-Munk 列サロゲートがある
  (`.devdocs/episodes/viewer_feedback_improve/p2/`)。色→材料配合を決める
  際の前向きモデルとして使える可能性がある。
- **規模感**: 50 mm の物体をプリンタピッチ(42.3 × 84.7 × 14 µm)で
  素直に dense 化すると約 1180 × 590 × 3570 ≒ 25 億ボクセル。
  batch1 の fur は 1418 × 354 × 358 ≒ 1.8 億で、`vdbmat convert` が
  12 分。**フルサイズ美術品を dense 配列で持つのは無理**で、粗い格子か
  スライス単位のストリーム処理が要る。これは Q3 の核心。

## ステップ

### Step 0 — 置き場と雛形(半日)

- `study/3dprint_artifact/` に上表の md を空の見出しつきで作る。
  `README.md` に本 plan へのリンクと運用ルールを書く。
- `.local/study/3dprint_artifact/{models,docs,shots}/` を作り、
  `README.md`(非管理)に「何をどこから落としたか」のログを置く。
- 出力: `report0.md`。

### Step 1 — データソース調査(Q1、1〜2 日)

advice.md の 4 候補を起点に、**10〜20 ソース**を横断して `sources.md` に
表を作る。列: 名前 / URL / 種別(美術品・骨董考古・建築遺跡・自然史)/
点数の目安 / 配布形式(glTF, GLB, OBJ, USDZ, STL, 点群)/ **色情報の有無と
種類(UV テクスチャ, 頂点色, PBR)** / ライセンス 4 欄 / 取得方法(手動 DL,
API, 要ログイン)/ 備考。

当たる先(順序は advice.md 通り、その後に広げる):

1. Smithsonian Open Access 3D(CC0、API あり。API でメタデータ一括取得が
   できるか確認)
2. British Museum on Sketchfab(点数・DL 可否・ライセンスを実際に確認。
   advice.md の「約 260 点」は検証する)
3. Sketchfab の博物館公式アカウント群(Sketchfab Download API の条件、
   `downloadable` + CC フィルタの使い方)
4. Open Heritage 3D / CyArk(遺跡中心。MVP には大きすぎる可能性を確認)
5. Scan the World(MyMiniFactory)、Europeana、MorphoSource、
   Archaeology Data Service、Zenodo、大学リポジトリ
6. 国内: 国立文化財機構・奈良文化財研究所・各博物館の 3D 公開状況、
   Sketchfab 上の日本の館の公式アカウント
7. 研究用の定番(Stanford 3D Scan Repository 等)は「美術品ではないが
   パイプライン検証用」として別枠に記録

`advice.md` の助言どおり、最後に **美術品中心 / 骨董・考古中心 /
建築・遺跡中心 / CC0 で商用可** の 4 分類で一覧を作る。

- 出力: `sources.md`, `license_notes.md`(CC0 / CC BY / CC BY-NC /
  館独自規約の違いと、社内検討・展示・販売それぞれで何が要るかの整理)、
  `report1.md`。

### Step 2 — MVP 候補の選定(Q2、1 日)

`sources.md` から **5〜10 点**を候補に挙げ、**2〜3 点**に絞る。

選定基準(`candidates.md` の冒頭に明文化する):

- ライセンス: CC0 または CC BY。NC 付きは「検討用のみ」と注記して残す。
- 形式: glTF/GLB/OBJ + テクスチャがそのまま落とせる(色が要るので STL のみは不可)。
- 形状: 単一の閉じたソリッドに近い、または簡単に修復できる。
  薄板・開口・内部空洞が少ない。
- 大きさ: J850 造形域(490 × 390 × 200 mm)に入る縮尺で、
  **粗格子 MVP なら 128 cells/axis 以内**に収まる縮尺が取れる。
- 色: 支配的な色が少ない(≤ 6 材料に量子化しても破綻しない)ものを 1 点、
  連続階調があるものを 1 点。
- 材質: 不透明な彩色物(陶器、木彫、彩色石像)を 1 点と、
  **半透明・透明の素材(翡翠、琥珀、ガラス、雪花石膏)** を 1 点。
  後者は本システムの光学シミュレーションが効く領域なので優先度を高くする。

候補は `.local` に実データを落とし、次を測って記録する: 三角形数、
テクスチャ解像度と種類、bbox と単位、watertight / manifold 判定、
連結成分数、sha256。判定は trimesh / Open3D で行い、コマンドは report に残す。

- 出力: `candidates.md`(表 + 各候補の所見 + 最終 2〜3 点の理由)、`report2.md`。

### Step 3 — 現行ツールチェーンとのギャップ分析(Q3、1 日)

「色つきスキャン → material-label voxel → GrabCAD スライス」の各段で、
今あるもの / 無いもの / 埋め方の選択肢 / 工数感を表にする。

想定される主なギャップ:

| 段 | 現状 | 必要なこと |
|---|---|---|
| 読み込み | STL のみ | glTF/OBJ + UV テクスチャ / 頂点色の読み込み(trimesh 等) |
| 修復 | watertight を要求するだけ | 穴埋め・自己交差除去・複数連結成分の扱い |
| 形状のボクセル化 | dense、128 cells/axis | 粗格子で MVP、将来はスライス単位のラスタライズかスパース化 |
| 色の体積化 | 無し | 表面色を **厚さ N ボクセルのシェル**に写し、内部は基材(白 or クリア)にする方式の検討 |
| 色→材料 | 無し | (a) パレット量子化 ≤ 6 材料、(b) CMYKW+クリアの 3D ハーフトーン(誤差拡散)。MVP は (a) |
| 透明素材 | 光学ライブラリはある | 半透明感を material 配合で作る場合の配合設計(KM サロゲートで事前確認できるか) |
| 出力 | export-print-slices あり | 6 色制限・スライス数・物理寸法の確認のみ |

- 「今すぐ可能か」への答えを **MVP ルート(粗格子 + シェル着色 + 6 色量子化)**
  と **本命ルート(プリンタピッチ + ハーフトーン)** に分けて書く。
- 出力: `pipeline_feasibility.md`, `report3.md`。

### Step 4 — 手法・計算・ツール調査(Q4、1〜2 日)

各ギャップに対して使えそうなものを列挙し、ライセンス / uv 環境への導入可否 /
一言評価をつける。転記ではなく参照リンク + 自分の要約で書く。

- **メッシュ読み込み・修復**: trimesh, Open3D, PyMeshLab, pymeshfix,
  Manifold, Blender(remesh / voxel remesh)
- **ボクセル化**: trimesh voxel, Open3D VoxelGrid, OpenVDB mesh→SDF,
  binvox, cuda_voxelizer、スライス単位のポリゴン塗りつぶし(スライサ方式)
- **色の体積化・ハーフトーン**: 3D カラープリント向けの誤差拡散と散乱補償に
  関する研究(Brunton らの 3D color printing、Elek らの scattering-aware
  texture reproduction、Sumin らの geometry-aware scattering compensation 等)、
  Fraunhofer Cuttlefish(商用の事実上の標準)。**何が公開実装として使えるか、
  何を自前で組む必要があるか**を切り分ける。
- **色管理**: J850 の色モード(VeroVivid CMY + 白 + 黒 + クリア)、
  GrabCAD 側の RGB→材料の対応の仕組み、ICC / 色域の情報源。
- **データ取得の自動化**: Smithsonian API、Sketchfab Download API の認証と制約。
- **本リポジトリで既に使えるもの**: `vdbmat` の KM サロゲートと v3 ライブラリを
  「色→配合」の前向きモデルに流用できるかを、既存 report を読んで判断する。

- 出力: `methods_tools.md`, `report4.md`。

### Step 5 — プリンタ制約・材料・コスト(Q5、半日)

- J850 の造形域、材料スロット数、使用可能材料(VeroVivid 各色、VeroUltraClear、
  Agilus、サポート材)、GrabCAD voxel print の制限(6 色 / 3 色、最低 30 スライス、
  色→材料は GUI で対応付け)を `.devdocs/vision/printer_export/roadmap.md` と
  公式ガイドから整理する。
- 社内プリンタの **実際の装填材料**、後処理(サポート除去、光沢/艶消し)、
  1 部品あたりの時間とコストの目安は、こちらで分からないので
  `open_questions.md` に「オペレータに聞くこと」として列挙する。
- 出力: `print_constraints.md`, `open_questions.md`, `report5.md`。

### Step 6 — 小規模フィジビリティ実験(Q3 の裏取り、1 日、任意)

Step 2 の候補 1 点(CC0)で、**印刷はせず**スライス生成まで通るかを試す。

1. `.local` のモデルを trimesh で読み、watertight 判定、必要なら修復。
2. 粗いピッチ(例 0.5 mm、128 cells/axis 以内)に縮尺を合わせ、
   STL に落として `voxelize-mesh` で形状ボクセルを作る。
3. `work/artifact_print/` の使い捨てスクリプトで、表面 N ボクセルのシェルに
   テクスチャ色を最近傍サンプリングし、≤ 6 色にパレット量子化して
   material ID を上書きする。
4. `export-print-slices` を通し、色数・スライス数・物理寸法をマニフェストで確認。
   `preview-slices` で見た目を確認する。
5. 余力があれば `vdbmat` で v3 ライブラリを当ててレンダし、
   「6 色量子化でどの程度見えるか」の当たりをつける。

この実験の中間生成物は `.local` か `outputs/`(非管理)に置く。
うまくいかなかった段こそ report に残す。

- 出力: `report6.md`(コマンド、失敗箇所、所要時間)。

### Step 7 — まとめと次フェーズ提案(半日)

- `study/3dprint_artifact/README.md` に、推奨データセット、推奨 MVP ルート、
  本命ルートまでの距離、主要リスク(ライセンス、規模、色再現)、
  次フェーズ(実装)の候補ステップを書く。
- 本 episode の `report7.md` に要約と、plan からの逸脱を書く。

## 成果物の対応表

```text
study/3dprint_artifact/            (git 管理)
  README.md                        Step 0, 7
  sources.md                       Step 1
  license_notes.md                 Step 1
  candidates.md                    Step 2
  pipeline_feasibility.md          Step 3
  methods_tools.md                 Step 4
  print_constraints.md             Step 5
  open_questions.md                Step 5(以降随時)
.local/study/3dprint_artifact/     (非管理)
  models/ docs/ shots/ README.md   Step 1〜6
.devdocs/study/artifact_print/p1/  report0..7.md
work/artifact_print/               Step 6 の使い捨てスクリプト
```

## スコープ外

- 実機プリント、材料の購入、社外への問い合わせ。
- `vdbmat` / `vdbmat-utils` 本体への実装変更(Step 6 は `work/` 内の
  プロトタイプのみ)。
- ハーフトーン・散乱補償の本実装(次フェーズ)。

## 想定リスク

- 色つき・DL 可・CC0 の三条件を満たす美術品は思ったより少ない可能性がある。
  その場合は CC BY まで広げ、NC 付きは「検討用」と明記して切り分ける。
- スキャンデータは薄い・開口が多い・複数部品で、watertight 化が最初の壁になる
  可能性が高い。Step 2 の判定で早めに把握する。
- 6 色量子化 MVP は「現物に近い色」には届かない見込み。届かない程度を
  Step 6 のレンダで示し、本命ルートの必要性の根拠にする。
