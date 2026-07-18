# denoise 実装計画 実施報告 — Step 2

`plan.md` の Step 2（`StageCore`: デノイズ適用と raw 出力の保全）を完了した。

## 変更内容

### `mitsuba_stage_core.py`

- `DenoiseVariantError`（`Exception`）: `render.denoise=True` を非CUDA variant
  で要求した場合に投げる例外。「approximate silently しない」原則どおり、
  黙ってデノイズを飛ばさず明示的に失敗する。
- `require_denoise_variant(variant: str)`: `variant` が `"cuda"` で始まらな
  ければ `DenoiseVariantError` を投げる。plan の「cuda_ad_rgb 系」要求どおり
  `cuda_ad_rgb` だけでなく `cuda_ad_rgb_double` 等の亜種も許容する
  prefix 判定にした。
- `denoise_image(mi, image, width, height, cache)`: `mi.OptixDenoiser` を
  `(width, height)` ごとに1個キャッシュして適用する。`mi` は
  `ModuleType` として渡すだけの純関数で、実 Mitsuba への依存は呼び出し境界
  で切れている(スタブでの単体テストが可能)。
- `finalize_render_image(mi, image, render, output_png, stats, denoiser_cache)`:
  final render の書き出しを一本化するヘルパ。`render.denoise` が偽なら
  従来どおり `output_png` へ書くだけ(`stats` 不変、`.raw.png` は作らない
  — pixel-identical)。真なら
  1. raw画像を `<output_png stem>.raw<suffix>`（例: `final.raw.png`）へ先に書く
  2. `require_denoise_variant` で variant を検証
  3. denoise 結果を `output_png` へ書く
  4. `stats` に `" denoise=optix"` を追記して返す
  という plan どおりの順序を実装した。`StageCore.render_final` と
  `mitsuba_stage_demo.py`（Step 4 で配線予定）の両方から呼べる、
  `StageCore` インスタンスに依存しない自由関数として置いた。

### `StageCore`

- `__init__` に `self._denoiser_cache: dict[tuple[int, int], object] = {}`
  を追加(解像度ごとの遅延生成キャッシュ、final render と settled preview
  で共有)。
- `render_final`: raw画像から PIXELSTATS を計算したうえで
  `finalize_render_image` に書き出しを委譲する形に変更。
- `render_preview`: `spp is None`(settled preview)かつ
  `config.render.denoise` が真の場合のみ `require_denoise_variant` →
  `denoise_image` を適用し、`stats` に `" denoise=optix"` を追記する。
  interactive preview（`spp` 明示指定)は denoise の対象外のまま
  (plan の非ゴール「interactive preview へのデノイズ適用」を守る)。
  stats は常に raw pixel から計算する(既存の `_pixel_stats` 呼び出し位置は
  denoise 分岐より前)。
- `_final_render_key` には touch していない(denoise はシーン構造に影響しない
  後処理のみのため、plan の想定どおり再prepare判定に含めない)。

## テスト

### 単体テスト（Mitsuba不要、スタブ `mi`）

`tests/test_mitsuba_stage_core_denoise.py`（新規、8件）: `_StubMi` /
`_StubDenoiser` / `_StubUtil` で `mi.OptixDenoiser` と
`mi.util.write_bitmap` をなぞらえ、次を検証した。

- `require_denoise_variant` が `cuda_ad_rgb` 系を許容し `llvm_ad_rgb` を拒否。
- `denoise_image` が解像度ごとに1個の denoiser を作り、同解像度の再呼び出し
  では作り直さないこと。
- `finalize_render_image` の denoise off/on の書き込みシーケンス
  (off: final のみ1回書き込み、stats不変、raw非存在。on: raw→denoised の
  順で2回書き込み、stats に `denoise=optix` 追記)。
- `finalize_render_image` が denoise on かつ非CUDA variant で
  `DenoiseVariantError` を投げ、何も書き込まないこと。

### 統合テスト（実Mitsuba、`tests/integration/test_mitsuba_stage_viewer.py` に追加）

- `test_denoise_off_final_render_writes_no_raw_sidecar`: denoise既定Falseの
  final render が `.raw.png` を作らないこと（既存動作からの無回帰）。
- `test_denoise_requires_cuda_variant_for_final_and_settled_preview`:
  `llvm_ad_rgb` で `render_final` と `render_preview(spp=None)` の両方が
  `DenoiseVariantError` を投げること、`render_preview(spp=1)`（interactive）
  は例外を投げず denoise もされないこと。
