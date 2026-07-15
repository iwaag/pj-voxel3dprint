# mitsuba_improve1 実装計画 — Mitsuba出力に判断材料のあるステージ背景を足す

## 前提調査（確認済み事実）

`vdbmat export mitsuba --render` を実際にホスト上(`uv run --group mitsuba`、
Docker不要)で `nested_material_cube` に対して実行し、
`.local/local_demo/nested_material_cube_mitsuba_render/render.png` を得た
（64×64、`MitsubaExportConfig` のデフォルト解像度）。

- Mitsubaの`heterogeneous`媒質は`sigma_t`/`albedo`をボクセルごとの連続密度場
  （`gridvolume`）としてそのまま受け取る設計（
  `vdbmat/src/vdbmat/exporters/mitsuba.py:265-304`）。境界メッシュ
  （`exterior-*.ply` / `interior-*.ply`）はIOR境界の屈折表現用の副産物で、
  内部の濃淡自体はメッシュ化されない。したがって微細・統計的な内部分布
  （例: ガウシアン分布した不透明インクルージョン）は、Blenderのswap方式
  （境界をポリゴン化して単色BSDFで塗る）より原理的に素直に扱える。
  この経路は`tests/integration/test_mitsuba.py`の
  `test_every_fixture_scene_loads_and_renders`で全synthetic fixtureに対して
  end-to-endテストされており、Blenderの OpenVDB hybrid 経路
  （[[demo_improve1]] 前段で確認した「過去に真っ黒画像で未解決」）と違い、
  既に動作実績がある。
- ただし現在のシーン（`_sensor_dict` / `_backlight_dict`,
  `vdbmat/src/vdbmat/exporters/mitsuba.py:435-495`）は、物体の背後に置いた
  単色白色の平面光源ひとつだけで、床も背景パターンもない。ユーザーが
  実際に画像を見た所感は「白背景に何かキューブっぽいものが見える」で、
  屈折・吸収がどのパターンに対して起きているのか判断できない。
- これはBlenderの`blender_glass_demo.py`が最初に直面したのと同じ問題
  （ドキュメント曰く「素のシーンだと透明物体はほぼ不可視」）であり、
  同スクリプトは模様入り背景・床・環境光を足す「lit stage」を追加する
  ことで解決した。Mitsuba側にも同種のステージを足すのが妥当。
- `render_mitsuba()` / `prepare_mitsuba_scene()` は
  「canonical pipeline boundary より下」に明記された科学的検証用アダプタ
  （`vdbmat/src/vdbmat/exporters/mitsuba.py`のモジュールdocstring、
  および`vdbmat/src/vdbmat/exporters/runner.py:76-79`のコメント）であり、
  デコリメンタード/デターミニスティックな出力に固定係数のstage要素を
  混ぜるべきではない。既存の`blender_glass_demo.py` /
  `blender_template_swap.py` / `blender_template_hybrid.py`は全て
  「demo-track helper、canonical pipelineの一部ではない、
  qualitative・uncalibrated」と明記して`examples/pipeline_run/demo/`に
  分離されている。Mitsuba側も同じ境界線を踏襲する。

## 規模判定

新しいフェーズやロードマップは不要。既存資産として

- `vdbmat.exporters.mitsuba.prepare_mitsuba_scene()`
  （medium・exterior/interior mesh・sensorを含むloadable scene dict）
- `vdbmat.exporters.mitsuba.MitsubaExportConfig`
  （width/height/spp/seed等の検証済み設定）
- `vdbmat.core.geometry.GridGeometry.continuous_index_to_world()` などの
  public API（`_scene_frame`と同じ中心・半径計算をprivate helperを
  importせず再現できる）
- 既存の複雑な入力サンプル
  （`examples/formation_generation/marble-like.formation.json`、
  複数のinterior境界を持つ`marble_mitsuba`実行例）
- `examples/pipeline_run/demo/blender_glass_demo.py` の
  「lit stage」設計（模様背景・床・環境光で判断材料を与える）

が揃っている。必要なのは、これらを土台にした新規デモスクリプト1本の追加
とその検証であるため、単一の function 実装計画として進める。

