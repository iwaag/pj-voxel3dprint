# gui_image_export 実施報告 — Step 3（マニュアル生成指示と雛形）

作成日: 2026-07-17

`plan.md` Step 3 を完了した。

## 変更内容

`.devdocs/function/gui_image_export/manual_prompt.md` を新規作成した。
別セッションのエージェントが追加の口頭説明なしにマニュアルを生成できる
自己完結性を意図し、次を含めた。

- このマニュアルが何を扱い何を扱わないか（GUIパネルのみ。ビューポート
  レンダー内容・材料/mapping/pipelineの科学的内容は対象外で
  README_QUICK/roadmapへ委譲）。
- 入力（manifest.jsonのフィールド定義、README_QUICKの該当節、roadmap）。
- 事実の根拠規則: `panel_text`/`status_text` または既存文書にない事実は
  書かない。`error` が非nullのcapture entryは黙って落とさず「既知の
  ギャップ」として明記する。
- 章構成（起動方法→画面構成→タブ別リファレンス→代表ワークフロー→
  ステータス行の読み方）。Input/Presetタブでは
  「ドロップダウン変更やRefreshだけでは何も起きない」という安全上重要な
  区別をREADME_QUICKの原文表現のまま保持するよう明記した。
- 画像取り込み規則: `.local` パスをマニュアル本文に書かない、採用画像は
  タブベースの安定名で `vdbmat/docs/gui/images/` へコピー、コピー前に
  ローカル環境情報の写り込みを目視確認する（Outputタブのpathフィールドが
  典型例であることを名指しで記載）。
- 再生成手順をマニュアル本文にも埋め込むよう指示する一節。
- 出力前チェックリスト。

## 完了条件の確認

`manual_prompt.md` は plan.md 本文とは独立して読めるよう、必要な背景
（このマニュアルの範囲、ground-truth規則、章構成、画像規則、
再生成手順）を全てファイル内に埋め込んだ。Step 4 で実際にこのファイルの
指示のみに従ってマニュアルを生成し、自己完結性を実地で確認した
（report4.md参照）。
