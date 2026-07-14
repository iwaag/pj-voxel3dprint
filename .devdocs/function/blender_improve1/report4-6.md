# blender_improve1 実装報告 — Step 4〜6

- **対象計画**: `.devdocs/function/blender_improve1/plan.md`
- **実施範囲**: Step 4〜6
- **ステータス**: 完了
- **コミット相当の境界**: 決定的入れ子キューブ入力の追加から
  pipeline / Mitsuba / OpenVDB / Blender の end-to-end 完走と利用手順まで

## Step 4 — 決定的な入れ子キューブ

既存 Phase 1 fixture generator へ `nested_material_cube` を追加した。

- shape: `uint16[16, 16, 16]` (ZYX)
- voxel size: XYZ 各 0.001 m
- 外側: transparent-resin (ID 1)、3,880 cells
- 中央 `z/y/x = [5, 11)`: black-opaque-resin (ID 3)、216 cells
- 全外周セル: ID 1
- bounds: XYZ 各 0.0〜0.016 m

外周をすべて透明樹脂に固定したため、Mitsuba export の
`exterior-*.ply` は 1 group になり、Step 1〜3 で実装した hybrid helper の
入力契約を満たす。

追加・更新した主なファイル:

- `vdbmat/src/vdbmat/fixtures/phase1.py`
- `vdbmat/src/vdbmat/fixtures/__init__.py`
- `vdbmat/examples/pipeline_run/generate_fixtures.py` の既存出力対象
- `vdbmat/examples/pipeline_run/generate_configs.py`
- `vdbmat/examples/pipeline_run/inputs/nested_material_cube.material_id.npy`
- `vdbmat/examples/pipeline_run/inputs/nested_material_cube.voxels.json`
- `vdbmat/examples/pipeline_run/inputs/nested_material_cube.expected.json`
- `vdbmat/examples/pipeline_run/configs/nested_material_cube.run.json`

fixture と config は既存の再生成スクリプトから出力でき、
`.npy` の手修正は必要ない。解析的 summary には material count、
core index range、bounds、payload SHA-256 を記録した。

## Step 5 — end-to-end 検証

### Direct voxel と optical mapping

```text
vdbmat run examples/pipeline_run/configs/nested_material_cube.run.json
run: ok

vdbmat validate .local/blender_improve1/nested_material_cube --json
status: ok
checksums: ok
```

確認した optical range:

- IOR: 1.48〜1.52
- RGB absorption: 0.5〜6000 m^-1
- RGB scattering: 0〜100 m^-1
- g: 0〜0.1

単体テストでは、外側セルが透明材料の係数、中心セルが
黒色不透明材料の係数になることも直接検証した。

### Mitsuba exterior

```text
exterior-000.ply
interior-001.ply
interior-002.ply
```

- exterior は想定どおり 1 個。
- exterior PLY: 6,144 vertices / 3,072 faces。
- PLY bounds: X/Y/Z とも `[0.000000, 0.016000]` m。
- internal IOR boundary は orientation/IOR side の group により 2 PLY になるが、
  今回の Cycles 定性デモでは読み込まない。

### OpenVDB

- dimensions: `[16, 16, 16]`
- required grids: `cycles_absorption`, `cycles_scattering` を含む 10 grids
- `cycles_absorption`: active 4,096、min 1.16667、max 5000
- `cycles_scattering`: active 216、min/max 100
- `ior`: active 4,096、min 1.48、max 1.52
- black core の 216 cells だけに scattering 100 が入っているため、
  材料分布が VDB まで失われず到達している。

### Blender 4.5.11 LTS hybrid smoke

```text
HYBRID target=exterior-000 exterior=exterior-000.ply vdb=volume.vdb
scale=20
grids=cycles_absorption,cycles_scattering,g,ior,
      sigma_a_b,sigma_a_g,sigma_a_r,sigma_s_b,sigma_s_g,sigma_s_r
mode=qualitative-uncalibrated

PIXELSTATS min=0.0000 max=0.0039 mean=0.0003 std=0.0011
exit 0
```

生成物:

- PNG: 909,358 bytes
- `.blend`: 11,278,856 bytes

テンプレートが pinned Blender より新しい 5.1 系で保存されているため、
画像は Step 1〜3 時と同様にほぼ黒い。この点は依頼方針に従い、
光量、カラー管理、コンポジター、Blender 世代互換性の追加調査を行わず、
次の成立をもって完了とした。

- 同じボクセル入力から PLY と VDB が生成される。
- 両者の bounds / transform が合う。
- Cycles volume node が required grids を参照する。
- Blender が PNG と再調査可能な `.blend` を出力して正常終了する。

### テスト

```text
ruff check: pass

pytest -q tests/fixtures/test_pipeline_input_fixtures.py \
  tests/pipeline/test_pipeline_runner.py
27 passed

pytest -q
370 passed, 2 skipped
```

2 skip は host に `pyopenvdb` が無いことによる既知の native integration skip。
OpenVDB export / inspection、Blender render 自体は pinned Docker 内で実行済み。

## Step 6 — 利用手順

`README_QUICK.md` の手作り Blender シーン節に、次の完全な実行例を
追加した。

1. committed direct-voxel input から `vdbmat run`
2. Mitsuba exterior PLY export
3. pinned Docker 内の OpenVDB export
4. template scene への PLY + VDB hybrid render
5. PNG と調査用 `.blend` の保存

同節に次も明記した。

- qualitative / uncalibrated preview である。
- RGB 光学係数は Cycles 用スカラー値へ簡約される。
- internal IOR interface はレンダーされない。
- exterior PLY は現時点で正確に 1 個のみ対応。
- Docker 実行時は `--user "$(id -u):$(id -g)"` を使う。
- template は pinned Blender 4.5.11 LTS と互換性のある世代で保存する。

## 完了判定

Step 4〜6 は完了。これにより `blender_improve1` 計画全体のデータ経路と
利用手順は閉じた。

残っているのはレンダリング結果のアート・ライティング調整であり、
材料ボクセルから Blender hybrid scene までの機能成立を阻むものではない。
そのため本計画の追加 Step にはせず、必要になった時点で別タスクとする。
