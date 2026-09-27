# artifact_print p1 step 5 report — プリンタ制約・材料・コスト(Q5)

## Done

- `study/3dprint_artifact/print_constraints.md`: 次の 6 節にまとめた。
  - batch1 で確定している事実(J850、High Quality、光沢、Vero UltraClear、樹脂の順序、RGBA 32 ビット)
  - J850 の公開仕様(造形域、装填数、層厚、モード別の同時樹脂数、精度)
  - 材料(VeroVivid / VeroUltra / 旧 Vero / Agilus / サポート)
  - Voxel Print の制約(本調査への影響付き)
  - GrabCAD の通常フルカラー
  - 後処理と仕上げ、コストと時間の目安
- `study/3dprint_artifact/open_questions.md`: オペレータに聞くことを 4 群(材料と装填、モードと仕上げ、時間と費用、測色)に分けて 13 項目足した。
  利用者に頼むこと(Sketchfab トークン、任意で api.data.gov キー)、データとライセンス、技術の問いもまとめた。
- 情報源は、Step 1 と同時に起動した J850 調査のサブエージェント(sonnet)と、本リポジトリの `roadmap.md`、batch1 の `provenance.md` と `memo.txt`。

## Commands

```bash
sed -n 1,30p casestudy/real_print/batch1/provenance.md
grep -rn "時間\|hour\|コスト\|glossy\|matte\|support" casestudy/real_print/batch1/*.md .devdocs/vision/printer_export/p3ex1/*.md
```

## Learned

- **7 スロットのうち、Voxel Print で同時に使えるのは 6**(1 スライスあたり 6 色の上限)。batch1 は W / K / Clear / C / M / Y の 6 で埋めていた。
  美術品の複製で色域を広げたい場合(たとえば、呉須の紺や釉の褐色の専用樹脂を足す)には、この 6 枠がそのまま制約になる。
- batch1 の記録には、**VeroVivid か旧 Vero カラーか**が書かれていない(名前は旧名)。色の配合の設計は装填された樹脂に強く依存するので、
  オペレータへの質問の第一項目にした。
- 公開情報では、時間、費用、GrabCAD の通常フルカラーの色の深さと最小壁厚が、どれも分からなかった。いずれも、実機の見積もり画面かオペレータに聞くしかない。
- 候補 A を 60 mm にしたときの樹脂量は、約 6 cm³(中空の器として。サポートは別)。材料費は小さく、支配的なのは装置の時間。

## Skipped

- 社外への問い合わせ(Stratasys、販売店)は、plan の範囲外。
- 価格は販売店の掲載値の抜粋だけ(確度は低いと明記した)。
