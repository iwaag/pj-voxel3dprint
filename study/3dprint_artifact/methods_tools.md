# 手法・計算・ツール(Q4)

> 調査日: 2026-09-27(artifact_print p1 Step 4)。調査は sonnet サブエージェント 3 体(3D カラー印刷の研究、メッシュ / ボクセル化ツール、
> J850 と GrabCAD)で行った。pip で入るかどうかは、使い捨ての venv(Python 3.12、Linux x86_64)で確認した。
> 各項目は、参照リンク + 自分の要約。「未確認」は、公開ページや検索では裏が取れなかったもの。

## 結論(先に)

- **テクスチャ付きメッシュから Stratasys のボクセルスライスまでを通す公開実装は見つからなかった。** 研究(Fraunhofer IGD、IST Austria / UCL、MIT、
  カレル大学)は、アルゴリズムと検証済みの光学モデルを論文にしているが、コードは公開されていないか、商用化されている(Cuttlefish)。
  **自前で組むしかない**が、部品(読み込み、修復、占有判定、最近傍色)は、成熟した OSS でほぼ揃う。
- 部品の推奨: 読み込みは **trimesh**、修復は **manifold3d**(Apache-2.0)を主に使い、ロバストな内外判定には **libigl の一般化巻き数**を使う。
  スライスごとの占有判定と最近傍の色の参照には **Open3D `RaycastingScene`** を使う(同じ加速構造を使い回せる)。
- 本リポジトリの資産で直接効くもの: **batch1 の 3D ハッシュディザ**(そのまま移植できる)、**KM 列サロゲート + v3 ライブラリ**
  (不透明色の配合の逆問題に使える。半透明には弱い。下記)、**recipes → optical mapping → Mitsuba** の見え方の予測。
- 最も参考になる論文(コードは無い): 誤差拡散は Brunton ら 2015、ボクセル単位の最適化は Nindel ら 2021、
  データ → ディザ → Stratasys の流れは Bader ら 2018、半透明の目標値の定義は Urban ら 2019。

## 1. メッシュの読み込みと修復

| ツール | URL | ライセンス | pip(py3.12) | 役割 | 一言評価 |
|---|---|---|---|---|---|
| trimesh | https://github.com/mikedh/trimesh | MIT | ○(5.1.0) | GLB / glTF / OBJ の読み込み、`TextureVisuals`、UV、頂点統合、`repair.fill_holes` | **既定の読み込み器**。Step 2 で 10 点を読めた。Draco 圧縮には DracoPy が要る |
| Open3D | https://www.open3d.org/ | MIT | ○(0.20.0) | テンソル版の I/O、`RaycastingScene`(Embree) | 読み込みより、問い合わせのエンジンとして使う |
| pygltflib | https://github.com/dodgyville/pygltflib | MIT | ○ | glTF の低レベル操作 | 拡張や検証が必要なときだけ |
| manifold3d | https://github.com/elalish/manifold | Apache-2.0 | ○(3.5.4) | 多様体を保証するブーリアン、レベルセットによる再構成 | **修復の主力**。ライセンスが緩い |
| pymeshfix | https://github.com/pyvista/pymeshfix | 未確認(元の MeshFix は非商用に限る歴史がある) | ○ | 穴埋め、自己交差の除去 | 商用に使う前にライセンスを確認する |
| PyMeshLab | https://github.com/cnr-isti-vclab/PyMeshLab | GPL-3.0 | ○ | MeshLab のフィルタ全般(穴を閉じる、非多様体の修復) | 最もロバストだが、GPL なので社内ツールに限る |
| MeshLib | https://meshlib.io/ | ソース公開、**商用は有償** | ○ | 自己交差の修正、ボクセルベースの再構成 | 商用には有償ライセンスが要る |
| Blender(bpy)の voxel remesh | https://www.blender.org/ | GPL | 未確認(wheel が大きい) | 確実に水密化できるが、**UV が失われる** | 重く、テクスチャの再投影も要るので、優先度は低い |

修復後のテクスチャ: 再メッシュで UV が失われた場合は、各頂点(または各ボクセル)について**元のメッシュ上の最近傍点**を求め、
その UV からテクスチャを引き直す(Open3D の `compute_closest_points`、`trimesh.proximity.closest_point`)。
本システムでは色をボクセル側で持つので、**メッシュの UV を保つ必要はそもそも無い**。形状は修復したメッシュから、
色は元のメッシュから取ればよい。

