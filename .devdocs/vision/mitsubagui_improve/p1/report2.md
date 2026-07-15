# mitsubagui_improve Phase 1 実施報告 — Step 2

`plan.md` の Step 2（Headless 経路）まで完了した。Step 1 で確定した
`RenderSettings.max_depth` を headless CLI、`MitsubaExportConfig`、scene dict、
scene summary、実行ログまで一貫して伝播できるようになったため、ここを次の独立した
コミット境界と判断した。viewer core と GUI は未着手である。

## 変更内容

### Headless CLI

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`
  - `--max-depth N` を追加した。
  - 他の render 引数と同様に、組み込み既定値 < stage preset < 明示 CLI の
    優先順位で `StageConfig.with_cli_overrides()` に適用する。
  - 正整数検証は Step 1 の `RenderSettings` を共通経路として利用し、CLI 専用の
    別契約を作っていない。
  - `MitsubaExportConfig(max_depth=stage.render.max_depth)` として scene prepare に
    実効値を渡すようにした。
  - `PIXELSTATS` に `max_depth=N` を併記し、headless 実行ログから実効値を確認
    できるようにした。
  - module docstring とコマンド例を `--max-depth` を含む内容へ更新した。

### テスト

- `vdbmat/tests/test_mitsuba_stage_demo.py` を新設した。
  - argparse が `--max-depth` を受理することを検証した。
  - headless `main()` の境界で次の3経路を検証した。
    - 旧 1.0.0 preset: max_depth を 8 で補完する。
    - 1.1.0 preset: 明示した max_depth を保持する。
    - 1.1.0 preset + CLI: CLI 値が preset より優先する。
  - 各経路で実効値が `MitsubaExportConfig` と `PIXELSTATS` ログの両方へ一致して
    伝わることを確認した。render 自体は fake Mitsuba に置換し、このテストを
    Mitsuba 不要の headless wiring test としている。
- `vdbmat/tests/integration/test_mitsuba.py`
  - 非既定値 `max_depth=14` で実際に scene prepare し、scene dict の volpath
    integrator と `scene-summary.json.render.max_depth` がともに14になることを
    検証した。

canonical exporter は既に正しい scene dict と summary を生成するため変更して
いない。今回の integration test は、その既存契約と新しい headless 伝播の接続点を
固定するものである。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q \
  tests/test_mitsuba_stage_config.py \
  tests/test_mitsuba_stage_demo.py \
  tests/test_mitsuba_stage_viewer_worker.py
26 passed in 0.39s

uv run --group mitsuba pytest -q tests/integration/test_mitsuba.py
11 passed in 0.53s

uv run pytest -q --ignore=tests/integration
380 passed in 20.30s

uv run ruff check \
  examples/pipeline_run/demo/mitsuba_stage.py \
  examples/pipeline_run/demo/mitsuba_stage_demo.py \
  tests/test_mitsuba_stage_config.py \
  tests/test_mitsuba_stage_demo.py \
  tests/integration/test_mitsuba.py
All checks passed!

git diff --check
問題なし
```

## コミット境界と未実施事項

この境界で次が成立する。

```text
stage JSON / --max-depth
          ↓
RenderSettings.max_depth
          ↓
MitsubaExportConfig.max_depth
          ↓
headless scene integrator / scene-summary / PIXELSTATS log
```

以下は次 Step 以降に残している。

- Step 3: preview の max depth 保持、予定された rebuild、final cache key と
  final config への伝播、viewer status。
- Step 4: Render タブの number input と StageBinder round-trip。
- Step 5: committed preset、README、GUI final と headless replay の
  end-to-end 検証。

canonical exporter、volume、boundary mesh、material mapping、依存関係には変更して
いない。動作確認用の `.local` 成果物も生成していない。
