# demo_improve1 実装計画 — 手作りシーンで入れ子キューブの内部不透明コアを可視化する

## 前提調査（確認済み事実）

`blender_template_swap.py` を pinned Docker image
（`vdbmat-openvdb-cycles:blender4.5.11`）上で実際に実行して確認した。

```
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/work" -w /work \
  vdbmat-openvdb-cycles:blender4.5.11 blender --background --python \
  vdbmat/examples/pipeline_run/demo/blender_template_swap.py -- \
  .local/local_demo/template_scene/cube_diorama.blend \
  .local/blender_improve1/nested_material_cube_mitsuba/exterior-000.ply \
  .local/blender_improve1/nested_material_cube_swap_demo.png --samples 96
```

- 実行は成功し、`PIXELSTATS std=0.1321` の空でないPNGが出力された。
- ただし出力画像は **中空のガラスキューブ** にしか見えない。中心の
  black-opaque-resin コアが写っていない。
- 原因: `vdbmat export mitsuba` は入れ子キューブ入力に対して
  `exterior-000.ply`（外側ドメイン境界、dielectric BSDF）と
  `interior-001.ply` / `interior-002.ply`（内部材質界面、
  `vdbmat/src/vdbmat/exporters/mitsuba.py:327-340` で
  `dielectric(int_ior=negative_ior, ext_ior=positive_ior)` として出力）を
  別ファイルに分けて書き出す。`blender_template_swap.py` は
  `--target-object` 1個に対して単一PLYを差し替える設計であり、
  `interior-*.ply` を読み込まない。
- `blender_template_hybrid.py`（exterior PLY + OpenVDB volume の吸収/散乱で
  内部を表現する既存の代替経路）も過去に同じ入力で試された形跡があるが
  （`.local/blender_improve1/nested_material_cube_hybrid.png`）、結果は
  真っ黒画像だった。[[blender_improve1]] の plan.md 自身が
  「代表 PNG の視認性は…深追いせず」と明記しており、この経路の
  可視性は未解決のまま完了扱いになっている。
- テンプレートシーン `cube_diorama.blend` には現状 `exterior-000`
  （material: `vbdmat-glass`）という配置アンカーが1個だけ存在する
  （`Volume` という別オブジェクトもあるが、これは hybrid 経路用で
  今回の対象ではない）。

以上から、今回の要求（入れ子キューブをブレンダーの手作りシーンで
実際にレンダリングして確認したい）に対しては、既存の
`blender_template_hybrid.py`（VDB密度ベース、過去に黒画像で未解決）を
デバッグするより、**Mitsuba export が既に幾何として書き出している
`interior-*.ply` をそのままオパーク材質のメッシュとしてシーンに追加する**
方が近道であり、既存資産の再利用度も高い。

## 規模判定

新しいフェーズやロードマップは不要。既存資産として

- `vdbmat export mitsuba` が生成する `exterior-*.ply` / `interior-*.ply`
- `examples/pipeline_run/demo/blender_template_swap.py` のテンプレート展開・
  メッシュ差し替え・レンダー処理
- `.local/local_demo/template_scene/cube_diorama.blend` の手作りシーン
- 入力ボクセル `vdbmat/examples/pipeline_run/inputs/nested_material_cube.*`
  と対応する `vdbmat run` 設定 `configs/nested_material_cube.run.json`

が揃っている。必要なのは `interior-*.ply` を無視している現行スクリプトの
拡張とデモ用検証のみであるため、単一の function 実装計画として進める。

## ゴール

`blender_template_swap.py` の後継として、同一テンプレート・同一アンカーに

1. `exterior-*.ply` を現行どおり Glass BSDF の外殻として配置する。
2. `interior-*.ply` を新規に読み込み、オパーク材質（Diffuse/Glossy BSDF、
   黒に近い色）のメッシュとして同じ transform 内に配置する。

を1回の Blender 実行で行い、「透明樹脂の外側キューブの中央に
black-opaque-resin の不透明コアが見える」PNGを生成できるようにする。

代表検証は既存の `nested_material_cube` 入力
（air / transparent-resin / black-opaque-resin）を使う。

## 非ゴールと表示の性格

- `interior-*.ply` が Mitsuba 用に持つ `dielectric(int_ior, ext_ior)`
  BSDF 情報は使わない。Cycles 側では内部 IOR 境界の屈折を再現せず、
  単純な不透明材質として塗る（[[blender_improve1]] の非ゴール
  「内部 IOR 境界は Cycles へ渡さない」と同じ方針を踏襲する）。
- コア材質の色は `phase0-provisional-materials-v1.optical-mapping.json`
  の `sigma_a_rgb_per_m` からの物理的な逆算はしない。暫定的に
  「ほぼ黒・非透過」を表す固定 BSDF 値を割り当てるデモ用途と明記する。
- 3種類以上の材質が入れ子になった任意の入力（`interior-*.ply` が
  3個以上、または材質ごとに異なる不透明度が必要なケース）は対象外。
  今回は `nested_material_cube`（材質は air / transparent-resin /
  black-opaque-resin の3種のみ、`interior-*.ply` は2枚）に閉じる。
