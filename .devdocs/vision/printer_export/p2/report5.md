# Step 5 報告 — docs と README 統合

## 実施内容

### `vdbmat-utils/docs/image-stacks.md`

`rgb` levels スキーマの節を新規追加:

- PNG の入力受理条件を gray/rgb で書き分け（rgb は mode "P"/"RGB"、PGM
  不可）。
- gray/rgb 混在禁止、`format: "png"` 必須、既存の未宣言値エラー・重複検出・
  material_id/name/role 検証は共通機構であることを明記。

### `vdbmat-utils/docs/print-slices.md`

- claims を更新: 往復契約テスト（`test_print_slices_roundtrip.py`）が
  既定軸・軸交換/flip 全変種・異方性感度・等倍恒等・double-run で通って
  いる旨を明記し、「Phase 2」だった non-claim を claim へ移動。
  `convert-image-stack` が本エクスポータの色ラベル PNG スタックを直接
  受理することも claim に追加。
- 新節「Round-trip verification (`convert-image-stack`)」を追加:
  levels 導出規則（`palette` の全エントリ→`rgb`/`material_id`/`name`/
  `role`、背景含む）、`voxel_size_xyz_m` の再計算式（`pitch_*_mm` からの
  mm 逆算をしない理由の再掲）、`format`/`format_version` の厳密検証、
  手動コマンド例、`preview-slices`/`material-counts` での目視・照合手順。

### `vdbmat-utils/README.md`

- image-stack workflow の節へ rgb levels 対応を1文追加。
- print-slices export の節を「往復契約は Phase 2 スコープ外」から
  「往復契約は固定済み、実機受理のみ範囲外」に更新。

### `README_QUICK.md`

- Use Case 4d「Export Print Slices for GrabCAD Voxel Printing」を新規
  追加（generate → export → 目視/寸法確認 → 往復検証
  （convert-image-stack + preview-slices + material-counts）の順、既存
  Use Case の文体・コマンド形式に合わせた）。
- コマンド一覧表へ `export-print-slices` の行を追加（Phase 1 で
  未追加だった分、plan の指示どおり本フェーズで追加）。

## 確認

```text
uv run pytest -q tests/unit tests/contract   # 462 passed（変更なし、docsのみの変更のため回帰確認目的）
uv run ruff check .                          # 本フェーズ変更ファイルはすべてクリーン
                                              # （既存の無関係な1件のみ: tests/integration/test_formation_workflows.py、
                                              #   p1 report6 記載のとおり本フェーズ対象外）
```

Markdown のコードフェンス（```）の対応本数がすべて偶数であることを
確認し、崩れがないことを確認した。

## 次ステップへの申し送り

Step 6（手動 walkthrough）で、README_QUICK の Use Case 4d の記載どおりに
実際に CLI を通し、`roundtrip.json`（levels 導出済み config）の生成方法
含めて記録する。
