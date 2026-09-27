# 未解決の問い・確認事項(Q5 ほか)

> Step 2 時点の暫定版。Step 5 でオペレータへの質問を追加する。

## 利用者(このリポジトリの担当者)に頼むこと

- [ ] **Sketchfab の API トークン**: 半透明枠の候補(玉璧 `d763ec3d…`、雪花石膏の喪服像 `0d89139b…`、
  ヒスイ製勾玉 `0f9fe38a…`)を落とすのに必要。Sketchfab にログインし、
  Settings → Password & API で表示されるトークンを使う(`Authorization: Token <token>` で `/v3/models/{uid}/download`)。
  トークンは `.local/` の外に書かない。

## データとライセンス

- [ ] Smithsonian 3D の候補 A、B について、オブジェクトページで CC0 の表示を確認する
  (当日は `3d.si.edu` が 403、Open Access API も DEMO_KEY の上限に達していた)。
  api.data.gov の個人キーがあれば、Open Access API で `metadata_usage` を引ける。
- [ ] The Met の 2026 年 3D 公開(約 140 点、CC0 との報道)の実際の配布条件。公式ページは当日 429 で読めなかった。
- [ ] GLB の単位の揺れ(m と mm が混在)。Smithsonian のメタデータに実寸があるか。
