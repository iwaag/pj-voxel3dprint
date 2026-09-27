# artifact_print p1 step 2 report — MVP 候補の選定(Q2)

## Done

- `study/3dprint_artifact/candidates.md`: 選定基準を 6 項目で明文化した(色の複雑さは、k-means で平均 ΔE76 < 6 になる最小の k と、
  k = 6 のときの平均 ΔE で数値化)。**Smithsonian の 10 点**を実際に取得して計測し、**Sketchfab の 9 点**はメタデータだけを記録して、
  最終 3 点を選んだ:
  - **A 染付の水注**(Cooper Hewitt 1986-61-53、CC0): 水密、単一成分、2 系統の色。**Step 6 の対象にする**。
  - **B 塩釉の炻器の水差し**(NMAAHC 2011.61、CC0): 連続階調(ΔE@k6 = 6.3)。穴は小さい。
  - **K 玉璧**(Mia、CC0、半透明)。予備は L(雪花石膏)と M(ヒスイ製勾玉、CC BY)。**Sketchfab の API トークンが無いので未取得。**
- 使い捨てスクリプト(git 管理、`work/artifact_print/`):
  - `fetch_si.py`: Step 1 の API スナップショットから、Smithsonian のファイルを引いて `.local` に保存し、取得ログ(sha256 付き)に追記する。
  - `measure_mesh.py`: 面数、テクスチャ、bbox、水密 / 巻き方向 / 境界辺 / 非多様体辺、連結成分、色の複雑さ。
  - `preview_points.py`: GPU なしで確認するための点群プレビュー(正面、側面、上面)。
- `open_questions.md` を暫定版として作成した(Sketchfab トークン、CC0 表示の確認、単位)。

## Commands

```bash
# 計測用の venv(非管理。vdbmat-utils 側の依存関係は変えない)
uv venv --python 3.12 .local/study/3dprint_artifact/venv
VIRTUAL_ENV=.local/study/3dprint_artifact/venv uv pip install trimesh open3d manifold3d pillow scipy networkx rtree pygltflib DracoPy scikit-image pymeshfix
#   -> trimesh 5.1.0, open3d 0.20.0

python3 work/artifact_print/fetch_si.py 88de08dd:150k-4096.glb ce850625:150k-4096.glb d8c63a70:150k-4096.glb \
  d8c64b96:150k-4096.glb d8c6393a:150k-4096.glb 0dc68216:150k-4096.glb 79da3e3f:150k-4096_std.glb \
  82adf5d6:150k-4096_std.glb 349e8fa2:150k-4096_std.glb 8edffe56:150k-4096.glb
.local/study/3dprint_artifact/venv/bin/python work/artifact_print/measure_mesh.py \
  .local/study/3dprint_artifact/models/si/*/*.glb --json .local/study/3dprint_artifact/docs/measure_si_step2.json
.local/study/3dprint_artifact/venv/bin/python work/artifact_print/preview_points.py <glb> .local/.../shots/step2/si_<pkg>.png

# Sketchfab: 半透明の素材で CC0 / BY の文化遺産を検索(認証なし)
#   q in {jade, nephrite, jadeite, amber, alabaster, rock crystal, glass, marble, agate, 勾玉, ヒスイ, netsuke, celadon}
#   /v3/search?type=models&q=<q>&downloadable=true&license=<cc0|by>&categories=cultural-heritage-history
```

## Learned

- **Smithsonian 3D の美術品はごく一部。** 3,576 パッケージのうち 3,381 件は学名タイトル(自然史)で、美術品・工芸品は約 20 点だった。
  半透明の素材(翡翠、琥珀、雪花石膏、ガラス)は **Smithsonian の直接配信には無い**。半透明枠は Sketchfab に頼ることになり、
  その取得には利用者のトークンが要る。
- **UV の継ぎ目で頂点が分かれているので、水密判定の前に頂点を位置で統合する必要がある。** 統合しないと、10 点すべてが「開いている」と判定された。
  統合後に水密だったのは A、C、J の 3 点。開いている器は、境界辺が 300〜560 本あった(口か底の穴)。
- **GLB の単位が揃っていない。** A、B、D〜G はメートル(glTF の規約どおり)。C と J は mm の桁。H と I は桁から判断がつかない。
  取り込みでは、単位を自動で推定せず、実寸(博物館のメタデータ)から縮尺を決めるべき。
- Figure of a Dancer(J)は、色テクスチャが無く normal map だけだった。「textured」という名前でも色が無いことがある。
- 色の複雑さの目安: 染付(A、D〜F)は k₆ = 4〜7。暗い単色(C、G、I)は k₆ = 2〜3。炻器(B)は k₆ = 7(ΔE@k6 = 6.3)。
  **6 色量子化で平均 ΔE < 6 に収まらない品がある**ことが、計測の段階で見えた。
- A の体積は 447 cm³。外寸 25 cm の水注の中実体積としては小さすぎるので、内外の面を閉じた中空の器と推定される。
  肉厚が薄いと、ボクセル化したときに壁が途切れるおそれがある(Step 6 で確認する)。

## Skipped

- **Sketchfab の候補(K〜S)の実データの取得と計測**: DL に OAuth2 か API トークンが要る。利用者への依頼として `open_questions.md` に記録した。
  `/v3/models/{uid}` の詳細(`textureCount` など)も 429 で取れなかったので、面数は検索 API の値を使った。
- 各オブジェクトの CC0 表示の個別確認(`3d.si.edu` が 403、DEMO_KEY が上限)。
- trimesh / Open3D による修復の試行は Step 6 に回した(plan では Step 2 は判定まで)。
