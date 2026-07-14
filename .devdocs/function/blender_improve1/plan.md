# blender_improve1 実装計画 — 手作りシーンへの PLY + OpenVDB ハイブリッド配置

## 規模判定

この拡張は新しいフェーズやロードマップを必要としない。既存資産として、

- `vdbmat export mitsuba` が生成する外表面 `exterior-*.ply`
- `vdbmat export openvdb` が生成する `volume.vdb` と
  `openvdb-manifest.json`
- `examples/native_fixtures/blender_cycles_volume.py` の Cycles 用
  Volume Absorption / Volume Scatter ノード構成
- `examples/pipeline_run/demo/blender_template_swap.py` のテンプレート展開・
  メッシュ差し替え・レンダー処理
- `.local/local_demo/template_scene/cube_diorama.blend` の手作りシーン

が揃っている。必要なのはこれらの接続とデモ用検証であるため、
単一の function 実装計画として進める。

## 実装状況

- Step 1〜3: 完了。`report1-3.md` 参照。
- Step 4〜6: 完了。`report4-6.md` 参照。
- データ経路・自動配置・再生成・文書化の完了条件は達成。代表 PNG の視認性は
  ユーザー方針により深追いせず、手作りテンプレートの視覚調整とともに別作業とする。
- 完了後補正: 任意モデル差し替えで判明した材質消失・原点差・View Layer 全無効を修正。
  `report7.md` 参照。

## ゴール

3 次元材料 ID 配列から生成した光学ボリュームを、手作りの Blender
シーン内で定性的に確認できるようにする。

1 回の Blender 実行で次の 2 要素を同じアンカーに配置する。

1. `exterior-*.ply` をテンプレート側の Glass BSDF 付き外表面として配置。
2. `volume.vdb` を同一 transform の内部参加媒質として配置し、
   `cycles_absorption` と `cycles_scattering` を Cycles のボリューム密度へ接続。

代表検証は「透明樹脂の外側キューブの中央に黒色不透明樹脂の
小キューブがある」ボクセルモデルとする。

## 非ゴールと表示の性格

- 内部 IOR 境界は Cycles へ渡さない。`ior` グリッドは VDB に残るが
  シェーダーには接続しない。
- `interior-*.ply` は読み込まない。不透明領域や大理石模様は、
  VDB 内の吸収・散乱分布として表示する。
- Cycles 用の RGB 係数は現行 exporter と同じスカラー簡約を用いる。
  Mitsuba との画素一致や物理的同等性は求めない。
- 係数は暫定・未校正である。出力は「qualitative / uncalibrated demo」とする。
- 任意の非一様 scale、shear、個別に動かした PLY/VDB の合成は対象外。

## 実装ステップ

### Step 1 — 入力契約と transform 方針の固定

- テンプレートファイル、Mitsuba export ディレクトリ、OpenVDB
  manifest、出力 PNG を入力とするデモ CLI を定義する。
- 現行の外表面だけのヘルパーは壊さず、新規の
  `examples/pipeline_run/demo/blender_template_hybrid.py` として分離する。
- テンプレートの `--target-object` を配置アンカーとして使い、
  外表面は現行どおり mesh data のみ差し替える。VDB オブジェクトには
  target と同じ `matrix_world` を適用する。
- PLY と VDB が共通のメートル座標系で出力されていることを前提とし、
  VDB に格納済みの index-to-world transform は書き換えない。
- target transform は、回転・並進と一様 scale のみ受理する。
  非一様 scale や shear は PLY/VDB 間の密度・幾何解釈を曖昧にするため
  明示エラーとする。

### Step 2 — テンプレート内への OpenVDB 読み込み

- `openvdb-manifest.json` から VDB パス、`phase_g`、Cycles 設定を読む。
- `bpy.data.volumes.new()` で VDB を開き、グリッドを load した時点で
  `cycles_absorption` / `cycles_scattering` の存在を検証する。
- Volume Absorption と Volume Scatter を Add Shader で結合し、Material Output の
  Volume へ接続する。密度は対応する named grid、散乱の Anisotropy は
  manifest の `phase_g` を使用する。
- ボリュームマテリアルとオブジェクト名は固定し、保存した `.blend`
  で後から追跡できるようにする。

### Step 3 — 外表面とボリュームの同時配置・レンダー

- Mitsuba export ディレクトリの `exterior-*.ply` を列挙する。最初の実装は
  境界全体が同一 IOR のデモを対象とし、1 個だけ受理する。
  0 個または複数個は黙って取捨選択せず、対応外としてエラーにする。
