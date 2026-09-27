# プリンタ制約・材料・コスト(Q5)

> 調査日: 2026-09-27(artifact_print p1 Step 5)。出典は、Stratasys の公式ページ、GrabCAD の公式ガイド、
> 本リポジトリの `.devdocs/vision/printer_export/roadmap.md`、batch1 の記録(`casestudy/real_print/batch1/provenance.md`、`printer_info/memo.txt`)。
> 「未確認」は、公開情報で裏が取れず、オペレータへの確認が必要なもの(→ [open_questions.md](open_questions.md))。

## 実績(batch1 で確定していること)

- 機種: **Stratasys J850**。モードは **High Quality**(層厚 14 µm、600 × 300 dpi = 42.3 × 84.7 µm)、**光沢仕上げ**。
- クリアのスロットは **Vero UltraClear**(VeroClear ではない)。
- 6 樹脂の順序(batch1 のすべての配合表で共通): white, black, clear, cyan, magenta, yellow。GrabCAD 側の名前は
  VeroPureWht, VeroBlack, VeroUltraClear, VeroCyan, VeroMgnt, VeroYellow。
  **VeroVivid(CyanV など)なのか、旧 Vero カラーなのか**は、記録からは判断できない(未確認)。
- 入力: GrabCAD Voxel Print の **PNG 方式、RGBA 32 ビット**(インデックスカラーの PNG は Voxel Print Utility に拒否された。printer_export p3ex1)。
- 部品: 60 × 30 × 5 mm のスラブ 3 枚(agate / amber / fur)。

## J850 の仕様(公開情報)

| 項目 | 値 | 出典 |
|---|---|---|
| 造形域(トレイ) | 490 × 390 × 200 mm | https://www.stratasys.com/en/3d-printers/printer-catalog/polyjet/j8-series-printers/j850-prime-3d-printer/ |
| 樹脂の装填数 | モデル材が最大 7 + サポート材 | 同上 |
| 層厚 | High Quality 14 µm / High Mix 27 µm / High Speed 27 µm / Super High Speed 55 µm(DraftGrey のみ) | 同上 |
| 同時に使える樹脂 | High Quality と High Mix は最大 7、High Speed は 3、Super High Speed は 1 | 同上、https://3dprintingindustry.com/news/stratasys-releases-j850-3d-printer-technical-specifications-and-pricing-163563/ |
| 精度 | 100 mm 未満で ±100 µm、それ以上で ±200 µm か長さの 0.06 % の大きい方(硬質材料) | 同上 |
| 解像度 | Voxel Print の PNG は X 600 dpi × Y 300 dpi。公式ガイドは J750 を例に書かれているが、J850 でも batch1 で実績がある | https://support.stratasys.com/en/Software/GrabCAD-Print/Tips-Guides-and-FAQs/Guide-to-Voxel-Printing |
| PANTONE Validated | 対応 | https://www.javelin-tech.com/3d/stratasys-3d-printer/stratasys-j850-j835-j826/ |

## 材料

