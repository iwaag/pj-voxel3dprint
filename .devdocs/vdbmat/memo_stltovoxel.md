# メモ: STL → voxel マニフェスト外部ツール(実装延期)

Phase 1-side1 ではメッシュボクセル化の外部ツール化を **実施しない**。コアからは
mesh 入力パスを削除するため、既存実装の知見をここに残す。将来
`vbdmat-voxelize`(仮称)を実装する際の出発点。

## 既存実装の所在

削除前の実装は git 履歴に残る。削除コミット直前の参照:

- STL リーダ: `src/vbdmat/io/mesh.py`(ASCII/バイナリ両対応、サードパーティ依存なし)
- ボクセル化本体: `src/vbdmat/voxelize/mesh.py`(ADR-006 のメッシュパス)
- エラー型: `src/vbdmat/voxelize/errors.py`(`MeshTopologyError`, `VoxelizationError`)、
  `src/vbdmat/io/errors.py`(`MeshReadError`)
- テスト: `tests/voxelize/test_mesh_voxelize.py`, `tests/unit/`(io/mesh 分)
- 設計根拠: `docs/adr/0006-phase1-inputs-and-voxelization.md`
- 旧 pipeline-config の `MeshVoxelizationSettings`(`pipeline/config.py` v1)が
  ツールの CLI 引数設計の下敷きになる: `source_unit`, `voxel_size_xyz_m`,
  `material_id`, `material_name`, `placement`(4x4 rigid), `padding_cells`

実装を含む最後のコミット: `8f55562`(fix and docs, 2026-07)。
削除はその直後のコミットで行われた。復元は
`git show 8f55562:src/vbdmat/voxelize/mesh.py` などで可能。

## アルゴリズムの要点(mesh.py)

- **方式**: dense cell-centre 分類。各セル中心から +X 方向レイの signed winding
  number(三角形の向き付き交差の合計)で内外判定。watertight かつ一貫向き付けが
  前提なので |winding| >= 0.5 で内部。
- **表面上の点**: closed-solid 規則(ADR-006)により表面上のセル中心は内部扱い。
  `_points_on_surface()` が平面距離 `_SURFACE_TOLERANCE_M = 1e-9` +
  barycentric 判定で検出。
- **数値ジッタ**: セル中心が三角形分割の対角線(非物理的な共有辺)に乗るのを避ける
  ため、YZ サンプル点にサブボクセルオフセットを加える:
  `_SAMPLE_JITTER_Y = 7.3e-5`, `_SAMPLE_JITTER_Z = 3.1e-5`(ボクセル寸法比)。
  Y と Z で値を変えるのが重要(45 度対角線上に留まらないため)。
  ジッタは barycentric 判定のみに使い、winding 用 X 交点は無ジッタ中心で評価。
- **ドメイン構築**: AABB をボクセルサイズにスナップ
  (`_DOMAIN_SNAP_EPS = 1e-6`: float32 STL の丸めで余分なセルが増えないよう、
  整数セル数近傍を吸着)、その後 `padding_cells`(既定 1)を全側に付加。
  origin は `local_to_world` 平行移動として `placement @ translation(origin)` で合成。
- **規模上限(Phase 1 のガード)**: `_MAX_AXIS_CELLS = 128`,
  `_MAX_TOTAL_CELLS = 2_000_000`。超過は明示エラー(粗いボクセルを促す)。
  外部ツール化の際は上限を設定可能にしてよいが、dense 法の計算量
  (z×y ループ × 全三角形 barycentric)は O(cells × triangles) なので注意。

## トポロジ検証(inspect_topology)

受理条件: watertight・一貫向き付け・単一連結ソリッド。手順:

1. 頂点 weld: 座標を `max(scale,1)*1e-9` トレランスで整数キー化し `np.unique`。
2. 縮退面除去: weld 後の頂点重複、面積 <= `(max(scale,1))^2 * 1e-18` を拒否。
3. 辺検査: 無向辺は必ず 2 面(1 面=open、3 面以上=non-manifold)、
   有向辺は各向き 1 回ずつ(向き付け一貫性)。
4. union-find で辺共有による連結成分数 = 1 を要求(複数ソリッド拒否)。

## STL リーダの要点(io/mesh.py)

- バイナリ判定: 80 byte ヘッダ + uint32 カウントから期待長を計算し、
  ファイル長が厳密一致すればバイナリ。「solid」で始まっても長さ一致なら
  バイナリ扱い(実在するバイナリ STL が "solid" で始まるケース対策)。
- バイナリレコード: `<f4 normal(3), f4 vertices(3,3), u2 attribute>` = 50 byte。
  `np.frombuffer` で一括読み。normal は捨てる(向きは頂点順序から)。
- ASCII: トークン分割して `vertex` の後の 3 値のみ拾う寛容パーサ。
  頂点数が 3 の倍数でなければエラー。
- 単位: STL は無単位。`source_unit`(`m` / `mm`)を必ず外部から与える設計を維持。

## 将来のツール設計方針(Phase 1-side1 の契約に合わせる)

- 出力は Zarr 直書きではなく **`vbdmat.voxels` マニフェスト + checksummed .npy**
  (ADR-006)。書き出しヘルパはコアの `vbdmat.io.voxel_manifest` に
  `write_material_label_manifest()` を追加して共有するのが素直
  (image-stack ジェネレータの実装がその置き場所の前例になる予定)。
- マニフェスト `source` には `generator: "vbdmat-voxelize"`, `generator_version`,
  `identity`(入力 STL の sha256 など)を記録。
- 置き場所は `tools/vbdmat-voxelize/`(独立 pyproject、tool → core 依存は許容)。
- 旧 CLI `vbdmat voxelize` の引数一式(`--source-unit`, `--voxel-size`,
  `--material-id`, `--material-name`, `--padding` 等)は `cli/main.py` の
  削除前版を参照。
- 移設すべきテスト: `tests/voxelize/test_mesh_voxelize.py` の解析ケース
  (立方体・既知体積・単位等価性・縮退/open メッシュ拒否)+
  「ツール出力マニフェストをコアパイプラインがそのまま読める」round-trip。

## 落とし穴メモ

- float32 STL 丸めによりドメインが 1 セルぶれる → `_DOMAIN_SNAP_EPS` が対策。
  単位表現違い(mm 表記 vs m 表記)の同一形状でグリッドが一致することを
  テストしていた点を維持すること。
- winding 判定で `denom`(YZ 射影面積)が微小な三角形(X 軸にほぼ平行)は
  `facing` マスクで除外。除外分は表面判定側が補う。
- `_points_on_surface` は三角形ループで遅い。大メッシュ対応時の最適化第一候補。
