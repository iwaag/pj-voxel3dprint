# 使い方ガイド — ボクセルモデルの生成からレンダラー出力まで

このツールチェーンは、3Dプリント（マテリアルジョッピング）の外観シミュレーションを目的としたボクセルモデル生成・処理ツール群です。

| パッケージ | 役割 |
|-----------|------|
| **vdbmat-utils** | ボクセルファイル（STL・画像等）の生成・変換・処理 |
| **vdbmat** | ボクセルデータへの光学特性マッピング、レンダラー向けエクスポート |

## 環境セットアップ

```bash
# リポジトリのクローン（サブモジュール含む）
git clone --recurse-submodules https://github.com/iwaag/pj-voxel3dprint.git
cd pj-voxel3dprint

# vdbmat-utils のインストール
cd vdbmat-utils && uv sync && cd ..

# vdbmat のインストール
cd vdbmat && uv sync --locked && cd ..
```

> **注意:** `vdbmat`はPyPIに公開されていません。サブモジュールとして配置されたローカルパス依存として扱われます。

---

## ユースケース1: STLメッシュからボクセルモデルを生成する

vdbmat-utilsの`voxelize-mesh`コマンドで、STLメッシュをボクセルデータに変換します。

```bash
cd vdbmat-utils

# メッシュをボクセル化
uv run vdbmat-utils voxelize-mesh path/to/model.stl \
    --config mesh.json \
    --out output/ \
    --name model

# 結果をプレビュー（スライス表示）
uv run vdbmat-utils preview-slices output/model.voxels.json --axis z

# 材料ごとのボクセル数を統計
uv run vdbmat-utils material-counts output/model.voxels.json
```

**出力ファイル:**
- `output/model.voxels.json` — ボクセルマニフェスト（形状・材料定義・メタデータ）
- `output/model.material_id.npy` — ボクセル座標ごとの材料ID配列

**制約:**
- STLは watertight（密閉）かつ一貫した向きを持つ必要があります
- ソース単位（`source_unit`）の指定は必須です
- グリッドサイズが大きすぎる場合はエラーになります

---

## ユースケース2: 画像スタックからボクセルモデルを生成する

複数のPGM（またはPNG）スライス画像からボクセルモデルを構築します。

```bash
cd vdbmat-utils

# 画像スタックを変換
uv run vdbmat-utils convert-image-stack slices/ \
    --config stack.json \
    --out output/ \
    --name model

# 結果をプレビュー
uv run vdbmat-utils preview-slices output/model.voxels.json --axis z
```

**制約:**
- 各グレー値は設定ファイルの`levels`に宣言する必要があります
- 番号の欠落や画像サイズ不一致はエラーになります

---

## ユースケース3: キースライス間のボクセルを補間する（Morph）

複数のラベル付きスライス（キースライス）から、Signed Distance Field（SDF）を用いて材料IDを補間します。

```bash
cd vdbmat-utils

# スライス間の補間（ラベルは平均されず、SDFで補間される）
uv run vdbmat-utils morph-stack slices/ \
    --config morph.json \
    --out output/ \
    --name model
```

**特徴:**
- ファイル名の数値がZインデックスとして使用されます（例: `slice_0000.pgm`, `slice_0008.pgm`）
- 各ラベルごとに独立にSDF計算が行われ、材料IDは平均されません

---

## ユースケース4: プロシージャル形成（自然素材）を生成する

MarbleやGraniteのような自然素材のパターンを程序적으로生成します。

```bash
cd vdbmat-utils

# 大理石風パターンを生成
uv run vdbmat-utils generate-formation \
    --config examples/phase3/marble-like.formation.json \
    --out output/marble \
    --name marble-like \
    --strict

# 形成統計を表示
uv run vdbmat-utils formation-stats output/marble/marble-like.voxels.json

# スイープ（パラメータ変化）を実行
uv run vdbmat-utils sweep-formation \
    --config examples/phase3/tiny-sweep.sweep.json \
    --out output/sweep \
    --name tiny
```