- target の mesh data を PLY と差し替え、テンプレート側の Glass
  マテリアル、transform、collection、名前を維持する。
- VDB オブジェクトを target と同じ collection に link し、同じ transform で
  外表面と重ねる。
- テンプレートのカメラ・照明・解像度・カラー管理は維持し、
  CLI から samples と出力先のみ上書き可能にする。
- PNG のほか、調査可能な `.blend` を任意で保存できるようにする。
- `PIXELSTATS` に加え、読み込んだ VDB 名、grid 名、target 名、一様
  scale をログ出力する。

### Step 4 — 入れ子キューブの決定的デモ入力

- `vdbmat/examples/pipeline_run/` の既存の direct-voxel 契約に合わせ、
  小さな `uint16` の ZYX 配列を生成する。
- 境界を含む全領域を transparent-resin (ID 1)、中央の軸対称な小ブロックを
  black-opaque-resin (ID 3) とする。外表面の全セルが ID 1 であることも
  生成時に検証する。
- voxel manifest、`.npy`、run config を既存の fixture 生成スクリプトから
  再生成可能にし、バイナリの手修正は行わない。
- `vdbmat run` 後の材料カウントを解析値と比較し、その後 Mitsuba と
  OpenVDB の両 export を生成する実行例を用意する。

### Step 5 — テストと実レンダー検証

- Python で検証できる範囲:
  - デモ入力の shape、material count、中央/境界セルの ID。
  - 生成した optical volume の黒コア領域で吸収が大きく、透明領域で
    散乱が 0 であること。
  - OpenVDB manifest と Mitsuba exterior が同じ world bounds を表すこと。
- pinned Docker image `vdbmat-openvdb-cycles:blender4.5.11` で次を検証する:
  - VDB の required grids がロードできる。
  - PLY と VDB の world-space bounds が一致する。
  - Cycles CPU レンダーが正常終了し、PNG と任意の `.blend` を出力する。
  - 低 samples の smoke render で `PIXELSTATS std` が空フレーム相当でない。
- 最終確認では同じ入力を以下の 2 条件でレンダーする:
  1. Glass 外表面のみ。
  2. Glass 外表面 + VDB ボリューム。

  2 でのみ中央の不透明コアが視認できることを目視で確認する。
  画像ハッシュの完全一致は完了条件にしない。

### Step 6 — 利用手順と制約の文書化

- `README_QUICK.md` の手作りシーン節に、次の一連の実行例を追加する:
  direct voxel 入力 → `vdbmat run` → Mitsuba/OpenVDB export → hybrid render。
- Blender 4.5.11 LTS の pinned Docker image を使うこと、`--user` を必須とすること、
  出力が定性・未校正であることを明記する。
- トラブルシューティングとして、外表面だけに見える場合の
  required grids、transform、密度値域の確認方法を記載する。

## 実施順序

Step 1 → Step 2 → Step 3 で最小ハイブリッド表示を成立させる。
Step 4 で代表入力を固定し、Step 5 で end-to-end 検証、Step 6 で使用方法を閉じる。

## 完了条件

- 入れ子キューブの direct-voxel 入力が決定的に再生成できる。
- 入力から optical.zarr、Mitsuba exterior PLY、OpenVDB を連続生成できる。
- 手作りシーンのガラス外表面と VDB ボリュームが同じ位置・回転・
  一様 scale で配置される。
- 透明外殻越しに中央の不透明コアが見える PNG を、pinned Docker
  環境で 1 コマンドの Blender 実行により生成できる。
- 保存した `.blend` を開き、Glass 外表面と VDB 内部媒質を別オブジェクト
  として調査できる。
- 内部 IOR 境界、RGB スカラー簡約、物理校正の非対応が文書に明記される。

## リスクと打ち切り条件

- **VDB の密度スケール**: テンプレートの一様 scale により物理寸法が
  拡大されると、光学厚も変わる。本デモはシーン内サイズを優先し、
  係数を自動補正しない。実寸の光学厚保存が必要になった場合は別機能とする。
- **高吸収領域のノイズ/黒つぶれ**: step size、samples、bounce 設定はデモ
  プリセットで調整する。コアの形が全く判別できない場合のみ、
  デモ用 density multiplier の追加を判断する。デフォルトは 1.0 とする。
- **Cycles の限界**: 内部屈折が必要、または Mitsuba と同等の光輸送が
  必要と判明した場合、本 function はそれを拡張せず Mitsuba 経路を使う。
- **複数 exterior**: 複数外面グループが必要な入力は、配置アンカーと
  Glass 材質の契約を別途設計する。本実装では暗黙に先頭だけを使わない。
