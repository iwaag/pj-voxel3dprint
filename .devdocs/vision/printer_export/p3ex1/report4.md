# Step 4 報告 — RGBA 出力ドキュメント更新

## 実施内容

- `vdbmat-utils/docs/print-slices.md` を RGBA(32-bit) 出力へ更新した。
  `write_rgba_png()`、alpha=`255` 固定、内部 palette index を最終 PNG には
  書かないこと、RGB値集合による書出し直後の再検査を記載した。
- claims に、GrabCAD Voxel Print Utility が従来の indexed-palette PNG を
  32-bit画像要件で拒否した実機確認と、それを受けて exporter が常に RGBA を
  出力する方針を記録した。RGBA版の再投入による当該エラー解消は Step 5 の
  人間確認として明確に残している。
- `convert-image-stack` の色PNG入力は独立した機能であるため、indexed PNG の
  reader/writer を残すことも記載した。
- 利用者向けの記載が実装と矛盾しないよう、`vdbmat-utils/README.md` と
  ルートの `README_QUICK.md` の print-slices 出力説明を RGBA(32-bit) に更新し、
  `docs/image-stacks.md` の rgb PNG 入力受理条件へ完全不透明 RGBA を追加した。

## 確認

```text
git diff --check
# clean
```

Step 3 の契約テストで、更新したドキュメントが説明する RGBA→RGB の
`convert-image-stack` 往復経路はすでに 15 passed で確認済みである。

## 次ステップ

Step 5 は実機再投入を伴う人間作業である。AI側では既存 config を再利用して
RGBA版スライスを `.local/printer_export/p3/` に生成・zip化するところまでを準備し、
GrabCAD Voxel Print Utility での投入結果の判断を依頼する。