| 系統 | 樹脂 | 役割 | 備考 |
|---|---|---|---|
| VeroVivid | VeroCyanV、VeroMagentaV、VeroYellowV | 彩度の高い CMY | 旧 VeroCyan などより彩度が高い(https://www.goengineer.com/3d-printing/stratasys-materials/verovivid) |
| VeroUltra | VeroUltraWhite、VeroUltraBlack、VeroUltraClear | 白と黒は不透明度 99 % 超。クリアはフルカラー向け | https://www.stratasys.com/en/materials/materials-catalog/polyjet-materials/veroultra/ 。VeroClear との光学的な差は未確認 |
| Vero(旧) | VeroPureWhite、VeroBlackPlus など | 汎用の硬質 | batch1 のメモの名前はこちら |
| Agilus30 | 軟質(ゴム状) | 手触りの再現 | 美術品の複製では通常は不要 |
| サポート | SUP705(ウォータージェットで除去)、SUP706B(可溶性。2 % NaOH + 1 % メタケイ酸ナトリウム) | 張り出しと中空部 | https://www.javelin-tech.com/blog/2021/03/removing-stratasys-polyjet-support-material/ |

「フルカラー」の構成(公開情報の推奨): VeroVivid の CMY + VeroUltra の White と Black(+ UltraClear)。
**社内機の 7 スロットに何が入っているか**が、配合の設計を左右する(未確認)。

## GrabCAD Voxel Print の制約

| 制約 | 値 | 本調査への影響 |
|---|---|---|
| 1 スライスあたりの色数 | 背景を除いて最大 6(High Speed では 3)。中間色が 1 ピクセルでもあると "Too many colors" エラー | **PNG の 1 色 = 1 樹脂**。6 樹脂の中でディザする(→ [pipeline_feasibility.md](pipeline_feasibility.md))。7 スロットのうち、使えるのは 6 まで |
| 最低スライス数 | 30 | 問題にならない(候補 A を 60 mm にすると 2,340 枚) |
| PNG の形式 | RGBA 32 ビット、連番、共通の接頭辞 | 既存の `export-print-slices` と batch1 のスクリプトの両方が対応済み |
| 色 → 材料の対応 | Voxel Print Utility の GUI で割り当てる(PNG 側に機械可読な対応表は無い) | 材料対応メモ(md)を必ず添える(batch1 の方式) |
| 出力 | `.gcvf`(GrabCAD Voxel File) | — |
| ライセンス | Voxel Print Utility は GrabCAD Print の有償アドオン(「PolyJet Research Package」)。Preferences → PolyJet → Enable Voxel Print で有効にする | batch1 で使えているので、社内では有効になっている |
| 画像サイズの上限 | 未確認 | 候補 A を 60 mm にすると 1 枚 1,418 × 650。batch1 の fur は 1,418 × 354 で通っている |
| スライス数の上限 | 未確認 | 候補 A を 100 mm にすると、14 µm で 3,899 枚 |

## GrabCAD Print の通常フルカラー(Voxel Print を使わない経路)

- 入力: テクスチャ付きの **OBJ(+ MTL + テクスチャ)、VRML(.wrl)、3MF**。STL は色なし
  (https://support.stratasys.com/en/Software/GrabCAD-Print/About/List-of-supported-file-formats)。
- テクスチャの RGB を、Vivid の CMY + 白 + 黒 + クリアの組み合わせに自動で割り付ける。クリアと組み合わせる場合は、PNG のテクスチャが推奨される
  (GrabCAD のチュートリアル https://grabcad.com/tutorials/how-to-3d-print-in-full-color-part-1 、part 2、part 3)。
- **未確認**: 色の付く層の深さ(表面だけか、何 mm か)、色付きの壁の最小厚さ、ポリゴン数やファイルサイズの上限、光沢と艶消しの切り替えの仕組み。
  これらは GrabCAD Print のマニュアル(一部はログインが必要)か、実機で確かめる。

## 後処理と仕上げ

- サポートの除去: ウォータージェット(SUP705)、アルカリ溶液への浸漬(SUP706B)。
  美術品の複製は、細部と中空部(器の内側)が多いので、**可溶性サポートが望ましい**(社内機にあるかは未確認)。
- 仕上げ: 光沢(Glossy)と艶消し(Matte)。艶消しでは、上面以外がサポート材に覆われて曇った表面になる、というのが一般的な理解。
  **色の見え方(彩度、半透明感)への影響は大きい**と考えられる(未確認)。batch1 は光沢で、Mitsuba の v3 ライブラリも光沢を前提にフィットしている。
- 陶磁器の釉の光沢や、石の艶消しの質感を再現するには、仕上げの選択と、後処理(研磨、クリアコート)の検討が要る(次フェーズ)。

## コストと時間の目安

| 項目 | 目安 | 確度 |
|---|---|---|
| 樹脂単価 | VeroUltraWhite は約 0.29 USD/g、可溶性サポートは約 0.09 USD/g(販売店の掲載価格の抜粋) | 低(未確認。Stratasys は定価を公開していない) |
| 造形時間 | High Quality は Super High Speed の約 7 倍遅い、とされる。絶対値は GrabCAD Print の見積もり機能で確認する | 低(未確認) |
| サポート材の消費 | 公開情報なし | 未確認 |
| 候補 A を 60 mm にしたときの樹脂量 | 水注の体積 447 cm³ × 0.239³ ≒ **6.1 cm³**(中空の器として。比重を約 1.2 とすると約 7 g)。サポートは別 | 形状からの計算 |

→ 実際の時間と費用は、オペレータに聞くか、GrabCAD Print の見積もりで確かめる([open_questions.md](open_questions.md))。