**形成構成ファイルの主要フィールド:**
- `shape_zyx`: ボクセル形状 [Z, Y, X]
- `voxel_size_xyz_m`: ボクセルサイズ [X, Y, Z] m
- `palette`: 材料IDと名称のマッピング
- `layers`: ホスト、ベイン、フラクチャーストラータ等のレイヤー定義
- `seed`: 再現性のためのシード値

---

## ユースケース5: ボリューム演算パイプラインを適用する

Crop、Pad、Resample、Orient、Place、Apply-Mask、Compose、Remap-Materialsなどの演算をパイプラインとして適用します。

```bash
cd vdbmat-utils

# パイプラインを実行
uv run vdbmat-utils apply-pipeline \
    --config pipeline.json \
    --out output/ \
    --name result

# ドライラン（変更内容を確認のみ）
uv run vdbmat-utils apply-pipeline \
    --config pipeline.json \
    --out output/ \
    --name result \
    --dry-run
```

**サポートされる演算:**
| 演算 | 説明 |
|------|------|
| `crop` | 指定範囲で切り出し |
| `pad` | パディングで拡張 |
| `resample` | ボクセルサイズ変更 |
| `orient` | 方向変換 |
| `place` | 座標配置 |
| `apply-mask` | マスク適用 |
| `compose` | ボクセル合成 |
| `remap-materials` | 材料IDマッピング変更 |

---

## ユースケース6: ボクセルデータをvdbmatに入力する

vdbmat-utilsで生成したボクセルデータを、vdbmatの形式（Zarr）に変換します。

```bash
# vdbmat-utilsでボクセルファイルを生成
cd vdbmat-utils
uv run vdbmat-utils voxelize-mesh model.stl --config mesh.json --out output/ --name model

# vdbmatにインポート（Zarr形式に変換）
cd ../vdbmat
uv run vdbmat import-voxels output/model.voxels.json output/model.zarr
```

**出力:** `model.zarr/` — Zarr形式の材料ボクセルボリューム

---

## ユースケース7: 光学特性マッピングを実行する

vdbmatでボクセルデータに光学特性マッピングを適用し、レンダラー用の光学ボリュームを生成します。

```bash
cd vdbmat

# 光学マッピングパイプラインを実行
uv run vdbmat run examples/phase1/configs/window_coupon.run.json

# 結果を検証
uv run vdbmat validate .local/phase1/quickstart/window_coupon --json

# 出力バンドルをinspect
uv run vdbmat inspect .local/phase1/quickstart/window_coupon --json
```

**出力バンドルの内容:**
- `material.zarr` — 材料IDボクセルボリューム
- `optical.zarr` — 光学特性（屈折率・吸収係数・散乱係数等）ボクセルボリューム
- 検証・要計診断、設定、系譜情報、チェックサム

---

## ユースケース8: レンダラー向けにエクスポートする

vdbmatで生成した光学ボリュームを、各レンダラー向けにエクスポートします。

### Mitsuba用エクスポート

```bash
uv run --group mitsuba vdbmat export mitsuba \
     .local/phase1/quickstart/window_coupon \
     output/mitsuba/
```

### OpenVDB / Blender Cycles用エクスポート

```bash
# Dockerコンテナ内でOpenVDB/Cycles Proofを実行
docker build -t vdbmat-openvdb-cycles:blender4.5.11 \
     -f tools/Dockerfile.openvdb-cycles .

docker run --rm \
     -v "$PWD:/work" -w /work \
     vdbmat-openvdb-cycles:blender4.5.11 \
     python3 -m pytest -q tests/integration/test_blender_cycles.py
```

---

## 全体ワークフローまとめ

