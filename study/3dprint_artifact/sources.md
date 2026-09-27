# データソース一覧(Q1)

> 調査日: 2026-09-27(artifact_print p1 Step 1)。件数は当日の API / サイトで数えたもの。
> 「未確認」は、その日に一次情報で裏が取れなかった項目。ライセンスは **ソース単位の傾向**で、
> 実際に使うときは必ずモデル単位で確認する(同じアカウントでも混在するため)。

## 結論(先に)

- 世界の名品を一か所で横断検索・取得できる単一 DB は無い。実データは
  **Smithsonian 3D(自前配信)** と **Sketchfab 上の博物館公式アカウント** の二本柱で、
  Europeana などの横断ポータルはメタデータだけで、ファイルは Sketchfab を指している。
- **色つき + ダウンロード可 + CC0** の三条件を満たす量が多いのは次のとおり:
  Smithsonian 3D(約 3,500 パッケージ。全館 CC0 方針)、Minneapolis Institute of Art
  (Sketchfab の DL 可 300 件のうち CC0 が 207 件)、Cleveland Museum of Art、
  Rijksmuseum van Oudheden(Leiden)、Musée Saint-Raymond、SMK、Hunt Museum、
  Virtual Museums of Małopolska(CC0 と CC BY が混在)。
- **大英博物館**の Sketchfab は約 240 件、うち DL 可は 179 件だが、その **95 % が CC BY-NC-SA**。
  社内検討には使えるが、展示・販売には使えない。
- **取得経路の違いが MVP の効率を左右する。** Smithsonian は `3d-api.si.edu` が
  **認証なし**で GLB / OBJ zip / PLY / 水密 STL の直リンクを返す。Sketchfab は検索と
  メタデータまでは認証なしで取れるが、**ダウンロードには OAuth2(利用者アカウント)が要る**。
- 遺跡・建築(Open Heritage 3D / CyArk)は 1 サイト平均で約 25 GB あり、机上サイズの MVP には向かない。
  Scan the World と threedscans は **STL(色なし)**なので、色の検証には使えない。

## 一覧表

凡例: 種別 = 美術品 / 骨董考古 / 建築遺跡 / 自然史 / 検証用。色 = UV(UV テクスチャ)、
VC(頂点色)、PBR(PBR マテリアル)、なし。4 欄 = ライセンス / 商用 / 改変 / クレジット。

### 海外・自前配信

