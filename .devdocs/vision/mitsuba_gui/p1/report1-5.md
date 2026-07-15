# mitsuba_gui Phase 1 実施報告 — Step 1〜5

`plan.md` の実施順序どおり、Step 1（`mitsuba_stage.py` 新設）→ Step 2（CLI統合）
→ Step 3（サンプルプリセット）→ Step 4（検証）→ Step 5（文書化）まで完了した。
Phase 1 全体（Step 1〜5）が「headless のプリセット契約を成立させる」という
1つの意味的まとまりであり、[[mitsuba_improve1]] と同様に1コミット単位として
扱うのが適切と判断し、途中で切らず最後まで進めた。

## 変更内容

- 新規: `vdbmat/examples/pipeline_run/demo/mitsuba_stage.py`
  - `StageConfig`（frozen dataclass、全既定値は旧ハードコード値と同一）と
    下位節 `RenderSettings` / `BackdropSettings` / `FloorSettings` /
    `KeyLightSettings` / `CameraOverride` / `BacklightOverride`。
  - `stage_config_from_json()` / `stage_config_from_dict()` /
    `stage_config_to_dict()`（`format: vdbmat.stage-config` /
    `format_version: 1.0.0` ヘッダ、部分指定補完、未知キー・型不一致・
    範囲外値の明示的拒否）。
  - `scene_bounds()`（旧 `_scene_bounds()` の移設。public `GridGeometry`
    API のみ使用という境界を維持）と `apply_stage()`（旧 `_add_stage()` +
    `_checkerboard_bsdf()` の一般化。`pattern="solid"` 単色 diffuse を追加）。
  - 計画の芯どおり、`camera` / `backlight` は既定 `None` = canonical エントリ
    への passthrough。非 null のときだけ scene_dict の**コピー上で**
    該当エントリを差し替える（backlight は nested dict を共有しないよう
    コピーで置換）。カメラ上書きの規約（方位角は+X基準で+Y向き、Z-up、
    距離 = `radius * distance_factor`）はモジュール docstring に明記した。
- 改修: `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`
  - argparse・zarr 読み込み・`prepare_mitsuba_scene()` 呼び出し・レンダー・
    PIXELSTATS 出力だけの薄い CLI になり、stage 構築は `mitsuba_stage` を
    import して使う（sibling module のため `sys.path` 追加は不要）。
  - `--stage-config PATH` を追加。`--width/--height/--spp/--checker-scale` は
    既定値を `None` に変え、明示されたときだけプリセットに最終上書きする
    （`StageConfig.with_cli_overrides()`）。無指定時の実効値は従来と同じ
    512/512/128/8。
- 新規: `vdbmat/examples/pipeline_run/demo/presets/stage-default.stage.json`
  （全フィールド明示。転記ミスを避けるため `stage_config_to_dict(StageConfig())`
  からコード自身で生成した）、`stage-highkey.stage.json`
  （部分指定の見本: key light 強化 `[12,11,9]`・`scale_factor 1.4`、
  floor を solid グレー、カメラ仰角 42° の俯瞰）。
- 更新: `README_QUICK.md` の Mitsuba stage 節にプリセットの使用例と
  「プリセット JSON が headless 再現の契約、GUI は Phase 2」の位置づけを追記。
- 変更なし: `vdbmat/src/` 配下・`pyproject.toml`・`uv.lock`
  （`git status` で demo 配下のみの差分であることを確認済み）。
  新規外部依存なし（dataclass＋標準 json のみ）。

## 検証結果（Step 4）

動作確認の入出力はすべて `.local/mitsuba_gui/p1/` に置き、git 管理しない。

### 既定出力のピクセル同一（最重要の完了条件）

リファクタ**前**（HEAD `770fffe` 時点のスクリプト）で `nested_material_cube` を
レンダーしてベースラインを確保してから改修に着手した。

```
baseline (リファクタ前):        PIXELSTATS min=0 max=22.0229 mean=0.0693241 std=0.15749
リファクタ後・引数なし:          PIXELSTATS 同上
リファクタ後・stage-default指定: PIXELSTATS 同上
```

PIXELSTATS 一致に加え、`mi.Bitmap` で読んだ 512×512×3 配列を
`np.array_equal` で比較し、**全画素一致**を確認した（引数なし・
`stage-default.stage.json` 指定の両方とも `True`）。lint 修正
（後述）の後にも再レンダーし、同一 PIXELSTATS を確認している。

なお PIXELSTATS の絶対値が [[mitsuba_improve1]] report の記録
（mean=0.100658）と異なるのは、入力の `optical.zarr` がその後再生成されて
いるためで、本検証は同一入力・同一マシンでのリファクタ前後比較として成立
している。

### プリセットの効果

`stage-highkey.stage.json` 指定で `PIXELSTATS min=0 max=48.5712
mean=0.300613 std=0.777455` と変化し、画像を目視すると俯瞰カメラ
（仰角42°、市松床が広く見える構図から単色グレー床の見下ろし構図へ）、
強い暖色キーライトと明瞭な落ち影、floor の solid 化がすべて反映されている。
カメラ上書き（canonical sensor の差し替え）、backlight 以外の全節の
上書きが機能することを画像で確認した。

### 複雑入力（marble-like）

`../.local/marble/bundle/optical.zarr`（複数 exterior/interior 境界群）を
`stage-highkey.stage.json` 付きでレンダーし、エラーなく完走
（`PIXELSTATS min=0 max=1.34577 mean=0.232165 std=0.198369`、数秒）。

### round-trip・バリデーション

スクリプト self-check（`.local` での手動実行）で以下を確認:

- `StageConfig()` → dict → `StageConfig` の同値性（既定・highkey の両方）。
- 部分指定補完: highkey プリセットで未指定の `backdrop` / `render` が
  既定値と同値。
- CLI 上書き優先: `with_cli_overrides(spp=16, checker_scale=4)` が
  render.spp と backdrop/floor 両方の checker_scale に効く。
- 明示的拒否（全て `StageConfigError`）: 未知トップレベルキー、節内の
  未知キー（`colour0` のスペル違い）、`spp=-5`、`spp=True`（bool を整数と
  して拒否）、`pattern="stripes"`、零ベクトル direction、仰角90°、
  format / format_version 不一致。

### 静的検査

`ruff check` は初回に E501 と UP037 の2件を検出 → 修正後
`All checks passed!`。`py_compile` も両ファイル OK。

## 完了条件との対応

- `mitsuba_stage.py`（StageConfig＋純関数）新設、demo が薄い CLI 化: 達成。
- 引数なし実行がリファクタ前と全画素一致: 達成（PIXELSTATS ではなく
  `np.array_equal` で確認）。
- プリセットでライト・カメラ・背景を変えた絵の headless 再現、既定値
  プリセット＝無指定と同一: 達成。
- サンプルプリセット2点が git 管理、部分指定が機能: 達成。
- canonical exporter・medium・境界メッシュ無変更、`pyproject.toml` 差分なし:
  達成。

## 未実施・保留事項

なし。打ち切り条件（ピクセル同一が保てない、look_at 規約の不整合、部分指定
補完の複雑化、solid 追加による関数の歪み）はいずれも発生しなかった。
カメラ上書きと canonical sensor の厳密一致は計画どおり要件にしていない
（規約は docstring に明記済み）。次は Phase 2（viser ビューア MVP）で、
着手時に `.devdocs/vision/mitsuba_gui/p2/plan.md` を切り出す。
