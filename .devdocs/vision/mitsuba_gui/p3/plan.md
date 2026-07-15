# mitsuba_gui Phase 3 実装計画 — traverse 差分更新と漸進レンダー

親ロードマップ: `.devdocs/vision/mitsuba_gui/roadmap.md`（Phase 3）。  
前提: Phase 1 / 2（`p1/report1-5.md`, `p2/report1-6.md`）完了済み。

## 前提調査（確認済み事実）

- Phase 2 の `mitsuba_stage_viewer.py` は、起動時に preview / final の
  `prepare_mitsuba_scene()` を行い、変更ごとに `scene_dict` の shallow copy →
  `apply_stage()` → `mi.load_dict()` → `mi.render()` を単一 worker で実行する。
  preview は latest-wins + 0.35 秒 debounce、final は同じ worker の job queue
  で直列化されている。
- Phase 2 の実測 preview は `nested_material_cube` で約 0.2 秒、
  `marble-like` で約 0.1 秒（256²/spp16）。すでにロードマップの「概ね1秒以内」
  を満たすため、本フェーズの価値は待ち時間の大幅短縮より、連続操作中の追随、
  `mi.load_dict()` の反復削減、更新契約をテスト可能にすることにある。
- `StageConfig` の `camera=None` / `backlight=None` は canonical scene の
  passthrough を意味する。GUI は override checkbox で null / 非 null を切り替え、
  key-light の方向・radiance は GUI 内だけで方位角/仰角、色×強度に分解する。
  保存 JSON の契約は Phase 1 のまま変更しない。
- ローカルの Mitsuba (`llvm_ad_rgb`) と `marble-like` で実際に
  `mi.traverse(scene)` を調べ、少なくとも次のキーを確認した。
  - `stage_key_light.emitter.radiance.value`,
    `stage_key_light.to_world`
  - `backlight.emitter.radiance.value`, `backlight.to_world`
  - `stage_backdrop|stage_floor.bsdf.reflectance.color0|color1.value`,
    `...reflectance.to_uv`, 各 shape の `to_world`
  - `sensor.to_world`, `sensor.x_fov`
- checker → solid では traverse キー集合が変わり、enabled の切替では shape 自体が
  増減する。この2種はパラメータ更新では表現できないため scene 再構築が必要。
  一方、色・radiance・transform・FOV は同じグラフ構造内で更新できる。
- film 解像度は scene に属する。Phase 2 と同じく preview scene と final scene は
  分ける必要があり、「scene を一度だけ load」は preview の同一構造が続く区間に
  対する要件とする。spp は `mi.render(..., spp=N)` で段階ごとに上書きできる。
- canonical exporter (`src/vdbmat/exporters/mitsuba.py`) と `StageConfig` / JSON、
  stage の幾何生成 (`mitsuba_stage.py`) は本フェーズでも変更不要。差分更新は
  viewer 内部だけの最適化である。

## 規模判定

親ロードマップの Phase 3 のみを扱う単一 function 相当。主な変更は
`mitsuba_stage_viewer.py` のレンダーコア・worker と、その demo-track 向けテスト。
依存追加、設定スキーマ変更、canonical pipeline 変更は行わない。

## ゴール

1. 同一グラフ構造の preview scene を保持し、StageConfig の連続値変更を
   `mi.traverse()` のパラメータ更新だけで反映する。
2. checker / solid、enabled / disabled 等の構造変更だけを、Phase 1 の
   `apply_stage()` を使った scene 再構築へフォールバックする。
3. 操作中は粗いレンダー、操作停止後は高品質 preview を表示する2段階レンダーを
   latest-wins で実現し、古い結果で新しい画像を上書きしない。
4. 同一 StageConfig について traverse 経路と fresh rebuild 経路の結果が一致する
   自動検証を用意し、マッピング漏れを検出可能にする。

## 設計

### 1. `TraversedPreviewScene` と明示的なマッピング層

`StageCore` から preview scene の寿命と更新処理を小さな内部クラス
（仮称 `TraversedPreviewScene`）へ分離する。

```
初回または構造変更時:
  dict(base_preview.scene_dict)
    -> apply_stage(mi, ..., preview用StageConfig)
    -> mi.load_dict()
    -> mi.traverse()
    -> scene / params / 適用済みconfig / structure key を保持

連続値変更時:
  StageConfig差分を分類
    -> 対応する params[key] だけ代入
    -> params.update()
    -> mi.render(保持scene, seed=固定, spp=段階別)
```

- Python 属性名から Mitsuba キーを暗黙生成せず、更新関数を明示的に定義する。
  対象は backdrop / floor の色・checker scale・transform、key light の
  radiance / transform、明示 backlight の radiance、明示 camera の transform / FOV。
- transform は `mitsuba_stage.py` と同じ `scene_bounds()`、座標系、積の順序で生成する。
  計算式の二重実装を避けるため、必要なら **scene_dict を生成する既存純関数を
  viewer から利用して対象値だけ読む**。canonical exporter 側へ helper を足さない。
