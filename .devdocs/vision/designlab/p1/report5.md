# Step 5 報告 — docs・手動 end-to-end 確認

## docs / README

- `vdbmat-utils/docs/primitive-arrays.md` を新規作成した。config 形、
  grid 導出式、cell-centre サンプリング規則（cube/sphere の内外判定、
  境界 tie 規則、`gap_m=0` での分離可能性の根拠）、claims/non-claims
  （光学テストパターンであり印刷プロセス・材料物性のシミュレーションで
  はない）、worked example（ASCII preview 込み）、下流連携コマンド例を
  記載した。
- `vdbmat-utils/README.md`: Status 節のコマンド一覧に
  `generate-primitive-array` を追加し、Usage 節に
  "Primitive-array workflow" 小節を追加した。
- `README_QUICK.md`: Use Case 4b として最小限の使用例
  （`generate-primitive-array` → `preview-slices`）を追加し、
  Command Reference の表に1行追加した（designlab GUI 全体の記述は
  Phase 2 で行う、という plan の指示どおり）。

## 手動 end-to-end walkthrough

`.local/designlab/p1/` 配下で実施した（git 管理外）。

1. **生成**: `primarray.json`（cube 3×2×1、size=4voxel、gap=2voxel、
   margin=1voxel、`transparent-resin`/`black-opaque-resin`）から
   `generate-primitive-array` で `demo.voxels.json` を出力。
   `1 (transparent-resin, material): 912` / `3 (black-opaque-resin,
   material): 384` を確認（`384 = 6 primitives * 4^3 voxels`、Step 2の
   unit test と同じ厳密値）。
2. **preview-slices**: z 中央スライスの ASCII preview で 3×2 個の
   cube 断面が明瞭に数えられることを目視確認（contract テストの
   golden と同一パターン）。
3. **import-voxels**: `demo.voxels.json` → `demo.zarr` の変換が
   `ok` で完了。
4. **run**: チェックイン済み `phase0-provisional-materials-v1`
   mapping（mapping ファイル追加なし、digest をそのまま指定）で
   `direct-voxel` input kind の run config を作成し `vdbmat run` を
   実行。全 stage（load / validate-material / persist-material /
   map-optics / validate-optical / persist-optical / summarize）が
   `ok`。`vdbmat validate --json` でも `checksums: ok` を確認。
   出力 bundle は `run.json` / `source/` / `material.zarr` /
   `optical.zarr` を持つ標準的な canonical run bundle 構造であり、
   既存viewerの Input カタログがそのまま検出できる形。
5. **目視確認（viewer 相当）**: 本開発環境はブラウザを操作できないため
   （`README_QUICK.md` の marble-like walkthrough と同じ制約）、viewer
   が内部で使うのと同じ `prepare_mitsuba_scene()` 経由の
   `mitsuba_stage_demo.py` で headless レンダーを行った。
   - checkerboard ステージでのレンダー（256x256, spp32）は完了し、
     `PIXELSTATS` が有意な分散を持つピクセルを記録（構造が存在する
     ことの間接確認）。
   - high-key preset（384x384, spp128, max_depth16）では、直方体上面に
     3×2 の明暗パターンがうっすら見える。ただし
     `black-opaque-resin` の吸収係数が非常に大きいため
     （phase0 mapping の uncalibrated 値、σa≈4000-6000/m）、
     6個の個別立方体としてクッキリ判別できるほどの視覚的コントラストは
     出ない。これは今回追加したジェネレータの不具合ではなく、
     既存の optical mapping・renderer 側の特性であり、plan の
     non-claims（"claims/non-claims: 光学テストパターンであり
     ... 印刷プロセスや材料物性のシミュレーションではない"）で
     許容範囲内と判断した。個数を確実に数えられることの一次証跡は
     material-id レベルの `preview-slices`（手順2）であり、そちらは
     明瞭。

## 完了条件の充足状況

- [x] `generate-primitive-array` が config JSON 1枚で決定論的に
      voxels 対を出力する。
- [x] 導出 shape・inclusion 数が unit test で厳密に固定されている
      （Step 2）。
- [x] 契約テスト（digest pin、double-run、ASCII preview、感度、
      seed非依存）が通る（Step 4）。
- [x] 既定 config の出力が `import-voxels` → `run`
      （チェックイン済み phase0 mapping、mapping ファイル追加なし）を
      通り、`preview-slices` で A×B×C 個が目視確認できる（本walkthrough
      手順1-4）。既存viewer（ブラウザ）そのものでの確認は環境制約により
      viewer 内部と同じレンダーパスでの代替確認とした。
- [x] docs / README が更新され、既存契約・既存テストに変更がない
      （`uv run pytest -q tests/unit tests/contract` は本 step 開始前と
      同じ 322 passed, 2 skipped のまま）。
- [x] 検証成果物が `.local/designlab/p1/` に隔離されている（git 管理外）。

## 静的検査・テスト結果（最終確認）

```
uv run ruff check .
uv run pytest -q tests/unit tests/contract
→ 322 passed, 2 skipped (PIL 未導入によるスキップ、無関係)
```

## 想定外事項

上記「目視確認」節に記載したレンダーの見えづらさ以外に想定外事項は
なかった。この点は不具合ではなく plan の non-claims の範囲内と判断して
続行した（人間判断が必要な事態ではないと判断）。
