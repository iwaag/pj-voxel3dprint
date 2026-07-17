# gui_image_export 実施報告 — Step 2（キャプチャスクリプト本体）

作成日: 2026-07-17

`plan.md` Step 2 を完了した。

## 変更内容

`vdbmat/examples/pipeline_run/demo/tools/mitsuba_gui_capture.py` を新規
作成した。計画通り、viewer本体のPythonモジュールをimportせず
（`prepare_fixture_input()` が `vdbmat.pipeline` を使うのみで、
`mitsuba_stage_*` 系は一切importしない）、subprocess境界のみで連携する。

処理内容は plan.md の記述通り:

1. fixture準備（Step 1の関数）。
2. `--input-root` / `--mapping-root`（checked-in demo mappings）/
   `--preset-root`（checked-in demo presets）を指定してviewerをsubprocess
   起動し、`--preview-size 64 --preview-spp 2 --interactive-spp 1` の軽量
   設定で描画コストを抑える。
3. Playwright（headless Chromium）でページを開き、`role=tab` の最初の要素が
   可視になるまで待機してから巡回を開始する。
4. `TAB_NAMES` の9タブを `page.get_by_role("tab", name=..., exact=True)`
   で順にクリックし、full page screenshot・panel-scoped screenshot・
   panel内可視テキスト（`panel_text`）を保存する。
5. 代表操作2件（Inputドロップダウンを開いた状態、Presetタブの概要表示状態）
   を追加キャプチャする。
6. `manifest.json`（schema `vdbmat.gui-capture-manifest/1.0`）を書き出す。
7. 末尾でself-check（期待件数の一致、各画像の存在・非0バイト）を行い、
   不合格なら例外を送出する。

### 計画からの実装上の調整（1件）

readiness待ちについて、plan.md は「stdoutの `viewer ready:` 行を待つ」と
書いていたが、実装検証中に **`PYTHONUNBUFFERED=1` を付けないと
その行が子プロセスのstdoutバッファに滞留し続け、事実上ハングしたように
見える**ことを発見した（非TTYへの出力はデフォルトでフルバッファリング
される）。`_start_viewer()` は子プロセス起動時に環境変数
`PYTHONUNBUFFERED=1` を明示的に設定することでこれを解消した。plan.md の
意図（viewer自身が「起動完了」とみなす合図を待つ）はそのまま維持している。

### DOM調査で確定させたセレクタ（plan.md執筆時点では未確定だった詳細）

実際にviewerを起動し、Playwrightで生きたDOMを調査して以下を確定した。

- タブは `role="tab"` を持つ要素として描画され、
  `page.get_by_role("tab", name=<label>, exact=True)` で一意に取得できる
  （mantine製のTabsコンポーネント）。
- control panel本体は、`.mantine-Paper-root` のうち
  `gui.set_panel_label("Mitsuba stage viewer")` で設定されたラベル文字列
  を含むものとして一意に特定できる
  （`page.locator(".mantine-Paper-root").filter(has_text="Mitsuba stage
  viewer")`）。同じboundingboxを持つ空の位置決め用wrapperと、隠れた
  dev-optionsポップオーバーも `.mantine-Paper-root` を持つため、
  DOM順序ではなくテキスト内容で選別する必要があった。この判断根拠は
  スクリプル内コメントに残した。

## 実行結果

`.local/gui_image_export/captures/<timestamp>/` に9タブ分18画像
（full/panel各1）＋代表操作2件分4画像＋`manifest.json` の計23ファイルが
生成されることを複数回の実行で確認した。全11件のcapture entryで
`error: null`（タブ取りこぼしなし）。self-checkは全実行で合格。

viewer subprocessは正常終了・異常終了いずれのパスでも確実にkillされる
ことを確認した（実行後に `ps aux | grep mitsuba_stage_viewer` が空である
ことを複数回確認）。

## lint

`ruff check` / `ruff format --check` を新規ファイルに対して実行し、
両方合格させた（初回実行で検出された不要 `noqa` 3件と
`try/except/pass` 1件は `contextlib.suppress` へ修正済み）。

`mypy src`（CIが実際に検査する範囲）はこのファイルを含まないため対象外。
`mypy` をこのファイル単体に手動で当てると10件のエラーが出るが、
同様に既存の `mitsuba_stage_viewer.py` を単体で当てても74件のエラーが
出ることを確認しており、`examples/` 配下のdemo/toolingスクリプトは
そもそも単体strict mypy通過を前提にしていない（CI設定
`vdbmat/.github/workflows/ci.yml` は `mypy src` のみを実行する）ため、
既存の慣行に合わせて対応不要と判断した。

## 完了条件の確認

1コマンドで9タブ＋代表操作2件の画像とmanifestが
`.local/gui_image_export/captures/<timestamp>/` に生成されることを確認した。