- `blender_template_hybrid.py`（VDB密度経路）の黒画像バグは本計画では
  修正しない。別経路として現状維持する。

## 実装ステップ

### Step 1 — スクリプトの拡張方針の固定

- 既存の `blender_template_swap.py` は壊さず、新規に
  `examples/pipeline_run/demo/blender_template_swap_nested.py` として
  分離するか、`--interior-ply` を複数回指定可能なオプションとして
  同スクリプトに追加するかを決める（後者を推奨: swap の基本ロジック
  ―テンプレートを開く、target の bounds center に合わせる、
  render して PIXELSTATS を出す―を再利用できるため）。
- CLI 引数: `TEMPLATE_BLEND EXTERIOR_PLY OUTPUT_PNG
  [--target-object exterior-000] [--samples 96]
  [--interior-ply PATH ...]`
- `--interior-ply` は0個以上（0個なら現行動作と完全互換）。

### Step 2 — interior メッシュの配置

- `exterior-000.ply` を差し替える際に得た `desired_center` と
  `target.matrix_world` の回転・スケールを再利用し、各 `interior-*.ply`
  も同じ transform（回転・一様 scale・平行移動）でシーンに配置する。
  `_bounds_center` と同じロジックで interior メッシュのローカル中心を
  target の中心に一致させる。
- 一様 scale / 回転のみを許容し、非一様 scale や shear は
  `blender_improve1` の方針を踏襲して明示エラーとする。
- interior オブジェクトは target と同じ collection に link する。

### Step 3 — オパーク材質の割り当て

- interior メッシュ用に新規マテリアルを1個作成する
  （`vdbmat-interior-opaque` のような固定名）。Diffuse BSDF（もしくは
  わずかな Glossy 成分を混ぜた BSDF）、色は暗めのグレー〜黒固定値。
- 複数 `interior-*.ply` がある場合は全て同じマテリアルを使う
  （`nested_material_cube` では2枚とも同一の transparent-resin /
  black-opaque-resin 境界面なので問題ない）。

### Step 4 — レンダーと検証出力

- レンダーは既存の `blender_template_swap.py` と同じ:
  Cycles 固定、View Layer 有効チェック、`--samples` 指定、
  PNGへ書き出し、`PIXELSTATS`(min/max/mean/std) をログ出力する。
- ログに `interior_count=N`（読み込んだ interior メッシュ数）を追加する。
- 既存の mitsuba export 済みアセット
  （`.local/blender_improve1/nested_material_cube_mitsuba/`）を使って
  実際にレンダーし、
  `.local/blender_improve1/nested_material_cube_swap_nested_demo.png`
  のような出力先に保存する。

### Step 5 — 目視確認

- Step 4 の出力画像を確認し、中心の black-opaque-resin コアが
  ガラス外殻越しに視認できることを確認する。
- 参考として Step 4 の1件は「exterior のみ」（今回既に取得済みの
  `nested_material_cube_swap_demo.png`）と比較し、コアの有無で
  差分が出ることを確認する。画像ハッシュの完全一致は完了条件にしない。

### Step 6 — 文書化

- `README_QUICK.md` の手作りシーン節、または
  `.local/local_env_memo.md` に、`--interior-ply` オプションの使い方と
  「Cycles では内部 IOR 境界を再現せず単純な不透明材質で近似する」旨を
  一言追記する。

## 実施順序

Step 1 → Step 2 → Step 3 で最小限の「外殻+コア」表示を成立させる。
Step 4 で既存アセットを使った実レンダー検証を行い、Step 5 で目視確認、
Step 6 で使用方法を追記して閉じる。

## 完了条件

- `exterior-000.ply` のみを指定した場合、既存 `blender_template_swap.py`
  と同一の出力になる（後方互換）。
- `--interior-ply` を1個以上指定した場合、外殻と同じ transform で
  オパーク材質の内部メッシュが配置される。
- `nested_material_cube` の mitsuba export（`exterior-000.ply` +
  `interior-001.ply` + `interior-002.ply`）を入力に、pinned Docker
  環境で1コマンドのBlender実行により、透明外殻越しに中心の不透明コアが
  見えるPNGを生成できる。
- 内部 IOR 境界を再現しないこと、コア材質色が暫定固定値であることが
  文書に明記される。

## リスクと打ち切り条件

- **interior メッシュの法線/シェーディングが不自然に見える場合**:
  `interior-*.ply` は元々2つの材質界面（negative_ior側・positive_ior側）
  として書き出されており、法線の向きがCycles上で見た目に影響する
  可能性がある。裏面カリングやシェーディングスムージングの調整のみで
  対応し、ジオメトリの作り直しはしない。
- **コアの視認性がなお乏しい場合**: 照明・露出はテンプレート側の設定を
  優先し、デモ用に露出補正オプションを1個追加する程度に留める。
  物理的な光学校正は行わない。
- **3種類以上の材質・複数コアを持つ入力への一般化が必要になった場合**:
  本計画は `nested_material_cube` 相当の単純な入れ子構造に閉じ、
  一般化は別 function として切り出す。
