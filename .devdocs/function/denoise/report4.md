# denoise 実装計画 実施報告 — Step 4

`plan.md` の Step 4（`mitsuba_stage_demo.py` と文書）を完了した。

## 変更内容

### `mitsuba_stage.py`

- `StageConfig.with_cli_overrides` に `denoise: bool | None = None` を追加
  した。`max_depth` と同じ「`None` はプリセット値を保持、明示指定が勝つ」
  規則。`False` の明示上書きも `is not None` 判定で正しく効くことを確認
  した(`denoise=False` は「None ではない」ので反映される)。

### `mitsuba_stage_demo.py`

- legacy CLI 形式に `--denoise`(`action="store_true"`)と
  `--no-denoise`(`action="store_false"`、同じ `dest="denoise"`)を追加した。
  既定は `None`(プリセット値を保持)。`--session` 形式では両方とも
  拒否されるよう、既存の render-override 拒否チェック
  (`--width`/`--height`/`--spp`/`--max-depth`/`--checker-scale`)の対象に
  `args.denoise` を追加した。
- `_resolve_legacy` の `with_cli_overrides(...)` 呼び出しに
  `denoise=args.denoise` を追加した。
- `render_stage()` を Step 2 の `finalize_render_image`
  (`mitsuba_stage_core.py`)経由の書き出しに変更した。従来の
  `mi.util.write_bitmap` 直呼び出しを置き換え、`stats` 文字列の組み立てを
  `PIXELSTATS` 接頭辞なしの中身だけにして `finalize_render_image` に渡し、
  返ってきた文字列に `print(f"PIXELSTATS {stats}")` で接頭辞を付ける形にした。
  モジュールレベルの `_denoiser_cache: dict[tuple[int, int], object] = {}` を
  新設し(1プロセス内での複数呼び出し— 主にテスト — で解像度ごとに1個の
  denoiser を使い回す)、viewer 側の `StageCore._denoiser_cache` と同じ
  キャッシュ規約に揃えた。
- モジュール docstring の CLI 使用例・オプション一覧・`--session` との
  排他リストに `--denoise`/`--no-denoise` を追記した。

## テスト

### 単体(`tests/test_mitsuba_stage_config.py`, `tests/test_mitsuba_stage_demo.py`、Mitsuba不要)

- `test_cli_denoise_override_wins_and_none_preserves_preset`:
  `with_cli_overrides()` の denoise 版(`max_depth` と同型)。
- `test_parse_args_denoise_defaults_to_none` /
  `test_parse_args_accepts_denoise_flag` /
  `test_parse_args_accepts_no_denoise_flag`: `--denoise`/`--no-denoise`
  フラグの argparse 解析。
- `test_parse_args_session_mode_rejects_denoise_overrides`
  (`--denoise`/`--no-denoise` を parametrize): `--session` 形式で両フラグが
  拒否されること。
- 既存 `test_main_propagates_effective_max_depth_to_export_and_log` が
  直接組み立てる `argparse.Namespace` に `denoise=None` を追加した
  (`_resolve_legacy` が新たに `args.denoise` を参照するようになったため
  必須になった変更、無回帰)。

### 統合(`tests/integration/test_mitsuba_stage_viewer.py`, 実Mitsuba)

- `test_demo_cli_denoise_requires_cuda_variant`: legacy CLI の `--denoise
  --variant llvm_ad_rgb` が `DenoiseVariantError` を投げること。
- `test_demo_cli_denoise_writes_raw_and_denoised_with_stats_suffix`
  (`cuda_ad_rgb` 必須): 実 `main()` 呼び出しで raw/denoised 両PNGが生成され
  互いに異なること、stdout の `PIXELSTATS` 行に `denoise=optix` が付くこと。
- `test_saved_denoised_session_viewer_final_matches_headless_session_replay`
  (`cuda_ad_rgb` 必須): Step 3 report で先送りにしていた「denoise=True の
  session を GUI の `StageCore.render_final` と headless `--session` replay
  の両方で render し、ピクセルが完全一致する」ことを確認した
  (`test_saved_session_viewer_final_matches_headless_session_replay` の
  denoise版)。raw sidecar(`viewer.raw.png` / `headless.raw.png`)の存在も
  確認した。これで Step 3 の完了条件のうち先送りにした項目が閉じた。

### 実機smoke(手動、`.local/denoise/step4-smoke/` に生成、git非管理)

`primitive-array-demo-186ad621ecca`(checked-in `.local` fixture)の
`optical.zarr` に対し、実際に CLI を2通り実行して確認した。

```text
uv run --group mitsuba python \
  examples/pipeline_run/demo/mitsuba_stage_demo.py -- \
  ../.local/blender_improve1/primitive-array-demo-186ad621ecca/optical.zarr \
  ../.local/denoise/step4-smoke/denoised.png \
  --width 64 --height 64 --spp 32 --max-depth 32 --denoise --variant cuda_ad_rgb

PIXELSTATS variant=cuda_ad_rgb seed=20260628 max_depth=32 min=0 max=1.56573
mean=0.0608198 std=0.100911 denoise=optix
```

