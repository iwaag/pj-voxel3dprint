# gui_image_export 実施報告 — Step 1（依存とfixture入力の準備）

作成日: 2026-07-17

`plan.md` Step 1 を完了した。

## 変更内容

`vdbmat/pyproject.toml` に dependency-group `gui-capture`（`playwright>=1.55`
のみ）を追加した。`mitsuba` group とは独立させてあり、キャプチャ実行時は
`uv run --group mitsuba-viewer --group gui-capture` で両方を有効化する
（`uv sync --group gui-capture` 単独では既存の `mitsuba-viewer` group が
アンインストールされることを確認済み — 必ず両方のgroup名を並べて指定する
必要がある）。

`uv.lock` は `uv sync --group mitsuba-viewer --group gui-capture` の実行で
自動更新された。

fixture準備関数は、計画通りStep 2のスクリプト内（`prepare_fixture_input()`）
に実装した。新規fixtureは作らず、既存の checked-in
`examples/pipeline_run/inputs/nested_material_cube.voxels.json` と
`run_pipeline()` を使って canonical run bundle を `.local/gui_image_export/
captures/fixture/nested_material_cube/` へ生成する。これは
`tests/integration/test_mitsuba_stage_viewer.py::_write_nested_material_cube_bundle`
と同じ手順の再利用である。

mapping と preset は checked-in の既存ディレクトリをそのまま
`--mapping-root` / `--preset-root` に渡すことにし、新規生成しなかった
（`examples/pipeline_run/mappings/` と
`examples/pipeline_run/demo/presets/` が両方とも git 管理済みで、
plan.md の「既存fixture APIの再利用のみ」という方針に合致するため）。

## 確認済み事実（想定と異なった点）

- ホストの `python3` には mitsuba/viser が入っていないが、`uv run --group
  mitsuba-viewer python3 -c "import mitsuba, viser"` は
  `mitsuba 3.9.0` / `viser 1.0.30` を問題なく import できた
  （事前調査でホストに直接 `import viser` した際の
  `ModuleNotFoundError` は、venv経由でなかったことが原因で、環境自体の
  制約ではなかった）。
- Chromium は `uv run --group gui-capture playwright install chromium` で
  取得できた。`--with-deps` はsudoを要求し失敗したが、`--with-deps` なしの
  単体インストールで headless Chromium は正常に起動できたため、システム
  パッケージの追加インストールは不要だった。

## 完了条件の確認

- `uv sync --group mitsuba-viewer --group gui-capture` が通ることを確認した。
- `prepare_fixture_input()` が `.local/gui_image_export/captures/fixture/`
  配下に bundle（`run.json` + `optical.zarr` ほか）を生成することを、
  Step 2 のスクリプト実行を通じて確認した（Step 1 単体の再現手順は
  report2.md のスクリプト実行ログを参照）。