## 2. ボクセル化(形状)

| 方式 | URL | ライセンス | pip | 規模 | 一言評価 |
|---|---|---|---|---|---|
| `vdbmat-utils voxelize-mesh`(既存) | 本リポジトリ | — | — | 1 軸 128 セル、総数 200 万セル | MVP の粗格子にはこれで足りる。STL、水密、単一成分が前提 |
| trimesh.voxel | trimesh | MIT | ○ | 密な配列 | 中規模まで |
| Open3D `VoxelGrid.create_from_triangle_mesh` | Open3D | MIT | ○ | 表面だけ | 中身は埋まらない |
| **Open3D `RaycastingScene.compute_occupancy` / `compute_signed_distance`** | https://www.open3d.org/docs/release/tutorial/geometry/ray_casting.html | MIT | ○ | 任意の点群を問い合わせられる → **スライスごとの XY 格子を流せる** | **本命ルートの第一候補**。速度は実データで計測が必要(Step 6) |
| **libigl `fast_winding_number`** | https://libigl.github.io/libigl-python-bindings/ | MPL-2.0 | ○ | 点の問い合わせ | 穴のあるメッシュでも内外判定がロバスト → **修復なしのルート**が取れる |
| pysdf | https://github.com/sxyu/sdf | 未確認 | ○ | 点の問い合わせ | Open3D の代わりとして比較する価値がある |
| mesh-to-sdf | https://github.com/marian42/mesh_to_sdf | 未確認 | ○ | レンダリングで SDF を取る | 10⁹ 規模には遅い |
| OpenVDB `meshToVolume` | https://www.openvdb.org/ | MPL-2.0 | pip の pyopenvdb には無い(未確認) | 疎な SDF | 本リポジトリの Docker イメージ(`vdbmat-openvdb-cycles`)に OpenVDB 10 がある。C++ か自前ビルドが必要 |
| binvox | https://www.patrickmin.com/binvox/ | 非商用 | CLI | 密な配列 | 規模とライセンスの両方で不向き |
| cuda_voxelizer | https://github.com/Forceflow/cuda_voxelizer | MIT | 自前ビルド | GPU で高速 | GPU があれば試す価値がある |
| スライサ方式(`trimesh.section_multiplane` + 多角形の塗りつぶし) | trimesh + Pillow / scikit-image | MIT 系 | ○ | スライス 1 枚ずつ | **プリンタピッチのラスタライズを最もよく制御できる**。断面が閉じないメッシュには弱い |

## 3. 色の体積化とハーフトーン(研究)

