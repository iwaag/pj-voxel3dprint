# artifact_print p1 step 6 report — 小規模フィジビリティ実験(Q3 の裏取り)

対象: 候補 A **染付の水注**(Cooper Hewitt 1986-61-53、Smithsonian 3D、CC0 とみなす)。Low_resolution GLB(15 万面、4096² テクスチャ)を使い、
**最長辺 60 mm、正立(glTF の +Y を造形の +Z に)**で、印刷はせず、GrabCAD Voxel Print 用のスライス PNG の生成まで通した。
中間生成物はすべて `.local/study/3dprint_artifact/step6/`(非管理)。

**計測条件の注意**: 実験の間、同じマシンで利用者の別の重い計算が走っていた(CPU / GPU)。所要時間は負荷のある状態での参考値。

## Done

使い捨てスクリプト(`work/artifact_print/`、git 管理):

| スクリプト | 役割 |
|---|---|
| `prep_mesh.py` | GLB → 頂点を位置で統合 → 正立 → 最長辺 N mm に縮尺 → STL と変換行列(色を引くときに元のメッシュへ戻すため) |
| `occupancy_o3d.py` | Open3D `RaycastingScene.compute_occupancy` による、セル中心の占有判定(`voxelize-mesh` と同じ格子の規約) |
| `shell_colour.py` | 表面から N mm のシェル → 最近傍の表面点の UV → テクスチャ色 → CIELAB で k-means → 意味ラベル → KM サロゲートでラベルごとの 6 樹脂配合(`--mode pure` は、最も近い単一樹脂 = plan の「6 色量子化」)。voxels、resin-recipes(batch1 形式)、semantic mapping、色の報告を書き出す |
| `export_dither_slices.py` | batch1 の fur の 3D ハッシュディザを移植。1 スライスずつ、プリンタピッチで書き出す。形状は、粗いラベルの最近傍(`coarse`)か、**STL をプリンタピッチで直接占有判定**(`mesh`)。RGBA PNG、マニフェスト、材料対応メモ |
| `stack_front_view.py` | 書き出した PNG の束から、正面から最初に当たる樹脂の色を並べて、正面図を再構成する(スライスの検証用) |

結果:

1. **読み込みと修復**: 修復は不要だった(頂点を統合したあとで、水密、巻き方向が一貫、単一成分)。60 mm で 60.0 × 32.8 × 54.9 mm、体積 6,083 mm³。
   **推定の壁厚は 1.5 mm**(2V/A)。断面(`preview-slices`)で、中空の器(壁は 2〜3 セル)であることを確認した。
2. **形状のボクセル化(0.5 mm)**:
   - Open3D: 93 万点を 0.3 s で判定。占有 48,698 セル × 0.125 mm³ = 6,087 mm³ で、メッシュの体積(6,083)と 0.1 % で一致。
   - 既存の `voxelize-mesh`(密な参照実装): **57 分たっても終わらなかった**(下記の Skipped)。
   - 0.1 mm にしても、Open3D なら 1.1 億点を 10.6 s(ピークのメモリ 10 GB)で判定できた。`voxelize-mesh` の上限(1 軸 128 セル、総数 200 万)を大きく超える。
3. **色の体積化と意味ラベル**(k = 8):
   - 0.5 mm 格子、シェル 1.0 mm: シェル 42,807 セル、2.0 s。
   - 0.1 mm 格子、シェル 0.5 mm: シェル 386 万セル、41.7 s。
4. **配合**: KM で逆に解いた配合の予測色と、クラスタの色との差は、ボクセル加重の平均で **ΔE76 = 3.4**(0.1 mm では 3.35)。最大は 6.7(褐色の汚れ)。
   **純色の樹脂を割り当てる方式(plan の 6 色量子化)では、平均 ΔE = 14.4〜16.1、呉須の中間の青で最大 44**。
   白い釉は「クリア」、呉須は「シアン」に割り当てられた。
5. **既存の `export-print-slices` を通した確認**(k = 5 + 芯 = 6 材料、パレットはクラスタの色): 通った。
   4,000 スライス、1,441 × 402 px、61.0 × 34.0 × 56.0 mm(パディングの 1 セルを含む)、色数の検査にも合格。**958 s**。
   ただし、これは「6 つの意味ラベルを 6 色で塗った」ものであり、樹脂の配合は表していない(Step 3 の結論どおり)。
