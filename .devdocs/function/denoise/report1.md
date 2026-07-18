# denoise 実装計画 実施報告 — Step 1

`plan.md` の Step 1（stage-config 1.2.0: `render.denoise` フィールド）を完了した。

## 変更内容

### `mitsuba_stage.py`

- `RenderSettings` に `denoise: bool = False` を追加し、`__post_init__` で
  `_check_bool("render.denoise", ...)` により型検証する。
- `STAGE_CONFIG_FORMAT_VERSION` を `1.2.0` に上げ、
  `STAGE_CONFIG_ACCEPTED_VERSIONS` を `{1.0.0, 1.1.0, 1.2.0}` にした。
- `render` 節の許容キーをバージョンごとに明示するテーブル
  `_RENDER_ALLOWED_FIELDS_BY_VERSION` を新設した
  (`1.0.0 → {width, height, spp}`, `1.1.0 → {width, height, spp,
  max_depth}`)。`1.0.0` に `max_depth` を許さない既存の挙動と対称に、
  `1.1.0` にも `denoise` を許さない（`unknown keys` として明示的に拒否する）
  ようにした。`1.2.0` 文書は制限なし（`RenderSettings` の全フィールドを許容）。
- `stage_config_to_dict` は `fields()` を介して常に `denoise` を書き出す
  （既存の仕組みをそのまま利用、変更不要）。

### `mitsuba_viewer_session.py`（想定外の追加変更）

plan の「組み込みポイント」節は viewer session について
「`render` 節にフィールドを足せば…追加実装なしで追従する」としていたが、
実装して `pytest` を通したところ誤りだと判明した。この module は
`RenderSettings` のフィールドを動的に参照せず、`_RENDER_KEYS =
frozenset({"width", "height", "spp", "max_depth"})` という**固定の許容キー
集合**で `render` 節を厳密一致検証しており、`denoise` を書き出すと
`render has unknown keys: ['denoise']` で reject されていた
(`tests/test_mitsuba_viewer_session.py` ほか `test_mitsuba_session_compat.py`
の計19件が failure)。

これは人間の判断を要する設計変更ではなく、`max_depth` 追加時と同一パターンの
機械的な追従漏れだったため、次を修正してStep 1のコミット境界とした。

- `_RENDER_KEYS` に `"denoise"` を追加。
- `_parse_stage_and_render` の `RenderSettings(...)` 構築に
  `denoise=render["denoise"]` を追加。
- `VIEWER_SESSION_FORMAT_VERSION`（`1.1.0`）はバンプしていない。既存の
  `max_depth` 追加時も本バージョンは変えておらず、viewer session は
  実行中のGUIサーバが都度生成する短命な成果物であり、stage-config preset
  のようにgit管理された長命ドキュメントの後方互換を保証する対象ではない
  ため（`format_version 1.0.0` の受理は `mapping` 節の有無のみを区別する
  目的で、`render` 節は現行 `RenderSettings` の全フィールドを常に要求する
  既存の非対称な設計を踏襲した）。

### テスト

- `tests/test_mitsuba_stage_config.py`: `RenderSettings.denoise` の
  既定値・型検証・`1.0.0`/`1.1.0` での黙補足・拒否、`1.2.0` での
  明示指定/既定値読み込み、serializer round-trip（`denoise: True` を含む）、
  version rejection の対象を `1.2.0` → `1.3.0` に更新、を追加・更新した。
- `tests/test_mitsuba_viewer_session.py`:
  `test_writer_reader_round_trip_preserves_all_fields` に
  `denoise=True` を含めるよう更新した。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q --ignore=tests/integration
598 passed in 39.57s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer.py
38 passed, 2 warnings in 25.32s
```

（warningは既存の非同期teardown由来（`RuntimeError: Event loop is closed`）で、
`.devdocs/vision/mitsubagui_improve/p5/report1.md` に記録済みの既知事象と同じ
もの。本Stepの変更に起因しない。）

```text
uv run ruff check examples/pipeline_run/demo/mitsuba_stage.py \
  examples/pipeline_run/demo/mitsuba_viewer_session.py \
  tests/test_mitsuba_stage_config.py tests/test_mitsuba_viewer_session.py
All checks passed!

uv run ruff format --check (同上ファイル群)
4 files already formatted

git diff --check
問題なし
```

既存 preset (`stage-default.stage.json` / `stage-highkey.stage.json`,
いずれも `format_version: "1.1.0"`) は無変更のまま読み込めることを
上記テストスイート経由で確認した（`denoise` キーを持たないため
`False` が黙補される）。

## コミット境界としての判断

Step 1 完了地点を独立したコミット境界とした。この境界で次が単独で成立する。

- `RenderSettings.denoise` が stage-config 1.0.0/1.1.0/1.2.0 のいずれでも
  期待どおり読み書きできる。
- viewer session の read/write も `denoise` を含めて round-trip する
  （plan の想定外だった箇所を含め、全既存テストが無回帰で通過）。
- `StageCore` / GUI / demo CLI は未着手（Step 2 以降の範囲）。

変更対象は次の4fileのみ。

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage.py`
- `vdbmat/examples/pipeline_run/demo/mitsuba_viewer_session.py`
- `vdbmat/tests/test_mitsuba_stage_config.py`
- `vdbmat/tests/test_mitsuba_viewer_session.py`

vdbmat submodule 側のコミット: `e1f537d denoise p0 step1: stage-config
1.2.0 render.denoise field`。

## 未実施事項

- Step 2: `StageCore` のデノイズ適用と raw/denoised 二重出力。
- Step 3: GUI（binder）checkbox と session 配線の確認
  （`mitsuba_session_compat.py` の stage digest 比較を含む）。
- Step 4: `mitsuba_stage_demo.py --denoise` と README_QUICK /
  stage viewer manual の追記。
- Step 5: 白バンドルでの一巡検証（GPU実測、report5.md）。