| 名前 | URL | 種別 | 点数の目安(確認方法) | 配布形式 | 色 | ライセンス | 商用 | 改変 | クレジット | 取得方法 | 備考 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Smithsonian 3D | https://3d.si.edu/ , API https://3d-api.si.edu/api/v1.0/content/file/search | 自然史 + 美術品 + 歴史資料 | ファイル 41,296 件、パッケージ 3,576 件。うち Download3D があるものが 3,496 件(API を全件ページングして集計) | Download3D: Full_resolution OBJ zip(約 1,350)/ PLY(約 2,100)、Low_resolution GLB・glTF zip・OBJ zip、USDZ、**Watertight STL(124)**。Web3D: Draco 圧縮 GLB(Thumb / Low / Medium / High / AR) | UV(ファイル名の例: `textured-150k-4096`)。PLY の多くは CT 由来で色なし | CC0(Smithsonian Open Access の方針)。**API のファイル行にはライセンス欄が無い**ので、オブジェクトごとの CC0 表示は未確認 | 可(CC0) | 可 | 不要 | API で直リンク、**認証不要**。`rows`/`start` でページング可 | 当日 `3d.si.edu`(HTML サイト)は 403 だったが、API とファイル配信は 200。`q=` の全文検索は効くが、形式や品質での絞り込みパラメータは効かない。自然史標本が多数派 |
| The Met(2026 年の 3D 公開) | https://www.metmuseum.org/press-releases/3-d-models-announcement-2026 | 美術品 | 約 140 点(二次情報。公式ページは当日 429 で読めず) | GLB / USDZ / FBX(二次情報) | UV(二次情報) | CC0(二次情報) | 未確認 | 未確認 | 未確認 | 各作品ページから DL(未確認) | Sketchfab の `metmuseum` アカウントは公開モデル 0 件。Step 2 で公式ページを再確認する |
| Europeana(3D) | https://api.europeana.eu/record/v2/search.json (`qf=TYPE:3D`) | 混在 | 13,474 件(demo key で検索して確認) | ファイルは持たず、提供元(多くは Sketchfab の oEmbed)へのリンクのみ | 提供元しだい | 項目ごとに混在 | 項目しだい | 項目しだい | 項目しだい | メタデータは API、実体は提供元 | 横断検索の入口としては使えるが、取得は提供元に行く |
| MorphoSource | https://www.morphosource.org/ | 自然史が中心(文化財はわずか) | 未確認(API `GET /api/media` は鍵なしで 200) | CT 由来メッシュ、フォトグラメトリ | 多くは色なし | 項目ごとの利用規約(Use Agreement) | 項目しだい | 項目しだい | 多くは要 | メタデータは API、DL は多くがログインと規約同意が必要 | 優先度は低い |
| Open Heritage 3D / CyArk | https://openheritage3d.org/ , https://www.cyark.org/ | 建築遺跡 | 数十〜数百サイト(未確認) | LiDAR 点群、フォトグラメトリのメッシュ | 写真由来の RGB。ありなしはデータセットによる | CC(データセットごと。NC 付きが多いとの情報あり、未確認) | データセットしだい | データセットしだい | 要(DOI) | フォームに記入すると DL リンクがメールで届く | FAQ では平均約 25 GB / サイト。MVP には不向き |
| Scan the World(MyMiniFactory) | https://www.myminifactory.com/scantheworld | 美術品(彫刻) | 数千(未確認) | **STL** | **なし** | CC0 / CC BY / CC BY-NC が混在 | 項目しだい | 項目しだい | 項目しだい | 手動 DL | 形状の検証用にはなるが、色は無い |
| threedscans.com | https://threedscans.com/ | 美術品(彫刻) | 未確認 | STL / OBJ | なし | パブリックドメインとの表示(未確認) | 可(未確認) | 可(未確認) | 不要(未確認) | 手動 DL | 色なし |
| Zenodo | https://zenodo.org/ | 骨董考古 | 散在(例: records/21728247, 13772922) | OBJ / GLB / E57 | 一部は UV | 項目ごと(CC BY から CC BY-NC-ND まで) | 項目しだい | 項目しだい | 要 | 手動 DL、ログイン不要 | 1 件ずつ当たる必要がある |
| Archaeology Data Service / tDAR | https://archaeologydataservice.ac.uk/ , https://www.tdar.org/ | 骨董考古 | 未確認 | 未確認 | 未確認 | 寄託ごと | 未確認 | 未確認 | 未確認 | 未確認 | 今回の Web 検索だけでは、色つき 3D の所蔵を確かめられなかった |

### Sketchfab 上の博物館公式アカウント

件数は Sketchfab Data API v3 の `/v3/search?type=models&user=<name>` を全件ページングし、
uid で重複を除いて数えた(カーソルが重複を返すため 5〜10 % の揺れがある)。
DL 可の内訳は `downloadable=true` と `license=<slug>` の組み合わせで数えた。
共通事項: 色は UV / PBR。形式は API 経由だと glTF zip / GLB(+ USDZ)。
**DL には OAuth2 が必要**(`/v3/models/{uid}/download` は認証なしだと 401)。