| 文献 | リンク | 要約(自分の言葉) | 公開実装 | 本システムとの関係 |
|---|---|---|---|---|
| Brunton, Arikan, Urban. *Pushing the Limits of 3D Color Printing: Error Diffusion with Translucent Materials.* ACM TOG 35(1), 2015 | https://doi.org/10.1145/2832905 | 2D の誤差拡散を、物体の表面に沿った層ごとの走査に拡張し、半透明の樹脂が重なった結果の色を目標に合わせる | 無し(Cuttlefish に組み込まれている) | **本命ルートの誤差拡散の手本**。走査順と、層をまたぐ誤差の流し方 |
| Brunton, Arikan, Tanksale, Urban. *3D Printing Spatially Varying Color and Translucency.* ACM TOG 37(4), 2018 | https://doi.org/10.1145/3197517.3201349 | 色と半透明を同時に合わせる。測定から駆動までのパイプライン | 無し | 半透明素材(翡翠、雪花石膏)の目標の立て方 |
| Urban ら. *Redefining A in RGBA: Towards a Standard for Graphical 3D Printing.* ACM TOG 38(3), 2019 | https://arxiv.org/abs/1710.00546 | RGBA の A を、物理的に定義された半透明度にする提案と、その測定手順 | 仕様の提案(コードは無い) | **半透明の目標値の定義**に採用を検討する |
| Elek ら. *Scattering-aware Texture Reproduction for 3D Printing.* ACM TOG 36(6), 2017 | https://visualcomputing.ist.ac.at/publications/2017/TexFab/ | 樹脂内部の散乱で模様がぼけるのを、前向きモデルで予測し、あらかじめ強調しておく | 無し | 染付の細い線がぼける問題。Mitsuba で再現できるかを先に確かめる |
| Sumin ら. *Geometry-Aware Scattering Compensation for 3D Printing.* ACM TOG 38(4), 2019 | https://doi.org/10.1145/3306346.3322992 | 上の手法を曲面に拡張(曲率でぼけ方が変わる) | 無し | 器の縁、彫刻の凹凸 |
| Babaei ら. *Color Contoning for 3D Printing.* ACM TOG 36(4), 2017 | https://doi.org/10.1145/3072959.3073605 | 網点ではなく層の厚さで色を作る(コントーン) | 無し | シェルの厚さを配合の代わりに使う発想 |
| Shi ら. *Deep Multispectral Painting Reproduction via Multi-Layer, Custom-Ink Printing.* ACM TOG 37(6), 2018 | https://gfx.cs.princeton.edu/pubs/Shi_2018_DMP/index.php | 層の積み重ねの前向きモデルをニューラルネットで学習し、分光で最適化する | 未確認 | KM サロゲートの発展形として参考になる |
| Nindel ら. *A Gradient-Based Framework for 3D Print Appearance Optimization.* ACM TOG 40(4), 2021 | https://doi.org/10.1145/3450626.3459844 | 見え方(色、半透明)を勾配で最適化し、ボクセルごとの材料比率を決める | 無し | **Mitsuba を持つ本システムと最も相性がよい**(Mitsuba 3 は微分可能レンダラ)。本命ルートの長期候補 |
| Morsy, Brunton, Urban. *Shape Dithering for 3D Printing.* ACM TOG 41(4), 2022 | https://doi.org/10.1145/3528223.3530129 | 形状そのものをディザする | 無し | 参考 |
| Bader ら. *Making Data Matter: Voxel Printing for the Digital Fabrication of Data across Scales and Domains.* Science Advances 4(5), 2018 | https://doi.org/10.1126/sciadv.aas8652 | 体積データを、メッシュを経ずに、ディザしたビットマップとして Stratasys に渡す | 無し | **本システムの MVP の流れとほぼ同じ**。ディザの作り方の参考 |
| OpenFab(Vidimče ら 2013) | https://doi.org/10.1145/2461912.2461993 | 材料の組成をシェーダのように手続き的に記述する | 無し(未確認) | ラベル → 配合の API 設計の参考 |

商用:

