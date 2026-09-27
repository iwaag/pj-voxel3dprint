# artifact_print p1 step 1 report — データソース調査(Q1)

## Done

- `study/3dprint_artifact/sources.md`: 約 40 ソースを、海外の自前配信(9)、Sketchfab の館アカウント(16)、
  国内(11)、パイプライン検証用(4)に分けて表にした。各ソースに、ライセンス / 商用 / 改変 / クレジットの 4 欄、
  形式、色の種類、取得方法を書いた。末尾で advice.md の 4 分類(美術品 / 骨董考古 / 建築遺跡 / CC0 で商用可)に並べ直した。
- `study/3dprint_artifact/license_notes.md`: CC0 から BY-NC-ND までと館独自規約について、社内検討・社外展示・販売の
  それぞれで何ができるかを表にした。「3D プリントは翻案にあたる」という前提と、ソース固有の注意、
  CC BY 用のクレジットのひな形も入れた。
- 調査は sonnet サブエージェント 4 体で並行して行った(Smithsonian / Europeana / MorphoSource、
  Sketchfab の館アカウント、遺跡系リポジトリと検証用、国内)。主な数値は自分で API を叩いて裏を取った(下記)。
- API のスナップショット(Smithsonian 3D の全ファイル行 41,296 件と、Sketchfab 集計の JSON)を
  `.local/study/3dprint_artifact/docs/api_snapshots/` に保存した(非管理)。

## Commands

```bash
# Smithsonian 3D API: 認証なしで直リンクを返すことを確認し、全件をページング
curl -s "https://3d-api.si.edu/api/v1.0/content/file/search?q=vase"
curl -s "https://3d-api.si.edu/api/v1.0/content/file/search?q=&rows=1000&start=<n>"   # rowCount 41296
# -> パッケージ 3,576、Download3D があるもの 3,496。Full_resolution OBJ zip 約 1,350、Watertight STL 124
curl -sI ".../3d_package:<id>/<name>-150k-2048-medium.glb"   # 200, model/gltf-binary

# Sketchfab: アカウント単位のライセンス内訳(サブエージェント)と、自分での抜き取り確認
curl 'https://api.sketchfab.com/v3/search?type=models&user=britishmuseum&downloadable=true&count=24'
curl 'https://api.sketchfab.com/v3/models?user=WirtualneMuzeaMalopolski&downloadable=true&count=3'
curl 'https://api.sketchfab.com/v3/search?type=models&user=WirtualneMuzeaMalopolski&downloadable=true&license=cc0'
curl 'https://api.sketchfab.com/v3/search?type=models&user=WirtualneMuzeaMalopolski&downloadable=true&license=by'
```

## Learned

- **取得経路が MVP を左右する。** Smithsonian は `3d-api.si.edu` が認証なしで、GLB、OBJ zip、PLY、
  **水密 STL(124 件)** の直リンクを `file_size` 付きで返す。一方、Sketchfab の DL には OAuth2 が必要
  (`/download` は認証なしだと 401)。CC0 の美術品が最も多いのは `artsmia`(DL 可 300 件のうち CC0 207 件)だが、
  そこから落とすには利用者の Sketchfab アカウント(API トークン)が要る。
- **大英博物館は DL 可 179 件のうち 170 件が BY-NC-SA。** 社内検討用にしか使えない。advice.md の「約 260 点」は、
  重複を含む生値の 263 とおおむね合う(uid で重複を除くと約 230〜245)。
- **二次情報の誤りを 1 件つぶした**: 「Virtual Museums of Małopolska は全件 CC0」は誤りで、
  API では CC0 と CC BY が混在していた。ソース単位のライセンス記述は当てにせず、モデル単位で確認することにした。
- `3d.si.edu`(HTML サイト)は当日 403 だったが、API とファイル配信は生きていた。The Met の 2026 年の 3D 公開
  (約 140 点、CC0 との報道)は公式ページが 429 で読めず、二次情報のまま未確認として残した。
- 国内では、中央のポータル(ColBase など)に 3D がほとんど無い。自治体や研究所の Sketchfab(CC BY 4.0 が主流)が
  主な出どころ。**翡翠の実物スキャン**(加曽利貝塚のヒスイ製勾玉、CC BY、約 1.4 万面)がある。
- Sketchfab の `/v3/models/{uid}` は、認証なしで連続 250 回ほど叩くと 429 になる。`archives`(サイズ)は認証なしだと null。
- 3D カラー印刷の研究の公開実装、および「テクスチャ付きメッシュ → Stratasys ボクセルスライス」の OSS は見つからなかった
  (Step 4 用に先行して調べた結果。Step 4 で詳述する)。

## Skipped

- 点数の目安で「未確認」が残ったもの: `clevelandart`、`TheHuntMuseum`、`WirtualneMuzeaMalopolski` の総数、ADS / tDAR の 3D 所蔵、
  ジャパンサーチと文化遺産オンラインの 3D。Małopolska の全件集計は API が遅く途中で止めた(CC0 と BY の混在が分かった時点で十分と判断)。
- The Met の公式ページの確認は、429 のため Step 2 に回した。
- plan は「10〜20 ソース」だったが、Sketchfab の館アカウントと国内を個別に数えた結果、約 40 行になった。
