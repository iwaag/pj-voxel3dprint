# Step 4 報告 — 往復契約テスト（`test_print_slices_roundtrip.py`）

## 実施内容

`vdbmat-utils/tests/contract/test_print_slices_roundtrip.py` を新規作成。
すべて「`export_print_slices()` → 出力マニフェストから
`image_stack_config_from_print_manifest()` で config 導出 →
`convert_image_stack()`」の順で固定する。

1. **既定軸の往復完全一致**（`test_default_axes_round_trip_matches_sampler`）:
   `multimaterial` fixture（非対称ラベル、4材料）で `material_id` 配列が
   `sample_slice()` を全 z 積んだ配列と完全一致、`voxel_size_xyz_m` が
   プリンタピッチと一致、palette の material_id 集合・role が入力と一致。
2. **軸交換・flip 変種**（`test_axis_swap_and_flip_variants_round_trip_match`）:
   `printer_x_axis`/`printer_y_axis` 交換、`flip_x`/`flip_y`/`flip_z` の
   各ケースで同じ非対称入力に対し全数一致。
3. **異方性リサンプリング感度**
   （`test_anisotropic_resampling_matches_independent_nearest_neighbour`）:
   等方 100 µm ソース → 既定 600/300 dpi + 27 µm。期待値は
   `printer.sampler` を一切 import せず、テスト内で直接 numpy で書いた
   `clip(floor(center/src_size))` 計算（plan のリスク節「往復一致が同じ
   バグの両側で偽装される」への対策どおり、sampler 非依存の外部基準）。
   `width/nx > height/ny` で X:Y 異方性の向きも確認。
4. **等倍ケース**（`test_exact_pitch_identity_round_trip`）: ソース
   voxel_size をピッチと厳密一致させ、往復結果がソース配列そのものと
   恒等になることを確認（サンプリングの退化ケース、こちらも sampler 非
   依存 — 出力形状がソース形状と一致することと配列の直接比較のみで
   判定）。
5. **double-run**（`test_double_run_stack_identity_matches`）: 往復全体
   （export → derive → convert）を2回実行し、`stack_identity()`
   （`image/stack.py` の既存関数、provenance ベースの identity）が一致。

いずれも初回実装で全ケースが一発で通過し、Phase 1 側（sampler /
exporter）への修正は不要だった（plan の Step 4-6 に該当する Phase 1 fix
は発生しなかった）。

## 実行結果

```text
uv run pytest -q tests/contract/test_print_slices_roundtrip.py   # 5 passed
uv run pytest -q tests/unit tests/contract                       # 462 passed（p2 step3完了時 457 + 5、回帰なし）
uv run ruff check tests/contract/test_print_slices_roundtrip.py  # clean
```

## 完了条件の確認

roadmap Phase 2 の中心条件「往復契約テストがCIで通る」を本ステップで
充足した。levels は Step 3 のヘルパで機械導出され、手書きの対応表には
一切依存していない。

## 次ステップへの申し送り

Step 5（docs・README統合）で、本テストが通っている事実を
`docs/print-slices.md` の claims に反映し、README_QUICK へ Use Case を
追加する。