- **Fraunhofer Cuttlefish**(https://www.cuttlefish.de/): 上の Brunton らの研究を実装したプリンタ非依存のドライバ。
  色、半透明、光沢を扱う。商用ライセンスで、学術ライセンスの有無は未確認。**本システムが目指すところの商用の到達点**なので、
  可能ならデモを見て比較の基準にする(社外への問い合わせになるので、本 phase の範囲外)。
- **GrabCAD Print の通常フルカラー**: テクスチャ付きの OBJ / VRML / 3MF を読み、Vivid の CMY + 白 + 黒 + クリアへ自動で割り付ける。
  内部の構造と半透明は制御できない。**比較の基準**にする(→ [pipeline_feasibility.md](pipeline_feasibility.md) の経路 0)。
  手順は GrabCAD の公式チュートリアル(https://grabcad.com/tutorials/how-to-3d-print-in-full-color-part-1)を参照。
- Mimaki 3DUJ-553: UV インクジェット方式で、ICC に準拠。PolyJet ではないので、色管理の考え方の比較用。

## 4. 色管理(J850)

- 材料: **VeroVivid**(CyanV、MagentaV、YellowV)、**VeroUltra**(White、Black、Clear。白と黒の不透明度は 99 % 超)。
  組み合わせで 50 万色以上。CMY + 黒 + 白で PANTONE の約 1,970 色に合わせられる、とされている
  (https://www.stratasys.com/en/3d-printers/printer-catalog/polyjet/j8-series-printers/j850-prime-3d-printer/ 、
  https://www.stratasys.com/contentassets/0f51534fbaf341739df42c45f2f4702f/bp_pj_3dprintingwithpantone_0120a.pdf )。
  **社内で実際に装填されている樹脂**(Vivid か旧 Vero カラーか)は未確認(→ [open_questions.md](open_questions.md))。
  batch1 の材料対応メモは、旧名(VeroCyan / VeroMgnt / VeroYellow)。
- GrabCAD Voxel Print では、PNG の各色を GUI で装填された樹脂に割り当てる。公式ガイドには、樹脂ごとの参考 RGB の表がある
  (https://support.stratasys.com/en/Software/GrabCAD-Print/Tips-Guides-and-FAQs/Guide-to-Voxel-Printing)。
- ICC プロファイルや公開された ΔE 表は見つからなかった。**半透明に対する業界標準の色管理は無い**(Urban ら 2019 が、その穴を埋めようとしている)。
  色の校正は、自前のチャート(配合 × 厚さ)を刷って分光測色計で測るしかない。

## 5. データ取得の自動化

- **Smithsonian 3D**: `https://3d-api.si.edu/api/v1.0/content/file/search?q=<語>&rows=<n>&start=<k>`。**認証不要**で、
  各ファイルの直リンク、品質、形式、サイズが取れる(Step 1 で全 41,296 行を取得した)。オブジェクト側のメタデータ(素材、実寸、CC0 の表示)は
  Open Access API(`api.si.edu/openaccess/api/v1.0/`、api.data.gov のキーが必要。DEMO_KEY は 1 時間あたりの上限が低い)。
  取得スクリプト: `work/artifact_print/fetch_si.py`。
- **Sketchfab Data API v3**: 検索(`/v3/search?type=models&downloadable=true&license=cc0&categories=cultural-heritage-history`)と
  メタデータ(`/v3/models/{uid}`)は認証なしで使える(ただし詳細の方は、連続して叩くと 429 になる)。
  DL(`/v3/models/{uid}/download`)には、OAuth2 か、**個人の API トークン**(`Authorization: Token …`)が要る。
  返ってくるのは、約 300 秒で失効する署名付き URL(glTF zip、GLB、USDZ)。元の形式(FBX / OBJ)は API では取れない
  (https://sketchfab.com/developers/download-api)。**ライセンスはモデル単位で、DL した時点の値を記録する。**
- Europeana API: 横断検索の入口(`qf=TYPE:3D`)。実体は提供元へのリンク。

## 6. 本リポジトリで既に使えるもの(既存の report を読んだうえでの判断)

| 資産 | 場所 | 使い道 | 判断 |
|---|---|---|---|
| 3D ハッシュディザ(決定的) | `work/fur/export_floating_fur_voxelprint.py` の `noise()` と、累積比率の `searchsorted` | 意味ラベルの配合 → プリンタピッチの樹脂ラベル | **そのまま移植できる**。batch1 の実機で Voxel Print Utility に通っている |
| KM 列サロゲート | `work/resins/km_surrogate.py`(`layer_rt`、`column_rgb`) | 配合 → 見かけの sRGB の前向きモデル。逆問題を解けば、色 → 配合になる | **不透明色には使える**: KM は Mitsuba に比べて 1.2〜1.4 倍明るく出るが、比率がほぼ一定なので補正係数で消せる(`.devdocs/episodes/viewer_feedback_improve/p2/report4.md`)。**半透明には弱い**: クリアに白を薄く混ぜた配合では、色の形が Mitsuba とずれる(fur の下毛で ΔE 12.4、amber の母材 100 % で ΔE 16.2)。翡翠や雪花石膏こそこの領域なので、**KM で当たりを付けてから、必ず Mitsuba で確かめ、最後はクーポンで実測する** |
| 光学ライブラリ v3 | `work/resins/vero-j850-provisional-v3.json` | 6 樹脂の σa、σs′(線形 sRGB) | 写真へのフィットで、測色による校正ではない(`calibration_status: provisional-uncalibrated`)。色の絶対値は ±15〜20 %(露出)の不確かさを持つ |
| recipes → optical mapping | `work/resins/recipes_to_mapping.py` | 配合表から print-aware な optical mapping を作る(体積比の線形混合) | そのまま使える(Step 6 で使う) |
| Mitsuba ステージとビューア | `vdbmat` の `mitsuba_stage*`、ステージのプリセット `stage-print-photo` | 見え方の予測 | 大きな白い部分は path depth 256 以上が要る(report4 の知見) |
| EDT | `vdbmat-utils/src/vdbmat_utils/fields/edt.py` | 表面からの距離 → 色シェルの厚さ | 使える |
