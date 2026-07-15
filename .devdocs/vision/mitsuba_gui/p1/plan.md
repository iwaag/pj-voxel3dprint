# mitsuba_gui Phase 1 実装計画 — StageConfig 抽出とプリセット契約

親ロードマップ: `.devdocs/vision/mitsuba_gui/roadmap.md`（Phase 1）。

## 前提調査（確認済み事実）

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`（233行）が対象。
  構成は `_parse_args()` / `_load_mitsuba()` / `_scene_bounds()` /
  `_checkerboard_bsdf()` / `_add_stage()` / `main()`。
- stage パラメータは現在すべて `_add_stage()` 内のハードコード値:
  - backdrop: 距離 `radius*2.2`、スケール `radius*2.6`、
    teal `(0.02, 0.09, 0.11)` / orange `(0.85, 0.5, 0.12)` の市松
  - floor: `minimum[2] - radius*0.1` の高さ、スケール `radius*6.0`、
    indigo `(0.03, 0.03, 0.13)` / yellow `(0.82, 0.76, 0.14)` の市松
  - key light: 方向 `(-1.0, -1.5, 2.1)` 正規化、距離 `radius*3.5`、
    スケール `radius*1.0`、radiance `[6.4, 5.6, 4.2]`
  - 市松の格子数のみ CLI `--checker-scale`（既定 8）で調整可能
- カメラ（sensor）と白色 backlight は `prepare_mitsuba_scene()` が生成する
  canonical な scene_dict エントリであり、本デモは一切触っていない
  （`scene_dict = dict(prepared.scene_dict)` のコピーに stage 要素を
  additive に追加するだけ）。`_scene_bounds()` はexporter の private
  `_scene_frame` と同じ center/radius/camera_direction
  （`(1.6, -2.2, 1.4)` 正規化）を public API のみで再計算した重複実装。
- スクリプトは `uv run --group mitsuba python examples/pipeline_run/demo/
  mitsuba_stage_demo.py -- ...` で起動される。Python はスクリプトの
  ディレクトリを `sys.path` に載せるため、同ディレクトリの sibling module は
  `import` できる（`blender_template_hybrid.py` 等と同じ配置規則の範囲内で
  モジュール分割が可能）。
- レンダーは `MitsubaExportConfig(width, height, spp)` を
  `prepare_mitsuba_scene()` に渡し、`mi.load_dict()` → `mi.render(scene,
  seed=config.seed, spp=config.spp)`。seed固定・同一ホストで決定的な出力が
  得られており、`PIXELSTATS min/max/mean/std` が回帰シグナル。
- 確認済みベースライン（[[mitsuba_improve1]] report）:
  `nested_material_cube` で `PIXELSTATS min=0 max=21.0502 mean=0.100658
  std=0.183592`（512²/spp128、約5.8秒）。

## 規模判定

親ロードマップの Phase 1 のみを扱う単一 function 相当。新規依存なし
（dataclass＋標準ライブラリの json で足りる。pydantic 等は導入しない）。
GUI（viser）は Phase 2 であり本計画に含めない。

## ゴール

1. stage パラメータを集約した `StageConfig`（dataclass、JSON round-trip
   可能）と、`build_stage_scene()` 相当の純関数群を sibling module
   `examples/pipeline_run/demo/mitsuba_stage.py` に切り出す。
2. `mitsuba_stage_demo.py` に `--stage-config PATH` を追加し、プリセット
   JSON からライト・カメラ・背景を変えた絵を headless で再現できるようにする。
3. 引数なし（プリセット未指定）の既定出力を現行とピクセル同一に保つ。
4. サンプルプリセット2点（既定値そのもの＋バリエーション1つ）を git 管理で
   `examples/pipeline_run/demo/presets/` に置く。

## 設計の芯: canonical エントリは「デフォルト passthrough、明示時のみ上書き」

ロードマップはカメラと backlight radiance を調整対象に含めるが、これらは
`prepare_mitsuba_scene()` が生成する canonical エントリである。そこで:

- `StageConfig` のカメラ節・backlight 節は **既定値 `null`（None）** とし、
  None の間は `prepared.scene_dict` の `sensor` / backlight エントリに
  一切触れない（現行と同じ passthrough）。
- ユーザーがプリセットで明示した場合のみ、scene_dict の**コピー上で**
  該当エントリを demo 側が組み立てた dict に差し替える。カメラは
  `_scene_bounds()` と同じ center/radius から方位角・仰角・距離倍率・FOV で
  `look_at` を構築する。
- この規則により「既定出力のピクセル同一」が検証頼みでなく構造的に保証され、
  canonical exporter のコード（`prepare_mitsuba_scene` / `render_mitsuba` /
  `MitsubaExportConfig`）は従来どおり無変更のまま維持される。

## StageConfig のスキーマ（初期スコープ）

```
StageConfig
├── render:    width=512, height=512, spp=128        # 現行CLI既定と同値
├── backdrop:  enabled=true, pattern="checker"|"solid",
│              distance_factor=2.2, scale_factor=2.6,
│              checker_scale=8, color0=(0.02,0.09,0.11),
│              color1=(0.85,0.5,0.12)
├── floor:     enabled=true, pattern, drop_factor=0.1,
│              scale_factor=6.0, checker_scale=8,
│              color0=(0.03,0.03,0.13), color1=(0.82,0.76,0.14)
├── key_light: enabled=true, direction=(-1.0,-1.5,2.1),
│              distance_factor=3.5, scale_factor=1.0,
│              radiance=(6.4,5.6,4.2)
├── camera:    null | {azimuth_deg, elevation_deg,
│              distance_factor, fov_deg}              # null=canonical passthrough
└── backlight: null | {radiance=(r,g,b)}              # null=canonical passthrough
```

- 全フィールドの既定値は現行ハードコード値と同一。既定 StageConfig →
  現行出力、が成り立つ。
- `pattern="solid"` は `color0` 単色 diffuse（市松の代わり）。柄種別の
  本格的な拡張（グリッド等）は Phase 2 以降で必要になってから足す。
- JSON は `{"format": "vdbmat.stage-config", "format_version": "1.0.0", ...}`
  のヘッダを持たせ、未知キー・型不一致・範囲外値（負のspp等）は明示的に
  エラーにする（既存 `.voxels.json` マニフェストの流儀を踏襲）。
- 部分指定を許す: JSON に無い節・フィールドは既定値で補完する
  （バリエーションプリセットが差分だけ書けるように）。

## 非ゴール

- canonical exporter 配下のコード変更、medium・exterior/interior mesh の
  BSDF/幾何の変更（従来どおり）。
- GUI（viser）・dependency group 追加・`mi.traverse()` 差分更新
  （Phase 2 / Phase 3 のスコープ）。
- 新規の外部依存（pydantic 等）。dataclass＋手書きバリデーションで足りる。
- 柄種別の拡充（checker / solid の2種のみ。グリッド・グレーカード等は保留）。
- `blender_*_demo.py` 側への同種リファクタの波及。

## 実装ステップ

### Step 1 — `mitsuba_stage.py` モジュール新設（ロジック移設）

- `examples/pipeline_run/demo/mitsuba_stage.py` を新設し、以下を移す/新設する。
  - `StageConfig` と下位 dataclass 群（上記スキーマ）。
  - `stage_config_from_json(path) -> StageConfig` /
    `stage_config_to_json(config) -> dict`（round-trip、部分指定補完、
    バリデーション）。
  - `scene_bounds(geometry)`（現 `_scene_bounds()` の移設。public API のみ
    使用という現行の境界コメントを維持）。
  - `apply_stage(mi, scene_dict, geometry, config) -> None`
    （現 `_add_stage()` + `_checkerboard_bsdf()` の一般化。config の値で
    backdrop / floor / key light を構築し、`camera` / `backlight` が
    None でなければ該当エントリを差し替える）。
- `mitsuba_stage_demo.py` は argparse・zarr読み込み・
  `prepare_mitsuba_scene()` 呼び出し・レンダー・PIXELSTATS 出力を担う
  薄い CLI となり、stage 構築は全て `mitsuba_stage` を import して使う。

### Step 2 — CLI 統合

- `--stage-config PATH` を追加。指定時は JSON を読んで `StageConfig` を得る。
  未指定時は `StageConfig()`（全既定値）。
- 既存 CLI 引数の扱い: `--width/--height/--spp/--checker-scale` は
  StageConfig の該当フィールドへの**最終上書き**として残す
  （プリセットより CLI が優先。既存の呼び出し例が挙動を変えないため）。
  `--checker-scale` は backdrop / floor 両方の `checker_scale` に効く
  （現行挙動と同じ）。
- モジュール docstring と `--help` にプリセットの使い方を追記する。

### Step 3 — サンプルプリセットの整備

- `examples/pipeline_run/demo/presets/stage-default.stage.json`:
  既定値を全フィールド明示で書き出したもの（スキーマの見本を兼ねる）。
- `examples/pipeline_run/demo/presets/stage-highkey.stage.json`:
  バリエーション1つ（例: key light を強め・カメラをやや俯瞰・floor を
  solid にする等、差分指定のみで書く部分指定の見本）。
- いずれも git 管理に含める（ローカル環境情報を含まない設定サンプルのため
  可。`.local/` 規律の対象外であることは `local_env_memo.md` の
  「サンプルパラメータファイルは git 管理に含めて良い」に合致）。

### Step 4 — 検証

- **既定出力のピクセル同一**: リファクタ前の HEAD で
  `nested_material_cube` をレンダーした PNG（`.local/` に保存）と、
  リファクタ後の引数なし実行の PNG を numpy で読み比べ、全画素一致を確認
  する。`--stage-config presets/stage-default.stage.json` 指定時も同一で
  あること（既定値プリセットの正しさの検証を兼ねる）。
- **プリセットの効果**: `stage-highkey.stage.json` で PIXELSTATS が変化し、
  目視でライト・カメラ・床の変更が画像に反映されていることを確認する。
- **round-trip**: `StageConfig()` → JSON → `StageConfig` の同値性、
  未知キー・型不一致・範囲外値が明示的にエラーになることを、demo-track
  の軽量テスト（スクリプト内 self-check または `.local/` での手動確認）で
  確認する。
- **複雑入力**: `marble-like` の `optical.zarr` でもプリセット指定込みで
  エラーなくレンダーされることを確認する。
- 静的検査: `ruff check` と `py_compile` を新旧両ファイルに対して通す。
- 動作確認の入出力は `.local/mitsuba_gui/p1/` にまとめ、git 管理しない。

### Step 5 — 文書化

- `README_QUICK.md` の Mitsuba stage 節に `--stage-config` とサンプル
  プリセットの使用例を追記する（「GUI は Phase 2、プリセット JSON が
  headless 再現の契約」という位置づけを一言添える）。

## 実施順序

Step 1 → 2 で headless のプリセット経路を成立させ、Step 3 で見本を置き、
Step 4 で同一性・効果・round-trip を検証、Step 5 で文書化して閉じる。

## 完了条件

- `mitsuba_stage.py`（StageConfig＋純関数）が新設され、
  `mitsuba_stage_demo.py` が薄い CLI になっている。
- 引数なし実行の出力がリファクタ前とピクセル同一
  （PIXELSTATS 一致では足りず、全画素一致で確認する）。
- プリセット JSON でライト・カメラ・背景を変えた絵が headless で再現でき、
  既定値プリセットは無指定と同一の絵を出す。
- サンプルプリセット2点が git 管理で置かれ、部分指定が機能する。
- canonical exporter・medium・境界メッシュに差分がない（git diff で確認）。
- 新規外部依存なし（`pyproject.toml` に差分がない）。

## リスクと打ち切り条件

- **ピクセル同一が保てない場合**: 原因を特定するまで完了としない。
  移設に伴う浮動小数点の評価順序変更など正当な理由による微差のみ、
  差分画素数と最大差を明記した上で許容判断する（ロードマップのリスク欄
  どおり）。ハードコード値の転記ミスはこの検証で必ず露見する。
- **カメラ上書きの look_at 構築が canonical sensor と整合しない場合**
  （例: FOV軸・up ベクトル規約の食い違いで、canonical 相当の値を指定しても
  同じ構図にならない）: passthrough 設計により既定挙動には影響しないため、
  上書き時の規約（方位角の基準軸等）を docstring に明記して閉じる。
  canonical `_sensor_dict` との厳密一致は要件にしない。
- **部分指定補完の実装が複雑化する場合**: ネスト2段（節→フィールド）まで
  の補完に限定し、それ以上の柔軟性（配列のマージ等）は要求しない。
- **`pattern="solid"` の追加が checkerboard 前提の関数を歪める場合**:
  BSDF 構築を pattern ごとの小関数に分けるだけに留め、プラグイン的な
  抽象化はしない（柄種別の本格拡張は Phase 2 以降の必要時）。