6. **プリンタピッチのディザ書き出し**(形状は STL を直接判定、14 µm):
   - 1,418 × 388 px × 3,920 層 = **21.6 億ボクセル**。
   - 0.5 mm ラベルのとき **106 s**(占有 45 s、PNG 46 s)、ピークのメモリ 417 MB、ディスク 65 MB。
   - 0.1 mm ラベルのとき **137 s**、ピークのメモリ 6.0 GB(ラベルの配列と最近傍のインデックス)、60 MB。
   - 樹脂の画素数の合計(1.21 億)× 画素の体積(5.02 × 10⁻⁵ mm³)= 6,087 mm³ で、メッシュの体積と一致する。
7. **スライスの見た目**(`stack_front_view.py` の正面図、`.local/.../step6/step6-compare-front.png`):
   0.5 mm ラベルでは、絵付けが **0.5 mm のモザイク**になった。**0.1 mm ラベルでは、人物、花紋、格子文までが読める**。
   純色の樹脂の方式では、地がクリア、絵がシアンになる。
8. **v3 ライブラリでのレンダ**(0.5 mm ラベル、Mitsuba、depth 256、spp 128、640²、`.local/.../step6/step6-render-km-vs-pure.png`):
   - 純色の樹脂: 地がクリアになり、ガラスの器のように透ける。絵はシアン。「染付」には見えない。
   - KM の配合: 絵の青の位置は正しい。**白い地が黄緑に寄り**(取っ手の中央値は sRGB で約 (184, 186, 166))、黄色い輝点(firefly、最大値 627)が多い。
     depth を 1024 に上げても平均は変わらなかった(0.42051 → 0.42052)ので、経路の打ち切りではない。
     原因は、KM と Mitsuba の白の食い違い(p2 report4 で、白の厚い板を Mitsuba で描くと 0.516 / 0.443 / 0.304 と暖色に出ていた)と推定する。
     KM で解いた配合は、Mitsuba でも実物でも、白が中立に出る保証が無い。

## Commands

```bash
P=.local/study/3dprint_artifact/venv/bin/python; E=.local/study/3dprint_artifact/step6
G=.local/study/3dprint_artifact/models/si/349e8fa2/chsdm-1986_61_53-ewer-master_model-20230112-150k-4096_std.glb
$P work/artifact_print/prep_mesh.py $G $E/ewer60 --longest-mm 60          # STL sha256 1171b525…
(cd vdbmat-utils && uv run vdbmat-utils voxelize-mesh $E/ewer60.stl --config $E/mesh.json --out $E/vox --name ewer60-geom)  # 57 分で打ち切り
$P work/artifact_print/occupancy_o3d.py $E/ewer60.stl $E/vox_o3d ewer60-geom --pitch-mm 0.5        # 0.3 s
$P work/artifact_print/occupancy_o3d.py $E/ewer60.stl $E/vox_o3d ewer60-geom-0p1 --pitch-mm 0.1    # 10.6 s
$P work/artifact_print/shell_colour.py $E/vox_o3d/ewer60-geom.voxels.json $G $E/ewer60.transform.json $E/sem ewer60-k8-km --k 8 --shell-mm 1.0 --mode km
$P work/artifact_print/shell_colour.py ... ewer60-k8-pure --mode pure
$P work/artifact_print/shell_colour.py $E/vox_o3d/ewer60-geom-0p1.voxels.json ... ewer60-0p1-k8-{km,pure} --k 8 --shell-mm 0.5
$P work/artifact_print/shell_colour.py ... ewer60-k5-km --k 5
(cd vdbmat-utils && uv run vdbmat-utils export-print-slices $E/sem/ewer60-k5-km.voxels.json --config $E/print-slices-k5.json --out $E/slices --name ewer60-k5-existing)
(cd vdbmat-utils && uv run vdbmat-utils preview-slices $E/sem/ewer60-k5-km.voxels.json --axis z --index 60)
$P work/artifact_print/export_dither_slices.py $E/sem/ewer60-k8-km.voxels.json $E/sem/ewer60-k8-km.resin-recipes.json $E/slices ewer60-k8-km-mesh --geometry mesh --stl $E/ewer60.stl
$P work/artifact_print/export_dither_slices.py $E/sem/ewer60-0p1-k8-km.voxels.json ... ewer60-0p1-k8-km-mesh --geometry mesh --stl $E/ewer60.stl
$P work/artifact_print/stack_front_view.py $E/slices/<name> $E/<name>
# レンダ(v3)
vdbmat/.venv/bin/python work/resins/recipes_to_mapping.py --library work/resins/vero-j850-provisional-v3.json \
  --recipes $E/sem/ewer60-k8-km.resin-recipes.json --semantic $E/sem/ewer60-k8-km.optical-mapping.json --out $E/sem/ewer60-k8-km.print-aware.optical-mapping.json
vdbmat/.venv/bin/vdbmat import-voxels --overwrite $E/sem/ewer60-k8-km.voxels.json $E/render/ewer60-k8-km-material.zarr
vdbmat/.venv/bin/vdbmat convert --overwrite --mapping-file ... $E/render/ewer60-k8-km-material.zarr $E/render/ewer60-k8-km-optical.zarr   # 81 s
work/compare/render_stage.sh $E/render/ewer60-k8-km-optical.zarr $E/render/ewer60-k8-km-front.png --stage-config $E/render/ewer-front.stage.json  # 530 s(pure は 674 s)
# stage: stage-print-photo 1.4.0 に、camera az -60 / el 20 / dist 3.0、640²、spp 128、depth 256
```