- `test_denoise_cuda_final_render_writes_raw_and_denoised_matching_stats`
  （`cuda_ad_rgb` 必須、`"cuda_ad_rgb" not in mi.variants()` で skip）:
  実 `mi.OptixDenoiser` で final render し、raw/denoised 両PNGが存在し
  互いに異なること、返り値の `stats` が「同一 session/config/seed で直接
  `core._render()` した raw pixel から計算した `_pixel_stats`」と
  `" denoise=optix"` 追記の形で完全一致することを検証した
  （PNG再読込ではなく直接の raw pixel 配列と比較 — `write_bitmap` の
  float→8bit 変換がロッシーなため、PNG往復比較では一致しないと判明し
  test を書き直した）。
- `test_denoise_cuda_applies_only_to_settled_preview`（同skip条件）:
  同一 `cuda_ad_rgb` core で interactive preview は denoise されず、
  settled preview のみ `denoise=optix` が付くこと。

cuda系テストは本機の GPU(`Quadro RTX 8000`, CUDA 13.1)上で実行し、
実際に `mi.OptixDenoiser` が動作することを確認した(plan の Step 5 で
本格検証する白バンドルの前段として、小サイズ合成volumeでの動作確認)。

variant切り替えについて: このテストファイルは `mitsuba` モジュールの
グローバル variant 状態を `StageCore.__init__`(`_load_mitsuba`)経由で
都度リセットしており、cuda系テストの前後にある全テストは自前で
`StageCore(variant=...)` を都度構築するため(既定 `llvm_ad_rgb`)、
cuda テストの追加が後続テストの ambient variant に影響しないことを
確認した(該当ファイル内で `TraversedPreviewScene`/`mi.render` を
`StageCore` を介さず直接呼ぶテストは、今回追加した4件より前にしか
存在しない)。

## 検証結果

実行場所は `vdbmat/`。GPU: `Quadro RTX 8000`(CUDA 13.1、`nvidia-smi` 確認済み)。

```text
uv run pytest -q tests/test_mitsuba_stage_core_denoise.py
8 passed in 0.68s

uv run pytest -q --ignore=tests/integration
606 passed in 38.17s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer.py -k denoise
4 passed, 38 deselected in 0.69s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer.py
42 passed, 2 warnings in 28.48s

uv run --group mitsuba-viewer pytest -q tests/integration/test_mitsuba_stage_viewer_regression.py
9 passed in 17.99s
```

（warningは Step 1 と同じ既知の非同期teardown由来で、本Stepの変更に起因
しない。）

```text
uv run ruff check examples/pipeline_run/demo/mitsuba_stage_core.py \
  tests/test_mitsuba_stage_core_denoise.py tests/integration/test_mitsuba_stage_viewer.py
All checks passed!

uv run ruff format --check (同上ファイル群)
3 files already formatted

git diff --check
問題なし
```

Step 2 完了条件「cuda ホストで、denoise on の final render が `.raw.png` と
デノイズ済み PNG の両方を出力し、PIXELSTATS が raw 側と一致する。off の
出力が従来と pixel-identical である。」を、上記の統合テストで実機確認した。

## コミット境界としての判断

Step 2 完了地点を独立したコミット境界とした。この境界で次が単独で成立する。

- `StageCore.render_final` / `render_preview` が `render.denoise` に応じて
  期待どおり raw/denoised を出し分ける(スタブ単体テストと実GPU統合テスト
  の双方で検証済み)。
- denoise 既定Falseの経路は無回帰(`.raw.png` を作らない、既存 final render
  テストが無改修で通過)。
- 非CUDA variant での denoise 要求は明示的に失敗する(黙って無視しない)。
- GUI（binder）・demo CLI・README はまだ未着手（Step 3 以降の範囲）。

変更対象は次の3fileのみ。

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_core.py`
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
- `vdbmat/tests/test_mitsuba_stage_core_denoise.py`(新規)

vdbmat submodule 側のコミット: `d7c79f6 denoise p0 step2: StageCore denoise
apply + raw output preservation`。

## 未実施事項

- Step 3: GUI（binder）checkbox、viewer 起動時の CUDA variant チェックに
  よる disabled 化、session 経由での denoise 記録・replay・digest 比較の
  確認。
- Step 4: `mitsuba_stage_demo.py --denoise`（`finalize_render_image` を
  `render_stage()` から呼ぶ配線を含む）、README_QUICK /
  stage viewer manual の追記。
- Step 5: 白バンドルでの一巡検証（GPU実測、report5.md）。
