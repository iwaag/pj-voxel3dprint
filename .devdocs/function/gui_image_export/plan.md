# gui_image_export 実装計画 — stage viewer GUIパネルの自動キャプチャと操作マニュアル生成

作成日: 2026-07-17

## この計画の位置づけ

`mitsuba_stage_viewer.py`（viser GUI）の操作マニュアルを作成・更新するために、
各GUIパネルのスクリーンショットを自動取得するツールを追加する。取得した画像と
「どの操作でその状態に至ったか」の記録（capture manifest）をAIエージェントへ渡し、
マニュアル本文を生成させるワークフローを成立させる。

これは docs/tooling であり、mitsubagui_improve roadmap の回帰テスト層とは独立に扱う。
pytest suite には組み込まず、正しさの検証は既存のPythonレベルのunit／integration
testに引き続き委ねる（事前検討で合意済み: Playwrightによる動作チェック自体は
行わない。用途はマニュアル用キャプチャに限定する）。

参照した前提資料:

- `README_QUICK.md`
- `.local/local_env_memo.md`
- `.devdocs/vision/mitsubagui_improve/roadmap.md` と Phase 1〜5 の plan / report
- `mitsuba_stage_viewer.py` / `mitsuba_stage_binder.py` / `mitsuba_stage_core.py`

## 前提調査（確認済み事実）

### GUI構成

タブは `StageBinder`（`mitsuba_stage_binder.py`）と `ViewerApp`
（`mitsuba_stage_viewer.py`）が構築し、次の9タブが存在する。

```text
Input / Preset / Render / Backdrop / Floor / Key light / Camera / Backlight / Output
```

- Input: 入力dropdown＋Refresh＋概要、mapping dropdown＋Refresh＋概要、
  `Load / Rebuild`、session load path＋`Load session`、Effective stateパネル、
  `Verify digests`
- Preset: preset dropdown＋Refresh＋概要＋`Apply stage preset`
- Output: preset保存、session保存、final PNG path＋`Render final`
- 他タブはstage連続値（照明・カメラ等）のslider/number群

### 起動にはMitsubaが必要

`ViewerApp.__init__` → `StageCore` がpreview scene構築時に `mi.load_dict` を
呼ぶため、viewer起動自体に `mitsuba` dependency group が要る。ホストでは
`uv run --group mitsuba-viewer` で従来どおり起動できる（Phase 1〜5で実績あり）。
ビューポートのレンダー内容はマニュアル上は仮画像で構わないという条件なので、
最小fixture＋低解像度・低sppで起動時間と描画コストを抑える。

### Playwrightはホストで利用可能

Node版 `npx playwright` の動作は確認済み（v1.61系）。本計画ではリポジトリの
言語構成に合わせて **Python版 Playwright** を採用する。core依存には入れず、
`vdbmat/pyproject.toml` の dependency-group として隔離する。

### viserのDOM

viserのcontrol panelはReact製で、タブはテキストラベル（"Input" 等）を持つ
クリック可能要素として描画される。安定したdata-testidは期待できないため、
セレクタはrole／テキストベースとし、タブ名リストをスクリプト側の単一の
定数に集約して破損時の修正点を1箇所にする。

## ゴール

1. 1コマンドで、viewer起動→全タブ巡回→タブごとのスクリーンショット＋
   capture manifest 出力までが完了する。
2. capture manifest に「画像ファイル名・タブ名・直前に行った操作列・
   キャプチャ時のstatusテキスト」が記録され、エージェントが画像を推測に
   頼らず説明文を書ける。
3. キャプチャ成果物は `.local/gui_image_export/` 配下に出力され、
   git管理物へ混入しない。マニュアル本文と採用画像だけを明示的な手順で
   git管理側（`vdbmat/docs/`）へ取り込む。
4. 生成されたマニュアルの雛形（章構成とエージェントへの指示文）が
   リポジトリに残り、GUI変更時に再キャプチャ→再生成で更新できる。

## 非ゴール

- pytest／CIへの組み込み、pixel回帰テスト、GUI動作の自動検証。
- ビューポート（three.js canvas／レンダー結果）の内容検証。仮画像でよい。
- `Load / Rebuild` や `Render final` の完了を伴う重い状態の網羅キャプチャ
  （初期版は各タブの静的状態＋少数の代表操作に限定する）。