## Learned

- **MVP ルートは成立する。** 色つきスキャンから Voxel Print 用のスライスまでの全段が、使い捨てスクリプトと既存の資産
  (batch1 のディザ、KM、recipes → mapping、Mitsuba)だけで通った。**負荷のある状態でも 60 mm の器 1 個が約 3.5 分**
  (占有 10 s + 色 42 s + 書き出し 137 s、0.1 mm ラベルの場合)。Step 3 の見積もり(数日)の内訳のうち、実装の手間はほぼこの実験で済んだ。
  **残る課題は、色の正しさ(配合と校正)**。
- **既存の `voxelize-mesh` は、テクスチャ付きスキャンには実用にならない**(15 万面 × 93 万セルで 57 分以上)。Open3D なら 0.3 s。
  次フェーズで本体に入れるなら、Embree 系の占有判定か、巻き数判定をベクトル化した実装に置き換える必要がある。
- **色のラベル格子は 0.1 mm 程度まで細かくする必要がある。** 60 mm に縮小した染付の絵付けは、0.5 mm ではモザイクになる。
  形状は STL を直接プリンタピッチで判定するので、階段状にはならない(「二段構え」が効いた)。
- **plan の「6 色量子化」は、数値でも見た目でも不可**(ΔE 14〜16、地がガラス状になる)。Step 3 の結論を裏付けた。
- **KM で逆に解いた配合は、Mitsuba では白が黄緑に寄る。** 不透明な白が支配的な陶磁器では、これが最大の誤差源になる。
  次の手は次の 2 つ:
  (1) 配合を Mitsuba で補正する(p2 と同じ `c_r` 方式で、ラベルごとにレンダ → 補正 → 再フィットを 1〜2 周)。
  (2) 白の樹脂を実測で校正する(クーポン)。v3 は写真へのフィットで、白の色味は ±15〜20 % の露出の不確かさの中にある。
- 中空の器の縮小: 60 mm で壁は約 1.5 mm。空洞はサポート材で埋まるので、口から除去することになる(可溶性サポートが望ましい)。
  これより小さくすると壁が 1 mm を切るので、縮尺の下限は壁厚で決まる。
- 意味ラベルの数は 6 に縛られない(今回は 9 = 芯 + 8)。1 スライスあたりの色数は、物理樹脂の 6 で、制約に合っている。

## Skipped

- **既存の `voxelize-mesh` の完走**: 57 分(CPU 100 %)で終わらず、打ち切った。Open3D の結果との一致の比較はしていない
  (体積はメッシュと 0.1 % で一致したので、Open3D 側の正しさは別に確かめられている)。負荷のある状態での値。
- レンダは 0.5 mm ラベルだけ(0.1 mm は `vdbmat convert` の体積が 125 倍になるので省いた)。
  KM の配合を Mitsuba で補正するループ(上記の (1))は、次フェーズに回した。
- plan の「実データの修復」は、候補 A が水密だったので不要だった。開いた器(候補 B、D〜F)の修復は試していない。
- 半透明の候補(玉璧など)は、Sketchfab のトークンが無いので未実施(`manual_handout.md` に回す)。
- スライスの Voxel Print Utility への投入(人の作業。`manual_handout.md` に回す)。
