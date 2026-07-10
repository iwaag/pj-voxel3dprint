ボクセル式インクジェット3dプリンタで透明素材と不透明素材を組み合わせてプリントする前提で、その外観を事前にシミュレートするツールを作りたいです。なんかの事前3次元空間行列計算ツール+blender cyclesあたりで考えているんですが、他に良い提案ありますか？

その構成（ボクセル空間で光学情報を計算 → Cyclesでレンダリング）はかなり筋がいいと思います。ただ、目的が「見た目をできるだけ実機に近づける」なら、Cyclesを最終レンダラとして使うよりも、ボリュームレンダリングエンジンを中心に据える方が精度も実装も良くなる可能性があります。

まず確認ですが、対象は

ボクセル式Material Jetting（Stratasys PolyJet系のような）
透明樹脂と白・黒・カラー樹脂を混ぜる
ボクセル単位（20〜50μm程度）で材料配置が決まる

という前提ですよね。

この場合、本質的には「メッシュ」ではなく**3次元密度場(volume)**です。

案1 ボクセル→OpenVDB→Cycles（おすすめ）

これはお考えの案を少し発展させたものです。

3D CAD

↓

Voxelizer

↓

material voxel grid
(R,G,B,透明度,IOR...)

↓

OpenVDB

↓

Cycles Volume

Cyclesには

Density
Color
Absorption
Scattering

があるので、

各ボクセルから

σa (吸収係数)

σs (散乱係数)

albedo

anisotropy g

へ変換できます。

つまり

「透明樹脂＋白樹脂」

なら

透明部分

σa = 小
σs = 0

白部分

σa = 小
σs = 大

というマッピングだけでかなり近づきます。

メリット

Blender資産が使える
GPU対応
OpenVDB対応
案2 NVIDIA Omniverse + MDL

こちらは業務用途ならかなり魅力があります。

Omniverseは

USD
OpenVDB
MDL(Material Definition Language)

が非常に強いです。

MDLなら

volume absorption

volume scattering

phase function

IOR

まで完全に書けます。

Material Jettingの研究用途なら
Cyclesよりこちらの方が自然です。

案3 Mitsuba3（個人的には一番おすすめ）

もし

「できるだけ実機に合わせたい」

なら、

CyclesよりMitsuba3です。

理由

Mitsubaは研究用レンダラなので

heterogeneous volume

spectral rendering

polarization

multiple scattering

path guiding

全部あります。

しかもPython APIがあります。

例えば

numpy voxel

↓

Mitsuba volume

↓

render

が非常に簡単。

さらに

測定データから

σa

σs

g

を最適化する機能まであります。

論文でもよく使われています。

案4 OSPRay

Intelの

OSPRay

もかなり相性がいいです。

特徴

OpenVDBをそのまま食べられる

医療CT向け

巨大ボリューム高速

CPUだけでも速い

Material Jettingシミュレータには向いています。

案5 独自レイトレーサ

実は最終的にはこれになるケースも多いです。

Cyclesは

「表面」

が得意ですが、

Material Jettingは

光

↓

ボクセル

↓

ボクセル

↓

ボクセル

↓

出射

なので

実際には

for ray:

    while inside:

        voxel取得

        Beer-Lambert

        散乱

        Fresnel

        屈折

        次ボクセル

だけです。

メッシュ不要。

BVH不要。

3D Textureだけ。

CUDAならかなり高速になります。

私ならこう設計します
STEP1

CAD

↓

Voxelizer

↓

Material Grid
STEP2

Material Grid

↓

Optical Property Grid

σa
σs
g
IOR
RGB

ここが最重要です。

STEP3

OpenVDB

↓

Renderer

Rendererは

Mitsuba
Cycles
Omniverse

どれでも差し替え可能。

STEP4

実機と比較

↓

Optical Property補正

↓

Renderer

このループで一致度を上げます。

さらに一歩進めるなら「見た目変換」レイヤーを設ける

実際のインクジェット方式では、ボクセルの材料指定がそのまま光学特性にはなりません。UV硬化や材料混合、界面のにじみなどで実効的な散乱・吸収特性が変わるため、材料IDから直接レンダリングするより、

Material ID Grid
        ↓
Optical Property Converter
        ↓
σa(x,y,z)
σs(x,y,z)
g(x,y,z)
IOR(x,y,z)
        ↓
Renderer

という層を設けておくと、実機測定からパラメータを校正でき、レンダラを入れ替えても資産を流用できます。

もし私がゼロから設計するなら、「ボクセル光学シミュレータ」をコアにして、表示バックエンドとして Blender Cycles や Mitsuba3 を選べる構成にします。特に Mitsuba3 + OpenVDB + NumPy の組み合わせは、ボクセルごとの散乱・吸収・屈折率を物理ベースで扱え、後から実測値で校正しやすいため、透明・不透明材料を組み合わせたインクジェット3Dプリントの外観予測には非常に相性が良いと思います。

では描画系は後で考えるとして、共通の事前計算バックエンドの設計と実装方針を大まかに作成してください。具体的実装ステップなどは後で改めて詳細化しますので、技術スタックやロードマップを重視してください。

前提を「描画エンジン非依存の、材料ボクセル→光学ボリューム変換バックエンド」と置いて整理します。実装詳細より、後でCycles/Mitsuba/Omniverse等へ吐き出せる中間表現を中心にします。

Thought for 6s

以下の方針がよいです。

基本設計

描画系から独立した中核を、Voxel Optical Preprocessor として作ります。

