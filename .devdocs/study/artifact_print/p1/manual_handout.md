# artifact_print p1 — 人の作業が必要なこと(manual handout)

p1 の調査では、自動では進められない作業をすべて飛ばしてここにまとめた。上から順に優先度が高い。
各項目の「結果の置き場」に書いてもらえれば、次のセッションでそこから続けられる。

## A. 利用者(このリポジトリの担当者)の作業

### A1. Sketchfab の API トークン(半透明の候補の取得)【優先度: 高】

- **なぜ**: 半透明枠の候補(玉璧、雪花石膏の喪服像、ヒスイ製勾玉)は Sketchfab にしか無く、DL にはログインが必要
  (`/v3/models/{uid}/download` は認証なしだと 401)。Smithsonian の直接配信には、半透明の素材の美術品が無かった。
- **手順**: Sketchfab にログイン → Settings → Password & API → API token をコピー。
  `.local/study/3dprint_artifact/sketchfab_token.txt`(非管理)に 1 行で保存する。**git 管理のファイルやチャットには貼らない。**
- **対象**(uid): `d763ec3d9b9c487fa1c6770ed80829cf`(玉璧、CC0)、`0d89139b17024e378f2882e575531e08`(喪服像、CC0)、
  `0f9fe38a1e424a47a77f8b1f8a3e4efb`(ヒスイ製勾玉、CC BY)。
- **結果の置き場**: トークンのファイルがあれば、Claude が DL し、`measure_mesh.py` で計測して `candidates.md` を更新する。

### A2. (任意)api.data.gov の API キー【優先度: 低】

- **なぜ**: Smithsonian Open Access API で、候補 A と B の CC0 表示(`metadata_usage`)と実寸を確かめるため。
  DEMO_KEY は、調査中に上限に達した。`3d.si.edu` の個別ページを、ブラウザで目視確認するのでもよい。
- **手順**: https://api.data.gov/signup/ で取得し、`.local/study/3dprint_artifact/api_data_gov_key.txt` に保存する。
  目視で確認する場合は、下の 2 ページで「CC0」の表示を確かめ、結果を `open_questions.md` に書く。
  - 候補 A: `3d.si.edu` で「1986-61-53」(Cooper Hewitt の水注)を検索
  - 候補 B: `3d.si.edu` で「2011.61」(Thomas Commeraw の炻器の水差し)を検索

### A3. Step 6 のスライスの Voxel Print Utility への試し投入【優先度: 中】

- **なぜ**: 本 phase は印刷しない方針だが、**数千枚(3,920 枚)の PNG を Utility が実用的な時間で読めるか**は、実機でしか分からない。
  batch1 は最大 358 枚だった。印刷までは不要で、GCVF ができるところまででよい。
- **ファイル**: `.local/study/3dprint_artifact/step6/slices/ewer60-0p1-k8-km-mesh/`(60 MB。材料対応メモも同じフォルダにある)。
  樹脂の対応は batch1 と同じ(1 白、2 黒、3 クリア、4 シアン、5 マゼンタ、6 イエロー)。
- **結果の置き場**: 取り込みにかかった時間、エラーの有無、GrabCAD の見積もり(造形時間、樹脂量)を `open_questions.md` に書く。

## B. プリンタのオペレータに聞くこと

`study/3dprint_artifact/open_questions.md` の「プリンタのオペレータに聞くこと」節に全項目がある。特に重要なもの:

1. **7 つのスロットに今なにが入っているか**(VeroVivid か旧 Vero カラーか、白と黒は Ultra か、7 本目は何か)。配合の設計の前提になる。
2. **可溶性サポート(SUP706B)が使えるか**。器の内側の空洞のサポートを除去するのに要る。
3. **High Quality で 60 mm の器 1 個の造形時間と費用**(GrabCAD の見積もり画面の値でよい)。
4. **光沢と艶消しの選択**と、それが色の見え方にどう影響するか(見本があれば写真)。
5. **GrabCAD Print の通常フルカラー**(テクスチャ付きの OBJ / 3MF)で刷った経験。色が何 mm の深さまで付くか。
6. 社内に **分光測色計か、色票を撮影できる環境**があるか。

**結果の置き場**: `open_questions.md` の各項目にチェックを入れ、答えと日付を書く。

## C. 次フェーズで人の判断が要ること

- **実機で比べるか**: 水注(60 mm)を、GrabCAD の通常フルカラーと本システムの MVP の 2 通りで刷って比べることを、次フェーズの最初の項目として提案している
  (`study/3dprint_artifact/README.md` の「次フェーズ」)。印刷と材料の予算、プリンタの時間の確保が必要。
- **ライセンスの運用**: 社外展示や販売を視野に入れるなら、法務の確認の手順を決める(`license_notes.md`)。
  NC 付き(大英博物館など)を社内の研究開発で使ってよいかの判断も含む。
- **社外への問い合わせ**: Fraunhofer Cuttlefish のデモや学術ライセンス、Stratasys への Voxel Print の上限(画像サイズ、枚数)の確認。
  本 phase の範囲外として保留している。