| アカウント | 館 | 種別 | 総数 | DL 可 | DL 可のライセンス内訳 | 商用 | 改変 | クレジット | 備考 |
|---|---|---|---:|---:|---|---|---|---|---|
| `artsmia` | Minneapolis Institute of Art | 美術品 + 骨董 | 315 | 300 | CC0 207 / BY-SA 69 / BY-NC-SA 20 / BY-NC-ND 2 / BY 1 | CC0 分は可 | CC0 分は可 | CC0 分は不要 | 翡翠、根付、七宝など。**CC0 の美術品が最も多い** |
| `clevelandart` | Cleveland Museum of Art | 美術品 | 未確認(抽出 4 件はすべて CC0) | 多数 | CC0 中心 | 可 | 可 | 不要 | 雪花石膏の小像がある |
| `Smithsonian` | Smithsonian Institution | 混在 | 151 | 150 | CC0 | 可 | 可 | 不要 | 本体の 3d.si.edu の方が多い |
| `rmo_leiden` | Rijksmuseum van Oudheden | 骨董考古 | 48 | 47 | CC0 44 / BY 5 | 可 | 可 | CC0 分は不要 | |
| `museesaintraymond` | Musée Saint-Raymond(トゥールーズ) | 骨董考古(古代ローマ彫刻) | 34 | 34 | CC0 31 / BY 3 | 可 | 可 | CC0 分は不要 | |
| `smkmuseum` | SMK(デンマーク国立美術館) | 美術品 | 9 | 9 | CC0 9 | 可 | 可 | 不要 | |
| `TheHuntMuseum` | Hunt Museum | 美術品 + 骨董 | 未確認 | 未確認 | CC0 あり | CC0 分は可 | 可 | 不要 | 水晶の聖遺物胸像がある |
| `WirtualneMuzeaMalopolski` | Virtual Museums of Małopolska | 美術品 + 骨董 + 民俗 + 技術史 | 報道では 2,000 点以上(未確認) | 多数 | **CC0 と CC BY が混在**(両方とも検索で 24 件以上ヒット) | 可 | 可 | BY 分は要 | 二次情報の「全件 CC0」は誤り。モデル単位での確認が必要 |
| `fitzwilliammuseum` | Fitzwilliam Museum | 美術品 + 骨董 | 153 | 127 | BY 110 / BY-NC 6 / BY-NC-ND 1 | BY 分は可 | BY 分は可 | 要 | |
| `harvardartmuseums` | Harvard Art Museums | 美術品 | 48 | 33 | BY 32 / BY-NC 2 | BY 分は可 | 可 | 要 | |
| `britishmuseum` | British Museum | 骨董 + 美術品 | 約 230〜245(ページングの生値は 263) | 179 | **BY-NC-SA 170** / BY 6 / BY-NC 3 | ほぼ不可 | 可(SA 継承) | 要 | advice.md の「約 260 点」は、重複を含む生値としてはおおむね合う |
| `GlobalDigitalHeritage` | Global Digital Heritage | 骨董考古 + 建築遺跡 | 5,000 以上(自己申告) | 多数 | BY-NC(未確認) | 不可 | 可 | 要 | |
| `nationalmuseumsscotland` | National Museums Scotland | 混在 | 259 | 6 | BY 2 / BY-NC-ND 4 | ほぼ不可 | ほぼ不可 | 要 | |
| `HornimanMuseum` | Horniman Museum | 混在 | 16 | 16 | BY-NC-ND 16 | 不可 | 不可 | 要 | |
| `ArtInstituteChicago` | Art Institute of Chicago | 美術品 | 4 | 2 | BY 2 | 可 | 可 | 要 | |
| `vamuseum` / `KunsthistorischesMuseumWien` / `NationalPortraitGallery` | V&A / KHM / NPG | 美術品 | 26 / 26 / 19 | 0 | — | — | — | — | 閲覧のみ |

Sketchfab 全体の補足:

