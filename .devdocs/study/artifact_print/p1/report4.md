# artifact_print p1 step 4 report — 手法・計算・ツール調査(Q4)

## Done

- `study/3dprint_artifact/methods_tools.md`: 6 節にまとめた。各項目に、ライセンス、pip で入るか、一言評価を付けた。
  1. メッシュの読み込みと修復(8 ツール)
  2. 形状のボクセル化(11 方式。既存の `voxelize-mesh` を含む)
  3. 色の体積化とハーフトーン(研究 10 本 + 商用 3 つ)。**公開実装の有無**で切り分けた
  4. J850 の色管理
  5. データ取得の自動化(Smithsonian、Sketchfab、Europeana)
  6. 本リポジトリの既存資産の流用判断(ディザ、KM サロゲート、v3、recipes → mapping、Mitsuba、EDT)
- 調査は、Step 1 と同時に起動した sonnet サブエージェント 3 体で行った(研究、ツール、J850)。論文の DOI 8 件は Crossref API で書誌を照合し、
  Cuttlefish と arXiv のページが生きていることも確認した。
- ツールの一部(trimesh、Open3D、manifold3d、pymeshfix、DracoPy)は、Step 2 の非管理 venv に実際に入れてあり、Step 6 で使う。

## Commands

```bash
# 書誌の照合(ACM / Science の DOI リンクは bot 対策で 403 になるので、Crossref を使う)
curl -s "https://api.crossref.org/works/10.1145/2832905"   # ほか 7 件
curl -sL https://arxiv.org/abs/1710.00546 | grep -o "<title>[^<]*"
# pip で入るかの確認(サブエージェントが scratchpad の venv で実施)
uv venv --python 3.12 && uv pip install trimesh open3d pygltflib pymeshfix manifold3d meshlib libigl mesh-to-sdf pysdf pymeshlab
```

## Learned

- **テクスチャ付きメッシュから Stratasys のボクセルスライスまでを通す公開実装は無い**(GitHub、論文の project page、著者のサイトを検索した)。
  研究のコードは、非公開か商用(Cuttlefish)。部品(読み込み、修復、占有判定、最近傍色)は OSS で揃うので、統合は自前になる。
- 本システムにとって最も効く既存の知見は、**KM サロゲートの適用範囲**だった。不透明色では、補正係数で使える。
  半透明(クリアに白を薄く混ぜた配合)では色の形がずれる(ΔE 12〜16)。翡翠や雪花石膏の配合設計は、KM で当たりを付けたうえで、
  Mitsuba での確認と、クーポンでの実測が必須になる。
- **色は元のメッシュから取ればよい**ので、修復で UV を保つ必要は無い。これで、修復の選択肢(manifold3d のレベルセット、voxel remesh)が一気に広がる。
- ライセンスの落とし穴: PyMeshLab は GPL、MeshLib は商用に有償、pymeshfix(MeshFix)は非商用の歴史がある、binvox は非商用。
  次フェーズで社外に出すコードに組み込むなら、manifold3d、trimesh、Open3D、libigl(MPL)を軸にする。
- Mitsuba 3 は微分可能レンダラなので、Nindel ら 2021(勾配による見え方の最適化)の方向は、本システムの延長として自然に来る(長期の候補)。

## Skipped

- 公開実装の有無は、ネット上で見つからなかったことを意味するだけで、存在しないことの証明ではない(methods_tools.md に明記した)。
- 占有判定と最近傍点の問い合わせの実測(10⁹ 規模のスループット)は、Step 6 で行う。
- Cuttlefish の学術ライセンスの有無は未確認(社外への問い合わせになるので、本 phase の範囲外)。