- viser内部APIへの依存追加や `src/vdbmat` の変更。
- リモートアクセス・認証（viewerは従来どおり `127.0.0.1` のみ）。

## 成果物と配置

| 成果物 | 配置 | git管理 |
|---|---|---|
| キャプチャスクリプト `mitsuba_gui_capture.py` | `vdbmat/examples/pipeline_run/demo/tools/` | する |
| capture manifest schema（スクリプト内docstring＋定数） | 同上 | する |
| エージェント向けマニュアル生成指示 `manual_prompt.md` | `.devdocs/function/gui_image_export/` | する |
| スクリーンショット＋manifest | `.local/gui_image_export/captures/<timestamp>/` | しない |
| 操作マニュアル本文＋採用画像 | `vdbmat/docs/gui/stage_viewer_manual.md`＋`images/` | する（人が確認後） |

`tools/` directoryは新設。demoモジュール群（`mitsuba_stage_*.py`）と同階層に
置かないのは、viewer本体のimport経路（テストが `DEMO_DIR` をsys.pathへ挿す）
にキャプチャ専用モジュールを混ぜないため。

## 実装ステップ

### Step 1 — 依存とfixture入力の準備

- `vdbmat/pyproject.toml` に dependency-group `gui-capture` を追加する
  （`playwright>=1.55` のみ。mitsuba groupとは独立させ、実行時は
  `uv run --group mitsuba-viewer --group gui-capture` で併用する）。
- `uv run --group gui-capture playwright install chromium` の手順を
  スクリプトdocstringへ記載する（初回のみ必要）。
- キャプチャ用入力は checked-in fixture（`write_phase1_fixtures` 系）から
  最小のbundleを `.local/gui_image_export/fixture/` へ生成する小さな
  準備関数をスクリプト内に持つ（既存fixture APIの再利用のみ。新規fixtureは
  作らない）。`--input-root` / `--mapping-root` / `--preset-root` には
  このfixture rootを渡し、Input/Preset/mapping dropdownに実在候補が
  表示された状態でキャプチャする。

完了条件: `uv sync --group gui-capture` が通り、fixture準備関数が
`.local` 配下にbundle・mapping・presetを生成する。

### Step 2 — キャプチャスクリプト本体

CLI（例）:

```bash
cd vdbmat
uv run --group mitsuba-viewer --group gui-capture \
  python examples/pipeline_run/demo/tools/mitsuba_gui_capture.py \
  --out .local/gui_image_export/captures \
  [--port 8090] [--keep-viewer] [--viewport-size 1400x900]
```

処理内容:

1. fixture準備（Step 1の関数）。
2. viewerをsubprocess起動（`--preview-size 128 --preview-spp 4` 等の軽量設定、
   port衝突回避のため既定8090）。stdoutの `viewer ready:` 行を待つ
  （timeout付き。失敗時はstdout/stderrを添えてエラー終了）。
3. Playwright（headless Chromium）でページを開き、control panelの描画完了を
   タブラベルの可視化で待つ。
4. タブ名定数リスト `TAB_NAMES = ("Input", "Preset", "Render", "Backdrop",
   "Floor", "Key light", "Camera", "Backlight", "Output")` を順にクリックし、
   各タブについて次を保存する。
   - full page screenshot（`NN-<tab>-full.png`）
   - control panel要素にスコープした screenshot（`NN-<tab>-panel.png`）
   - statusテキストと、パネル内の可視テキスト（widget名の裏取り用）
5. 代表操作の追加キャプチャ（初期版は次の2つに限定）:
   - Inputタブ: 入力dropdownを開いた状態（候補一覧が見える）
   - Presetタブ: preset概要が表示された状態（dropdown選択のみ。Applyは押さない）
6. `manifest.json` を出力する。schema（version付き、初版 `1.0`）:

```json
{
  "schema": "vdbmat.gui-capture-manifest/1.0",
  "captured_at": "...",
  "viewer_command": ["..."],
  "viewport_size": [1400, 900],
  "captures": [
    {
      "image": "01-input-panel.png",
      "tab": "Input",
      "actions": ["click tab 'Input'"],
      "status_text": "...",
      "panel_text": ["input", "Refresh", "Load / Rebuild", "..."]
    }
  ]
}
```

7. 終了時にviewer subprocessを確実に停止する（`--keep-viewer` 指定時を除く。
   異常系でもfinallyでkill）。

実装上の規約:

- タブクリックは `get_by_role`／`get_by_text(exact=True)` を基本とし、
  ヒットしない場合はそのタブをmanifestへ `"error"` 付きで記録して続行する
  （1タブの破損で全キャプチャを失わない）。
- 固定sleepではなく要素待機を使う。previewレンダー完了は待たない
  （ビューポートは仮画像でよい条件のため、statusが `starting…` のままでも
  キャプチャは有効。その旨をmanifestのstatus_textで判別できる）。
- スクリプトはviewer本体のPythonモジュールをimportしない（subprocess境界のみ。
  タブ名定数の二重管理はコメントで `mitsuba_stage_binder.py` への参照を明示）。

完了条件: 1コマンドで9タブ＋代表操作2件の画像とmanifestが
`.local/gui_image_export/captures/<timestamp>/` に生成される。

### Step 3 — マニュアル生成指示と雛形

- `.devdocs/function/gui_image_export/manual_prompt.md` を作成する。内容:
  - エージェントへの指示: manifestと画像を読み、
    `vdbmat/docs/gui/stage_viewer_manual.md` の章構成
    （起動方法→画面構成→タブ別リファレンス→代表ワークフロー→トラブル時の
    見方）に沿って本文を書く。
  - 事実の根拠規則: 操作手順・widget名はmanifestの `panel_text` /
    `actions` と既存文書（README_QUICKの運用小節、roadmap）だけを根拠とし、
    画像からの推測で仕様を書かない。
  - 画像の取り込み規則: 採用画像のみ
    `vdbmat/docs/gui/images/` へコピーし、ファイル名はタブベースの安定名
    （`input-panel.png` 等）へリネームする。`.local` パスをmanualへ
    書かない。
- マニュアル本文の初版生成は本計画のStep 4で1回実施し、以後の更新は
  「再キャプチャ→manual_prompt.mdで再生成→人がdiff確認」を標準手順とする。

完了条件: manual_prompt.md 単体で、別セッションのエージェントが追加の
口頭説明なしにマニュアルを生成できる自己完結性がある。

### Step 4 — 一巡実行と初版マニュアル

- ホストでStep 2を実行し、キャプチャ一式を取得する。
- manual_prompt.md に従って `vdbmat/docs/gui/stage_viewer_manual.md` の
  初版を生成し、採用画像をコピーする。
- README_QUICK のviewer節から本マニュアルへの参照を1行追加する。

完了条件: マニュアル初版と画像がgit管理側に入り、本文中の全画像リンクが解決し、
本文にローカル絶対パス・`.local` パスが含まれない。

## 検証方針

- pytestには組み込まない。スクリプト自身のself-check（生成画像が存在し
  0 byteでない・寸法がviewport指定と整合・manifestのcaptures件数が期待数）を
  実行末尾で行い、不合格ならexit非0にする。
- manifest構築・ファイル名採番・fixture準備などpure部分は関数として分離し、
  将来テストを足せる形にはするが、本計画ではself-checkまでとする。
- 破損ケース（viewer起動失敗、タブ名不一致）はエラー文言にstdout抜粋／
  該当タブ名を含めることを手動で確認する。

## リスクと方針

### viserのDOM構造がバージョンで変わる

セレクタとタブ名を定数に集約し、タブ単位のエラー記録で部分的に生き残る設計に
する。viser更新時はキャプチャ再実行が検知手段になる（それ以上の防御はしない —
docs用ツールであり回帰テストではない）。

### Mitsuba無し環境で動かせない

viewer起動自体がMitsubaを要するため、本ツールはMitsuba入りホスト前提とする。
Mitsubaをstub化してviewerを起動する経路は、viewer本体へのtesting hook追加を
伴うため本計画では行わない（必要になったら別計画）。

### スクリーンショットにローカル環境情報が写り込む

Output/Inputタブのpath text widgetには `.local` 配下の相対〜絶対パスが表示され
うる。fixture root相対の短いパスになるよう起動引数を整え、git管理側へコピーする
採用画像は取り込み時に人が写り込みを確認する（manual_prompt.mdの規則に明記）。

### キャプチャとGUI実装の乖離

GUI変更（タブ・widget追加）時にマニュアルが古くなる。再キャプチャ→再生成の
標準手順をmanual_prompt.mdとマニュアル冒頭に明記し、乖離検知は運用
（GUI変更を伴うphase完了時に再実行）へ委ねる。