CAD / mesh / slice data
        ↓
voxel material grid
        ↓
process simulation
        ↓
optical property volume
        ↓
renderer export

重要なのは、材料IDを直接レンダラへ渡さず、

material voxel
→ effective optical voxel

へ変換する層を持つことです。

中間表現

内部データは最低限これです。

material_id[x,y,z]
fill_ratio[x,y,z,material]
surface_distance[x,y,z]
sigma_a[x,y,z,λ]
sigma_s[x,y,z,λ]
anisotropy_g[x,y,z]
ior[x,y,z]

透明・不透明の見た目は、主に

吸収 σa
散乱 σs
屈折率 IOR
界面粗さ
材料混合/にじみ

で決まります。

推奨技術スタック
コア
Python：実験、パイプライン制御
NumPy / SciPy：初期実装
Numba or CuPy：高速化
Rust or C++：後の本実装候補
ボリューム保存
Zarr：開発中の主フォーマット
チャンク化・圧縮されたN次元配列に向いています。
OpenVDB：レンダラ渡し用
疎な3Dボリュームの業界標準的な形式です。
NanoVDB：GPU処理・将来のリアルタイム用途
OpenVDBをGPUで扱いやすくする位置づけです。
外部連携
OpenUSD / UsdVol：将来のOmniverse、Hydra、DCC連携用
USDはVolumeスキーマでOpenVDB等の体積データを扱えます。
アーキテクチャ
1. Input Layer
   - STL / OBJ / STEP-derived mesh
   - printer voxel data
   - material palette

2. Voxelization Layer
   - solid voxelization
   - shell/interior classification
   - support for anisotropic voxel size

3. Print Process Model
   - droplet spread
   - material mixing
   - curing shrinkage
   - interface blur
   - halftoning / dithering simulation

4. Optical Mapping Layer
   - material ratio → σa
   - material ratio → σs
   - material ratio → IOR
   - spectral or RGB approximation

5. Volume Optimization Layer
   - chunking
   - sparse conversion
   - mipmap / LOD
   - boundary extraction

6. Export Layer
   - Zarr
   - OpenVDB
   - NanoVDB
   - USD + VDB reference
ロードマップ
Phase 1：研究用MVP

目的は「透明/白/黒の組み合わせがそれっぽく見える」こと。

Python + NumPy
dense voxel grid
Zarr保存
材料ID → σa/σs/IOR の固定変換
小型サンプルのみ対象

この段階では物理精度より、パイプラインの形を固めます。

Phase 2：実機寄せ
キャリブレーション用テストピースを印刷
透過率、反射率、濁り、内部視認性を測定
材料ごとの実効光学係数を推定
interface blur / material bleeding を導入

ここで「材料ライブラリ」を作ります。

Phase 3：大規模化
OpenVDB出力
チャンク処理
sparse volume化
LOD生成
並列処理

この段階で、実サイズの造形物を扱えるようにします。

Phase 4：レンダラ非依存化
Cycles用VDB
Mitsuba用volume
Omniverse/USD用VDB
独自GPUレイトレーサ用NanoVDB

描画系を差し替え可能にします。

Phase 5：予測精度向上
波長別スペクトル処理
異方性散乱
表面粗さモデル
UV硬化・収縮モデル
実測値による逆推定
最初に決めるべき設計判断

一番重要なのは、内部表現を

材料IDベース

ではなく、

光学物性ベース

にすることです。

つまり最終的な共通バックエンドの成果物は、

「このボクセルは透明樹脂」

ではなく、

「このボクセルの吸収係数・散乱係数・屈折率はこれ」

であるべきです。

結論としては、開発中はZarr、レンダラ連携はOpenVDB、GPU/将来用途はNanoVDB、DCC連携はUSD という構成が最も堅いです。

これって一つのモジュール、一つのリポジトリにまとめれる話ですか、複数のモジュールに分けるべき話ですか？

最初は1リポジトリのモノレポ、中身は複数モジュールに分けるのがよいです。

voxel-optics/
  core/              # 共通データ構造・座標系・単位系
  io/                # STL, OBJ, Zarr, OpenVDB, USD export
  voxelize/          # メッシュ→材料ボクセル
  process_model/     # にじみ、混合、硬化、界面ぼかし
  optics/            # 材料比→σa, σs, g, IOR
  calibration/       # 実測値から係数推定
  pipeline/          # 一連の処理 orchestration
  cli/               # コマンドライン
  examples/
  tests/

理由は、これは「一つの処理」ではなく、

形状処理
材料配置
プリントプロセス近似
光学物性変換
フォーマット出力
キャリブレーション

という別関心の集合だからです。

ただし、初期から別リポジトリに分けるのはおすすめしません。インターフェースが固まる前に分割すると、変更コストが高くなります。

おすすめの進め方はこうです。

Phase 1
1 repo / 1 Python package / 内部だけモジュール分割

Phase 2
1 repo / 複数 package化
例:
  voxel_optics_core
  voxel_optics_io
  voxel_optics_calibration

Phase 3
必要なものだけ別repo化
例:
  nanovdb exporter
  blender plugin
  calibration lab tools

特に分離すべき境界はここです。

core        : 絶対に軽く保つ
io/export   : 依存が重いので分ける
renderer    : 後で別repoでもよい
calibration : 実験データ依存なので分けてもよい

結論としては、プロジェクトとしては1つ、実装単位としては複数モジュールがベストです。最初はモノレポで始めて、OpenVDB/USD/Blender連携のような重い依存だけ後から外に出す設計が安全です