## ゴール

`vdbmat.exporters.mitsuba.prepare_mitsuba_scene()` が返す scene_dict
（medium と exterior/interior mesh は変更しない）に、次を additive に
足した新規デモスクリプトを作る。

1. 物体の背後に、市松模様などの認識しやすいテクスチャを持つ diffuse
   backdrop plane。
2. 物体の下に、同様のテクスチャまたはグリッドを持つ diffuse floor plane。
3. 奥行き・輪郭が読み取れるよう、既存の白色 backlight に加えて
   斜め方向からの key light を1個追加。
4. デモ用に十分な解像度・sppに引き上げた render
   （canonical `DEFAULT_MITSUBA_CONFIG` の 64×64/spp32 は変更しない。
   デモ側だけ独自の高解像度設定を使う）。

代表検証は次の2入力で行う。

- `nested_material_cube`（単純な入れ子キューブ、[[demo_improve1]] の
  BlenderデモとMitsuba側で見た目を比較できる）。
- `marble-like` formation（境界群が複数に分かれた複雑な入力の代理。
  本物のガウシアン分布インクルージョン fixture は非ゴールとする）。

## 非ゴールと表示の性格

- `prepare_mitsuba_scene()` / `render_mitsuba()` / `MitsubaExportConfig`
  など canonical pipeline boundary 配下のコードは変更しない。
  stage要素は呼び出し側（デモスクリプト）でscene_dictに追記するだけに
  留める。
- medium（`sigma_t`/`albedo`）と exterior/interior mesh のBSDF・幾何は
  変更しない。科学的な光学係数には一切手を入れない。
- 新規のガウシアン分布インクルージョン fixture（材質ボクセル生成）は
  本計画に含めない。既存の `marble-like` formation を複雑ケースの代理と
  する。専用fixtureが必要になった場合は別 function として切り出す。
- Blenderの`cube_diorama.blend`のような作り込まれた背景アセット
  （書籍・家具等の3Dモデル）は用意しない。Mitsuba側はプロシージャルな
  市松模様と単純な平面ジオメトリのみで「読める」ことを狙う。
  写実的な部屋の再現は目的ではない。
- 解像度・spp・カメラ距離などのデモ用既定値は固定の qualitative preset
  とし、被写体ごとの自動最適化は行わない。

## 実装ステップ

### Step 1 — 入力契約とシーン拡張方針の固定

- 新規ファイル `examples/pipeline_run/demo/mitsuba_stage_demo.py` を追加する。
  既存の `render_mitsuba()` 等は変更しない。
- CLI 引数: `OPTICAL_ZARR OUTPUT_PNG [--width 512] [--height 512]
  [--spp 128] [--checker-scale N]`。
- `vdbmat.io.zarr.read_volume`（または既存exporterが使っているのと同じ
  読み込み経路）で `OpticalPropertyVolume` を読み、
  `prepare_mitsuba_scene()` にデモ用の高解像度 `MitsubaExportConfig` を
  渡して base scene_dict を得る。
- `volume.geometry.continuous_index_to_world()` と `shape_xyz` を使い、
  `_scene_frame` と同じ center/radius/camera_direction を
  デモスクリプト側で再計算する（private helper はimportしない）。

### Step 2 — 背景・床・追加ライトの構築

- 市松模様は Mitsuba の `checkerboard` texture（`bitmap`ではなく
  procedural textureを使い、外部アセット不要にする）を diffuse BSDFの
  `reflectance` に割り当てて作る。
- backdrop plane: 物体中心から見て backlight と同じ側、あるいは
  backlightをそのまま checkerboard 付き diffuse plane に置き換える形で
  配置する（emitterを失わないよう、backdrop本体とは別に既存の白色
  backlight rectangleは維持し、その手前か奥にbackdropを1枚追加する）。
- floor plane: シーン半径から求めたZ方向下端よりやや下に、水平な
  checkerboard diffuse plane を配置する。
- key light: 既存 backlight に加えて、カメラとは異なる斜め方向から
  当てる小さな area light をもう1個追加する。

### Step 3 — 解像度・sppの引き上げとレンダー