- FOV は設定上の degree 値と traverse の `sensor.x_fov` が常に同義とは限らない
  （film aspect / FOV axis の影響）ため、固定値の直書きを避ける。更新用に生成した
  sensor dict を一時 load/traverse して値を得る、または実測で同値性を証明した変換を
  helper 化する。ここは Step 1 の probe で決定し、推測で式を置かない。
- `params.update()` 後に保持中 config を更新する。キー欠落・型不適合・Mitsuba の
  update 例外時は黙って古い scene を使わず、1回だけ rebuild へ退避して status/log
  に理由を出す。再構築後も失敗する場合は通常の render error とする。

### 2. 構造判定とフォールバック

`StageConfig` から次だけを抽出した immutable な `structure_key` を定義する。

```
(backdrop.enabled, backdrop.pattern,
 floor.enabled, floor.pattern,
 key_light.enabled,
 camera is not None,
 backlight is not None)
```

- `structure_key` が同じなら traverse 更新候補、異なれば必ず rebuild する。
- camera / backlight の null 切替は、現在の plugin 型が同じでも canonical
  passthrough と override の契約境界なので、初期実装では安全側に rebuild とする。
- render width / height は preview には影響させない（Phase 2 と同じく preview 用
  `RenderSettings` に差し替える）。spp も preview 品質設定を使うため traverse
  マッピング対象外。final 解像度変更時の `_ensure_final()` は現状を維持する。
- rebuild は必ず `dict(base_preview.scene_dict)` + `apply_stage()` の1経路に限定し、
  stage graph を viewer 内で再実装しない。rebuild 後は params と基準 config を
  再取得し、次の連続変更から traverse に戻る。

### 3. 漸進レンダーと世代管理

CLI は既存 `--preview-size`, `--preview-spp` を settled preview の設定として維持し、
`--interactive-spp`（既定4）と `--settle-delay`（既定0.35秒）を追加する。
解像度を段階ごとに変えると film 再構築が必要になるため、初期実装では両段階とも
同じ preview 解像度（既定256²）を使い、spp のみ 4 → 16 とする。192²を望む場合は
既存 `--preview-size 192` で選択できる。

- GUI update ごとに config と単調増加 generation を worker へ渡す。
- worker は最初に最新 config を `interactive-spp` で描画する。描画中に新しい
  generation が来た場合、その結果は GUI へ publish せず、直ちに最新値へ進む。
- 最後の update から `settle-delay` 経過後、同じ generation を
  `preview-spp` で再描画する。完了時にも generation を照合し、古ければ破棄する。
- coarse と settled は同じ scene / params を使う。scene update と render は既存どおり
  単一 worker 内だけで行い、Mitsuba を並行実行しない。
- GUI status に `interactive` / `settled`、更新経路 `traverse` / `rebuild`、所要時間を
  表示する。性能検証とフォールバック多発の発見に使い、永続成果物には含めない。
- final job は既存キューで直列化し、開始時に config snapshot を固定する。
  final 完了後は pending preview の最新 generation を処理する。preset 保存はレンダーを
  必要としないため GUI callback で同期保存してよい。

## 非ゴール

- canonical exporter、medium、exterior/interior mesh、StageConfig JSON schema の変更。
- final render の traverse 常駐化。final は頻度が低く、解像度変更もあるため Phase 2 の
  fresh scene 経路を正しさの基準として残す。
- レンダー途中の Mitsuba cancel。実行中の低spp render は完走させ、結果の世代判定で
  stale 表示を防ぐ。
- preview の解像度を段階間で切り替えること、adaptive sampling、画像の JPEG 化。
- GUI framework の変更、複数入力、プリセットギャラリー、Blender 対応。
- `src/` 配下への viewer 専用抽象化追加、新規依存 group / submodule の追加。

## 実装ステップ

### Step 1 — traverse 契約 probe と更新表の確定

- 既定、solid、disabled、camera/backlight override の各 scene を小解像度で load し、
  `mi.traverse()` のキーと値型を記録する開発用 probe を行う。
- 各連続フィールドについて「更新キー」「Mitsuba 値型」「値の生成方法」をコード上の
  明示表または updater 関数として確定する。checker `to_uv` と camera FOV は実際に
  変更後レンダーまで行い、単にキーが見えるだけでなく更新可能なことを確認する。
- probe 出力・画像は `.local/mitsuba_gui/p3/` のみに置き、git 管理しない。

### Step 2 — preview scene の常駐化とフォールバック

- `StageCore._render()` の preview と final の責務を分け、preview に
  `TraversedPreviewScene` を導入する。final の fresh `load_dict` 経路は保持する。
- `structure_key`、config 差分、updater、`params.update()`、rebuild を実装する。
- 実際に値が変わったフィールドだけ更新し、同一 config の settled render では
  params 更新を行わない。