- 2020 年 2 月に、Sketchfab 上で文化遺産の CC0 化が行われた(約 27 機関、公開時点で 1,700 点以上。
  https://sketchfab.com/blogs/community/sketchfab-launches-public-domain-dedication-for-3d-cultural-heritage/ )。
- API のカテゴリ `categories=cultural-heritage-history` は実際に絞り込みとして効く。
- 運営の変遷: 2021 年に Epic Games が買収し、2024 年に有料ストアが Fab に移った。
  2026 年 8 月に KitBash3D が再買収したとの情報がある(二次情報)。当日の時点で Data API v3 は動いている。

### 国内

| 名前 | URL | 種別 | 点数の目安 | 配布形式 | 色 | ライセンス | 商用 | 改変 | クレジット | 取得方法 | 備考 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 奈良文化財研究所(`nabunken`) | https://sketchfab.com/nabunken | 骨董考古 + 建築遺跡 | 24 件以上(API で確認) | Sketchfab | UV | CC BY 4.0(ほぼ全件) | 可 | 可 | 要 | Sketchfab(OAuth) | 瓦、石垣、石室など。小物は少ない |
| 埼玉県立さきたま史跡の博物館(`sakitamamuse`) | https://sakitama-muse.spec.ed.jp/3dmodel | 骨董考古(埴輪) | 公式発表で 42 点 | Sketchfab | UV | **混在**: BY / BY-NC-SA / BY-NC-ND | モデルしだい | モデルしだい | 要 | Sketchfab(OAuth) | 水鳥形埴輪と武人頭埴輪は CC BY |
| 福岡市埋蔵文化財センター(`fukuokacity-maibun`) | https://sketchfab.com/fukuokacity-maibun | 骨董考古(勾玉、石製品) | 複数件 | Sketchfab | UV | CC BY 4.0 | 可 | 可 | 要 | Sketchfab(OAuth) | |
| 加曽利貝塚博物館の観察記録シリーズ(`arakiminoru`) | https://sketchfab.com/arakiminoru | 骨董考古(ヒスイ製勾玉ほか) | 複数件 | Sketchfab | UV | CC BY 4.0 | 可 | 可 | 要 | Sketchfab(OAuth) | **翡翠の実物スキャン**(約 1.4 万面) |
| 群馬県文化財保護課(`gunmabunkazai`) | https://sketchfab.com/gunmabunkazai | 骨董考古(縄文土器など) | 複数件 | Sketchfab | UV | CC BY(確認した個体) | 可 | 可 | 要 | Sketchfab(OAuth) | |
| 東京文化財研究所(`tobunken`) | https://sketchfab.com/tobunken | 骨董考古 + 建築遺跡 | 24 件以上 | Sketchfab | UV | 未確認 | 未確認 | 未確認 | 未確認 | Sketchfab | |
| 全国文化財情報デジタルツインプラットフォーム(なぶんけん + 産総研) | https://sitereports.nabunken.go.jp/3ddb | 建築遺跡 | 未確認 | 点群、CAD | 未確認 | 提供機関ごと | 未確認 | 未確認 | 要 | サイト経由 | |
| ColBase(国立文化財機構) | https://colbase.nich.go.jp/ | 美術品 + 骨董 | 画像は数十万件、**3D は確認できず** | 画像 | — | 独自規約(出典を明記すれば商用・改変可) | 可(画像) | 可(画像) | 要 | 手動 | 東博・奈良博・九博の 3D 公開は確認できず |
| 国立科学博物館 Yoshimoto 3D | https://yoshimoto.kahaku.go.jp/3d/ | 自然史(剥製) | 23 点 | 専用ビューア | UV | CC BY-NC | 不可 | 未確認 | 要 | 未確認 | |
| VIRTUAL SHIZUOKA | https://www.geospatial.jp/ckan/dataset/virtual-shizuoka-mw | 地形点群 | 多数 | LAS(1 ファイル平均約 300 MB) | 点群 RGB(未確認) | CC BY 4.0 / ODbL | 可 | 可 | 要 | DL | 個別の文化財ではない |
| 文化遺産オンライン / ジャパンサーチ / 山梨県立考古博物館 | https://bunka.nii.ac.jp/ , https://jpsearch.go.jp/ | — | 3D 公開は未確認 | — | — | — | — | — | — | — | 要再調査 |

国内の傾向: 中央のポータル(ColBase など)には 3D がほとんど無い。色つきで DL できる考古遺物の
主な出どころは、自治体・研究所・埋蔵文化財センターの Sketchfab アカウントで、**CC BY 4.0 が主流**。
美術品(仏像、陶磁器の名品)の 3D を CC で DL できる例は見つからなかった。
海外館の所蔵する日本の作品(`artsmia` の根付や縄文土偶など)は CC0 で出ている。

### パイプライン検証用(美術品ではない)

| 名前 | URL | 点数 | 形式 | 色 | ライセンス | 商用 | 改変 | クレジット | 備考 |
|---|---|---:|---|---|---|---|---|---|---|
| Khronos glTF-Sample-Assets | https://github.com/KhronosGroup/glTF-Sample-Assets | 数十 | glTF / GLB | PBR | モデルごと(CC0 / CC BY 4.0 ほか) | モデルしだい | モデルしだい | モデルしだい | 読み込みの確認用 |
| Google Scanned Objects | https://research.google/blog/scanned-objects-by-google-research-a-dataset-of-3d-scanned-common-household-items/ | 1,030 | OBJ + PNG | UV | CC BY 4.0 | 可 | 可 | 要 | 実スキャンで小さく、テクスチャもある |
| Stanford 3D Scanning Repository | https://graphics.stanford.edu/data/3Dscanrep/ | 約 10 | PLY | 3 点だけ頂点色あり | 研究・教育用(商用は許可が必要) | 不可 | 条件つき | 要 | 形状の定番 |
| Objaverse / Objaverse-XL | https://github.com/allenai/objaverse-xl | 80 万 / 1,020 万 | glTF ほか | 混在 | オブジェクトごとに混在(収集の経緯に異論あり) | 危険 | 危険 | 危険 | 社内の検証にとどめる |

## 4 分類(advice.md の分け方)

- **美術品中心**: Smithsonian 3D(Freer / Sackler、NMAH ほか)、`artsmia`、`clevelandart`、`smkmuseum`、
  `harvardartmuseums`、`fitzwilliammuseum`、The Met(2026 年)、`TheHuntMuseum`、Scan the World(色なし)。
- **骨董・考古中心**: `britishmuseum`(NC)、`rmo_leiden`、`museesaintraymond`、`WirtualneMuzeaMalopolski`、
  `GlobalDigitalHeritage`(NC)、Zenodo、国内各アカウント(`nabunken`、`sakitamamuse`、`fukuokacity-maibun`、
  `arakiminoru`、`gunmabunkazai`、`tobunken`)。
- **建築・遺跡中心**: Open Heritage 3D / CyArk、なぶんけんのデジタルツイン、`GlobalDigitalHeritage` の一部、VIRTUAL SHIZUOKA。
- **CC0 で商用可(まとまった量があるもの)**: Smithsonian 3D、`artsmia`(CC0 分)、`clevelandart`、`rmo_leiden`、
  `museesaintraymond`、`smkmuseum`、`Smithsonian`(Sketchfab)、`WirtualneMuzeaMalopolski`(CC0 分)、
  `TheHuntMuseum`(CC0 分)、The Met(2026 年、未確認)。

## 取得の実務メモ

- Smithsonian: `https://3d-api.si.edu/api/v1.0/content/file/search?q=<語>&rows=1000&start=<n>` の
  各行に `usage`(Download3D / Web3D / App3D / Image2D)、`quality`、`file_type`、`file_size`、
  `uri`(直リンク)、`model_url`(= パッケージ ID)がある。パッケージ単位でまとめれば、
  「OBJ のフル解像度 + GLB の低解像度 + 水密 STL」の有無が一覧になる。
  オブジェクト側のメタデータ(素材、寸法、CC0 表示)は Open Access API(`api.si.edu`、api.data.gov の鍵、
  DEMO_KEY も可)で引くが、3D パッケージ ID との結びつけ方は未確認。
- Sketchfab: 検索とメタデータ(`faceCount`、`vertexCount`、`textureCount`、`license`、`isDownloadable`)は
  認証なしで取れる。ただし `/v3/models/{uid}` を連続で 250 回ほど叩くと 429 になる。
  `archives`(ファイルサイズ)は、認証なしだと null。DL には OAuth2 か API トークンが要り、
  返ってくるのは約 300 秒で失効する署名付き URL(glTF zip / GLB / USDZ)。

## 参照

- Smithsonian 3D API(当日実測): https://3d-api.si.edu/api/v1.0/content/file/search
- Sketchfab Data API: https://sketchfab.com/developers/data-api/v3 、Download API: https://sketchfab.com/developers/download-api
- Europeana API: https://pro.europeana.eu/page/search
- 国内: https://current.ndl.go.jp/car/45853 (なぶんけんの Sketchfab 開設)、
  https://www.tobunken.go.jp/info/news/2023/info20231017/index.html
- Open Heritage 3D FAQ: https://openheritage3d.org/faq