```
┌─────────────────────────────────────────────────────────────────────┐
│  vdbmat-utils                                                         │
│   ┌──────────────┐     ┌──────────────┐     ┌───────────────────┐   │
│   │ STLメッシュ     │     │ 画像スタック   │     │ プロシージャル     │   │
│   │ → ボクセル化   │     │ → 変換       │     │ 形成生成           │   │
│   └──────┬───────┘     └──────┬───────┘     └─────────┬─────────┘   │
│          │                     │                        │               │
│          └────────────────────┴───────────────────────┘               │
│                              │                                          │
│                      .voxels.json + .material_id.npy                    │
└──────────────────────┬───────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  vdbmat                                                                 │
│   ┌──────────────┐     ┌──────────────┐     ┌───────────────────┐   │
│   │ import-voxels │ →   │    run        │ →   │  export (Mitsuba/ │   │
│   │ (Zarr変換)     │     │ (光学マッピング)│     │  OpenVDB/Cycles) │   │
│   └──────────────┘     └──────────────┘     └───────────────────┘   │
│          │                     │                                        │
│          ▼                     ▼                                        │
│   material.zarr        optical.zarr                                    │
│    (材料ID)              (光学特性)                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## コマンド一覧

### vdbmat-utils

| コマンド | 説明 |
|----------|------|
| `voxelize-mesh` | STLメッシュをボクセル化 |
| `convert-image-stack` | 画像スタックをボクセル化 |
| `morph-stack` | キースライス間のSDF補間 |
| `apply-pipeline` | ボリューム演算パイプライン適用 |
| `generate-formation` | プロシージャル形成生成 |
| `formation-stats` | 形成統計表示 |
| `sweep-formation` | パラメータスイープ実行 |
| `preview-slices` | スライスプレビュー |
| `material-counts` | 材料統計 |
| `generate-fixture` | 合成フィクスチャ生成（テスト用） |

### vdbmat

| コマンド | 説明 |
|----------|------|
| `import-voxels` | ボクセルマニフェストをZarrに変換 |
| `run` | 光学マッピングパイプライン実行 |
| `validate` | ボクセルデータまたは出力バンドルを検証 |
| `inspect` | 出力バンドル内容を表示 |
| `export mitsuba` | Mitsuba用フォーマットにエクスポート |
| `export openvdb` | OpenVDB用フォーマットにエクスポート |

---

## 出力ファイル形式

### ボクセルマニフェスト（`.voxels.json`）

```json
{
   "format": "vdbmat.voxels",
   "format_version": "1.0.0",
   "asset_type": "material-label",
   "payload": {
     "path": "model.material_id.npy",
     "sha256": "...",
     "dtype": "uint16",
     "dimensions": ["z", "y", "x"]
   },
   "shape_zyx": [64, 64, 64],
   "voxel_size_xyz_m": [0.0001, 0.0001, 0.0001],
   "local_to_world": [...],
   "materials": [
     {"material_id": 0, "name": "air", "role": "background"},
     {"material_id": 1, "name": "transparent-resin", "role": "material"}
   ]
}
```

### 材料IDペイロード（`.material_id.npy`）

NumPy uint16配列。形状は`shape_zyx`、次元順序は`["z", "y", "x"]`。各要素は材料ID。

### Zarrボリューム（`.zarr/`）

Zarr v3形式。`material.zarr/`は材料ID、`optical.zarr/`は光学特性（屈折率・吸収係数・散乱係数）を保存。

---

## 参考ドキュメント

- [vdbmat README](vdbmat/README.md) — 詳細なアーキテクチャと設計
- [vdbmat-utils README](vdbmat-utils/README.md) — ユーティリティの詳細
- [vdbmat ADR一覧](vdbmat/docs/adr/) — 設計決定記録
- [vdbmat-utils ADR一覧](vdbmat-utils/docs/adr/) — ユーティリティ設計決定記録
- [vdbmat-utils 決定論性仕様](vdbmat-utils/docs/determinism.md)