- キー欠落時の診断と rebuild fallback を追加し、status 用に更新経路を返す。

### Step 3 — worker を2段階 latest-winsへ変更

- 現在の「0.35秒待って1回 render」を、即時 coarse + 静止後 settled に変更する。
- generation による publish guard、pending config の上書き、final job との直列化を
  condition/event ベースで実装する。固定 sleep の間も新規 update で速やかに起床できる
  ようにし、テストが時間依存で不安定にならない構造にする。
- `--interactive-spp`, `--settle-delay` の正値検証を追加し、
  `interactive-spp <= preview-spp` を要求する。既存 CLI は互換維持する。

### Step 4 — 自動検証

- Mitsuba を必要としない worker 単体テスト:
  - burst update で coarse は最新値へ収束し、settled は最後の1件だけ。
  - coarse 実行中に更新しても古い画像を publish しない。
  - final job と preview が並行実行されず、final 後に最新 preview が処理される。
  - render 例外後も worker が次要求を処理できる。
- 小解像度/spp の Mitsuba integration 検証:
  - radiance、各色、checker scale、各 transform、camera FOV を最低1回ずつ変更し、
    traverse 経路と fresh rebuild 経路を同一 seed で描画する。
  - HDR 配列の `np.array_equal` を第一判定とする。Mitsuba の update 経路固有の
    浮動小数差が確認された場合だけ、最大絶対差・平均差を記録して根拠ある厳しい
    tolerance を設定する。PIXELSTATS だけの一致で済ませない。
  - checker↔solid、各 enabled、camera/backlight null 切替が rebuild と判定され、
    rebuild 後の次の連続変更が traverse に戻ることを確認する。
  - 想定キーを意図的に欠落させ、診断付き fallback が動くことを確認する。
- `nested_material_cube` と `marble-like` で GUI 相当の連続操作 → settled → preset
  保存 → final → headless 再現を行い、Phase 2 の全画素一致を維持する。
- interactive / settled の所要時間と rebuild 回数を記録する。受入基準は色・ライト・
  カメラの連続操作で coarse 表示が概ね1秒以内。Phase 2 より速いことを必須にはせず、
  traverse が通常経路で `mi.load_dict()` を呼ばないことを計測/spy でも確認する。
- `ruff check`、`py_compile`、既存 Mitsuba tests を実行する。動作確認成果物はすべて
  `.local/mitsuba_gui/p3/` に置く。

### Step 5 — 文書化

- `README_QUICK.md` の viewer 例に coarse / settled の挙動、新 CLI、status の
  `traverse` / `rebuild` 表示を追記する。
- 実施報告に実測 latency、traverse/rebuild 一致結果、fallback したフィールドを残す。
  ローカルパスや環境情報を git 管理文書へ転記しない。

## 実施順序

Step 1 で Mitsuba の実契約を固定 → Step 2 で正しい差分更新と再構築退避を成立 →
Step 3 で世代付き漸進 worker を接続 → Step 4 で更新網羅・一致・競合を検証 →
Step 5 で利用方法と結果を文書化する。

## 完了条件

- 同一 `structure_key` 内のライト・カメラ・色・checker scale・配置変更が
  `params.update()` 経路を使い、変更ごとに `mi.load_dict()` しない。
- 構造変更だけが `apply_stage()` による rebuild へ落ち、以後 traverse に復帰する。
- coarse → settled が latest-wins で動き、古い世代の画像が新しい設定を上書きしない。
- traverse と rebuild の HDR 結果が同一（または根拠を明記した厳しい許容差内）。
- `nested_material_cube` / `marble-like` で preset → final → headless の全画素一致を維持。
- 連続値操作の coarse preview が概ね1秒以内。canonical exporter、`src/`、medium、
  geometry、StageConfig schema、既定 dependency group に差分がない。

## リスクと打ち切り条件

- **特定キーが traverse できない / update が描画へ反映されない**:
  そのフィールドだけ rebuild 分類へ移す。理由と対象を明示し、他の更新まで
  fallback させない。
- **camera update が variant や FOV 規約に依存する**: camera のみ rebuild とする。
  canonical exporter を変更してまで高速化しない。
- **差分更新と rebuild の画素が一致しない**: stale params、transform 型、
  `params.update()` 漏れを解消するまで当該 updater を採用しない。原因不明のまま
  緩い tolerance で閉じない。
- **coarse render 自体が1秒を超える入力**: `--preview-size 192` / より低い
  `--interactive-spp` を案内する。それでも超える場合は cancel 機構を追加せず、
  latest-wins の結果破棄と settled debounce による準ライブ動作を許容する。
- **Phase 2 実測に対して traverse の管理コストが利得を上回る**: 正しさと保守性を
  優先し、確実に更新できる radiance / 色 / transform のみに範囲を縮小する。
  全対象が rebuild となり利得が消える場合は、Phase 3 を世代管理付き漸進レンダー
  のみとして閉じ、実施報告に打ち切り理由を残す。