- `render_mitsuba()` は使わず、デモスクリプト内で直接
  `mi.load_dict(scene_dict)` → `mi.render(...)` → `mi.util.write_bitmap(...)`
  を呼ぶ（`render_mitsuba()` はcanonicalな1枚出力契約に固定されており、
  stage拡張後のscene_dictを渡す口が無いため）。
- CLIの `--width`/`--height`/`--spp` でデモ用設定を上書きできるようにし、
  既定値は `nested_material_cube` 相当の被写体で数秒〜十数秒程度に
  収まる値とする。
- 出力PNGに加え、pixel統計（min/max/mean/std）をログ出力し、
  既存Blenderデモ群の `PIXELSTATS` と横並びで比較できるようにする。

### Step 4 — 検証

- `nested_material_cube` に対して実行し、画像を目視で確認する。
  - 市松模様が透明外殻越しに歪んで見えること（屈折の判断材料になる）。
  - 中心の不透明コアが背景パターンを遮って輪郭が判別できること。
  - [[demo_improve1]] で得たBlender版
    （`.local/local_demo/nested_material_cube_swap_interior.png`）と
    並べて、同程度以上に「読める」ことを比較する。
- `marble-like` formation（既存 `marble_mitsuba` 実行例、複数interior
  境界を持つ複雑な入力の代理）に対しても実行し、複雑な境界群があっても
  シーンがエラーなくロード・レンダーされ、パターン歪みから内部構造の
  存在が読み取れることを確認する。
- 静的検査: `ruff check examples/pipeline_run/demo/mitsuba_stage_demo.py`
  と `py_compile` を通す。

### Step 5 — 文書化

- `README_QUICK.md` の Mitsuba 関連節（またはHandy Tool節）に、
  `mitsuba_stage_demo.py` の実行例と、`prepare_mitsuba_scene()` の
  canonical出力とは別物の qualitative demo である旨を追記する。
- 本計画の非ゴール（fixture未整備、写実背景は狙わない、canonical
  exporterは不変）を明記する。

## 実施順序

Step 1 → Step 2 → Step 3 で最小限の「読めるMitsuba静止画」を成立させる。
Step 4 で `nested_material_cube` と `marble-like` の両方で検証し、
Step 5 で使用方法を追記して閉じる。

## 完了条件

- 新規 `mitsuba_stage_demo.py` が canonical exporter
  （`prepare_mitsuba_scene` / `render_mitsuba` / `MitsubaExportConfig`）を
  変更せずに追加されている。
- `nested_material_cube` の `optical.zarr` から、市松模様の背景・床・
  斜め方向からのライトを持つPNGを、Docker不要でホスト上の1コマンドで
  生成できる。
- 生成画像を目視した際、背景パターンの歪み・遮蔽から屈折・不透明コアの
  存在と概形が、現在の白背景版より明確に読み取れる。
- `marble-like` のような複数interior境界を持つ複雑な入力でもエラーなく
  同じスクリプトが動く。
- canonical mitsuba exporter・medium・境界メッシュのBSDF/幾何は無変更。

## リスクと打ち切り条件

- **checkerboard textureの歪みが小さすぎて判断材料にならない場合**:
  背景平面の位置・サイズ・パターンの格子サイズ（`--checker-scale`）の
  調整のみで対応する。medium係数やBSDFの物理値は変更しない。
- **既存のbacklight（白色emitter）とbackdrop diffuse planeが干渉し
  不自然な露出になる場合**: backlightのradianceかbackdropの反射率を
  デモ用パラメータとして調整する。両者を同一平面に統合することはしない
  （emitterとtextured diffuse surfaceは別オブジェクトのまま保つ）。
- **`marble-like`のような多境界入力でロードや計算コストが著しく増える
  場合**: このデモは低速な高解像度プリセットを既定にしない。デフォルト
  はDocker無しで数秒〜十数秒に収まる設定とし、重い設定はオプション
  引数側に寄せる。
- **本物のガウシアン分布インクルージョンでの検証が別途必要になった場合**:
  本計画は非ゴールとして扱った通り着手しない。専用fixture生成は
  別functionとして計画する。