`denoised.png` と `denoised.raw.png` の両方が生成されることを確認した。

```text
uv run --group mitsuba python \
  examples/pipeline_run/demo/mitsuba_stage_demo.py -- \
  ../.local/blender_improve1/primitive-array-demo-186ad621ecca/optical.zarr \
  ../.local/denoise/step4-smoke/should-fail.png \
  --width 32 --height 32 --spp 4 --denoise --variant llvm_ad_rgb

mitsuba_stage_core.DenoiseVariantError: render.denoise requires a
cuda_ad_rgb-family Mitsuba variant (mi.OptixDenoiser is CUDA-only); got
variant='llvm_ad_rgb'
```

CPU variant では黙って無視されず、トレースバック付きで明示的に失敗することを
確認した。

## 文書更新

- `README_QUICK.md`(Use Case 8): 「Adjust the Stage with a Preset」節を
  stage-config 1.2 表記に更新し(1.0→1.1→1.2 の黙補則を明記)、新設の
  「Reduce Noise with OptiX Denoising (Scattering Media Subjects)」節に
  ノイズの構造的原因(デルタ誘電体境界のため NEE が効かず 1/√N 収束に
  頼るしかないこと)、`max_depth` の推奨値(散乱媒質を含む被写体では
  32〜64、既定8だとエネルギー損失で暗くなる)、`--denoise` の使い方、
  raw sidecar と PIXELSTATS が denoise の影響を受けないこと、
  再現性の限定(denoise済み出力は同一GPU/ドライバでのみ pixel-identical、
  raw側は無条件)を追記した。viewer の CUDA variant 節と headless replay の
  排他オプション一覧にも `--denoise`/`--no-denoise` を反映した。
- `vdbmat/docs/gui/stage_viewer_manual.md`: Render タブ節に
  `denoise (OptiX)` checkbox の説明(既定off、settled previewのみに適用、
  raw sidecarとPIXELSTATSの規則、CUDA variant必須の disabled 条件)を
  追記した。既存スクリーンショット(`images/render-panel.png`)は
  このcheckbox追加前のものであり、`gui_image_export` の再キャプチャ対象と
  明記した(本ステップでは実ブラウザでの再キャプチャは行っていない —
  非対話環境であるため)。

## 検証結果

実行場所は `vdbmat/`。GPU: `Quadro RTX 8000`(CUDA 13.1)。

```text
uv run pytest -q --ignore=tests/integration
615 passed in 35.71s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer.py
46 passed, 2 warnings in 27.20s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer_regression.py
9 passed in 18.36s
```

（warningは既知の非同期teardown由来、Step 1〜3と同じ。）

```text
uv run ruff check docs 以外の変更ファイル一式
All checks passed!

uv run ruff format --check (同上)
6 files already formatted

git diff --check
問題なし
```

## コミット境界としての判断

Step 4 完了地点を独立したコミット境界とした。この境界で次が単独で成立する。

- `mitsuba_stage_demo.py` の legacy CLI が `--denoise`/`--no-denoise` を
  受け付け、`--session` では拒否する。
- headless の `render_stage()` が viewer の `StageCore` と同じ
  raw保全・PIXELSTATS規則・variant guardで denoise を適用する
  (実GPUでの手動smoke・統合テストの双方で確認)。
- GUI final render と headless `--session` replay が denoise=True でも
  同一GPUでピクセル一致する(Step 3 の先送り項目を解消)。
- README_QUICK.md と stage_viewer_manual.md に denoise の使い方・
  再現性の限定・ノイズの構造的原因が記載されている。

変更対象は次のとおり(vdbmat submodule内)。

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage.py`
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`
- `vdbmat/docs/gui/stage_viewer_manual.md`
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
- `vdbmat/tests/test_mitsuba_stage_config.py`
- `vdbmat/tests/test_mitsuba_stage_demo.py`

および親リポジトリの `README_QUICK.md`(このコミット境界と併せて次のコミットで反映)。

vdbmat submodule 側のコミット: `58e9e6f denoise p0 step4: mitsuba_stage_demo.py
--denoise CLI flag and docs`。

## 未実施事項

- Step 5: 白バンドル(前提調査と同じ
  `primitive-array-demo-10x-white-1b16d5b2975c`)での一巡検証。GUIから
  spp 256 + max_depth 64 + denoise の final render を実行し、従来の
  spp 1024・denoise なしと目視比較して改善を確認する。session
  save→headless replay のピクセル一致は Step 4 で白バンドル以外の
  合成volumeを使って既に確認済みだが、Step 5 では実際の白バンドルで
  再確認する。`llvm_ad_rgb` viewer で checkbox が disabled であることの
  実ブラウザ確認(非対話環境のため代替手段を検討)も残っている。
