# mitsuba_gui ロードマップ — Mitsuba確認用シーンのGUI調整ツール

## 背景と動機

[[mitsuba_improve1]] で `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`
を追加し、checkerboard backdrop/floor と key light によって Mitsuba レンダーの
可読性は大きく改善した。しかし stage のパラメータ（ライトの明るさ・色、カメラの
方位角/仰角/距離/FOV、背景の柄・色ペア・格子スケール）はスクリプト内の固定値
であり、被写体ごとに「人間の目でモデルが適切に生成/描画されているか」を判断
しやすい構図・露出へ追い込むには、値を書き換えて数秒待つレンダーを何度も回す
しかない。これをGUIスライダー等でライブ調整できるようにする。

## 前提調査（確認済み事実）

- `mitsuba_stage_demo.py`（233行）は `_scene_bounds()` / `_checkerboard_bsdf()` /
  `_add_stage()` / `main()` という構成で、stage パラメータ（backdrop距離
  `radius*2.2`、teal/orange・indigo/yellow の色ペア、key light radiance
  `[6.4, 5.6, 4.2]` 等）はすべて関数内のハードコード値。CLIから調整できるのは
  `--width/--height/--spp/--checker-scale` のみ。
- Mitsuba 3 はホスト上で `uv run --group mitsuba` により Docker 不要で動作し、
  512×512 / spp128 の stage レンダーが `nested_material_cube` で約5.8秒、
  `marble-like` で約2.5秒（[[mitsuba_improve1]] report）。プレビュー解像度・
  低sppなら1秒未満〜1秒台が見込める。
- Mitsuba 3 には `mi.traverse(scene)` があり、emitter の radiance、BSDF の
  reflectance、checkerboard texture の `to_uv`、sensor / shape の `to_world` を
  **シーン再構築なしに**更新して `mi.render(scene, params)` で再レンダーできる。
  zarr 読み込み・PLY 書き出し・gridvolume ロードという重い初期化を毎回払わずに
  済むため、インタラクティブ化の技術的な鍵はここにある。
- vdbmat は `[dependency-groups]`（`dev`, `mitsuba`）で optional 依存を管理して
  おり、GUI用依存も同じ流儀で `mitsuba-viewer` のような group として足せる。
- `render_mitsuba()` / `prepare_mitsuba_scene()` / `MitsubaExportConfig` は
  canonical pipeline boundary 配下であり変更しない、という [[mitsuba_improve1]]
  の境界線は本ロードマップでもそのまま維持する。GUIは demo/QA トラックの
  qualitative ツールである。

## 規模判定

単一の function plan には収まらない。理由:

1. 既存デモの stage 構築ロジックを設定オブジェクト＋純関数に切り出す
   リファクタ（それ単体で headless の価値がある）と、
2. GUIビューア本体（新規依存 group、新規ツールディレクトリ）、
3. `mi.traverse()` 差分更新・漸進レンダーによるインタラクティブ性能改善、

がそれぞれ独立に実装・検証・出荷できる別フェーズであり、各フェーズが
function 1本分の実装計画に相当する。よって `.devdocs/vision/mitsuba_gui/` に
ロードマップとして置き、各フェーズ着手時に `.devdocs/function/` へ個別の
plan.md を切り出す。

## 全体ゴール

GUI（ブラウザ）上でスライダー・カラーピッカーを操作すると Mitsuba の stage
レンダーがライブ更新され、納得した設定を **stage 設定 JSON（プリセット）**
として保存できる。保存したプリセットは headless の `mitsuba_stage_demo.py` に
渡して同じ絵を再現できる。GUI は「シーンを編集するツール」ではなく
「stage 設定を探索するツール」であり、一級の成果物はプリセット JSON である。

調整対象パラメータ（初期スコープ）:

- ライト: key light の radiance（強度・色温度）、backlight の radiance、
  key light の方位角/仰角
- カメラ: 方位角・仰角・距離（シーン半径倍率）・FOV
- 背景: backdrop / floor それぞれの柄種別（市松 / 単色 / 無効）、色ペア、
  格子スケール、配置距離
- レンダー: プレビュー解像度・spp、確定レンダーの解像度・spp

## 非ゴール（全フェーズ共通）

- canonical exporter（`prepare_mitsuba_scene` / `render_mitsuba` /
  `MitsubaExportConfig`）、medium 係数、exterior/interior mesh の BSDF・幾何は
  一切変更しない。stage 要素は従来どおり scene_dict への additive な追記のみ。
- 新規 git submodule は作らない。ツールは vdbmat 内の demo/QA トラック
  （`examples/pipeline_run/demo/` 配下）に置き、依存は optional な
  dependency group に隔離する。renderer 依存を core package に足さない、
  という既存方針（`.local/local_env_memo.md`）を踏襲する。
- ボクセル・光学係数そのものの編集機能は持たない（入力 `optical.zarr` は
  読み取り専用）。
- 複数ユーザー同時利用、リモート公開、認証などのサーバ機能は持たない。
  ローカル開発者1人が使う確認ツールである。
- Blender/Cycles 側の同等 GUI は本ロードマップの範囲外（必要なら別 vision）。
- 写実的な背景アセットは作らない。プロシージャルな平面ジオメトリと
  テクスチャのみ。

## 技術スタック（決定事項）

- **GUI: viser**。Python サーバ＋ブラウザ GUI で、スライダー・カラーピッカー・
  フォルダ状パネル・画像表示の API が揃い、pip のみで導入できて Docker 不要
  （Mitsuba がホストで動く現状と一致）。フロントエンドコードを書かず、全ロジック
  を Python 側に置けるため、下記 StageConfig 中心の設計とそのまま一致する。
  Gradio（連続スライダー更新が苦手）、PySide6/Dear PyGui（デスクトップ配布が
  重くリモート開発と相性が悪い）、自作 FastAPI+React（保守コストに見合う要件が
  ない）は不採用。
- **設定契約: `StageConfig`**（dataclass、JSON round-trip 可能）。
  GUI・headless CLI・将来のレグレッションが共有する唯一の契約。
- **高速化: `mi.traverse()` による差分更新＋漸進レンダー**（Phase 3）。
  柄種別の切替などグラフ構造が変わる操作のみ scene_dict 再構築へ
  フォールバックする。

## フェーズ構成

### Phase 1 — StageConfig 抽出とプリセット契約（headless のみで完結）

`mitsuba_stage_demo.py` の stage 構築を、設定オブジェクトと純関数に切り出す。
GUI なしでも「プリセット JSON を書けば同じ絵が再現できる」状態を先に成立させ、
以降のフェーズの土台と検証手段を確保する。

- `examples/pipeline_run/demo/mitsuba_stage/` パッケージ（または単一モジュール）
  を新設し、`StageConfig`（ライト・カメラ・背景・レンダー設定、全フィールドに
  現行ハードコード値と同一のデフォルト）と
  `build_stage_scene(volume, config) -> scene_dict` 純関数を置く。
  `_scene_bounds()` / `_checkerboard_bsdf()` / `_add_stage()` の実体を移す。
- `StageConfig` の JSON serialize / deserialize（`xxx.stage.json`）と
  バリデーション（未知キー・範囲外値は明示的に拒否）を実装する。
- `mitsuba_stage_demo.py` に `--stage-config PATH` を追加。既存 CLI 引数
  （`--checker-scale` 等）は StageConfig の該当フィールドへの上書きとして残し、
  **引数なしの既定出力が現行とピクセル同一**（PIXELSTATS 一致）であることを
  検証する。
- サンプルプリセット（既定値そのもの＋バリエーション1つ）を
  `examples/` 配下に git 管理で置く。動作確認の入出力は従来どおり `.local/`。

完了条件: 既定動作の PIXELSTATS が現行と一致し、プリセット JSON 経由で
ライト・カメラ・背景を変えた絵が headless で再現できる。

### Phase 2 — viser ビューア MVP（素朴な全再構築で成立させる）

最小の GUI を成立させる。性能最適化はしない（全パラメータ変更で
scene_dict 再構築＋再レンダーでよい）。

- dependency group `mitsuba-viewer`（`mitsuba` group の内容＋ `viser`）を追加。
- `examples/pipeline_run/demo/mitsuba_stage_viewer.py` を新設。
  CLI: `OPTICAL_ZARR [--stage-config PATH] [--port N]`。
  起動すると zarr を読み、viser サーバを立て、ブラウザに
  レンダー画像＋パラメータパネル（StageConfig のフィールドに対応する
  スライダー / カラーピッカー / セレクタ）を表示する。
- パラメータ変更は debounce（操作が落ち着いてから1回）でプレビュー設定
  （低解像度・低spp、目安 256²/spp16 以下）の再レンダーを非同期実行し、
  画像を差し替える。レンダー中の操作は最後の値だけが反映されればよい。
- 「Save preset」で `xxx.stage.json` を書き出し、「Render final」で
  確定設定（高解像度・高spp）の PNG を出力する。どちらも出力先は
  CLI 引数で受け、既定は `.local/` 側を促す。
- PIXELSTATS を確定レンダー時にログ出力し、既存デモ群と横並びで比較できる
  ようにする。
- 検証: `nested_material_cube` と `marble-like` の両方で、GUI 起動 →
  ライト・カメラ・背景を操作 → プリセット保存 → headless
  `mitsuba_stage_demo.py 
 --stage-config` で同じ絵が再現される、を確認する。

完了条件: ブラウザ上の操作で数秒以内にプレビューが追随し、保存した
プリセットが headless で同一 PIXELSTATS を再現する。

### Phase 3 — `mi.traverse()` 差分更新と漸進レンダー

MVP の応答性を「スライダーに追随する」水準へ引き上げる。

- ビューア内部を「scene は一度だけ `mi.load_dict()` し、以降は
  `params = mi.traverse(scene)` で radiance / reflectance / `to_uv` /
  `to_world` を書き換えて再レンダー」する構造に変更する。
  StageConfig の各フィールドを traverse 可能なパラメータキーへ対応付ける
  マッピング層を設ける。
- グラフ構造が変わる操作（柄種別の切替、backdrop/floor の有効・無効）のみ
  scene_dict 再構築にフォールバックする。再構築経路は Phase 1 の純関数
  1本に限定されているため二重実装にはならない。
- 漸進レンダー: ドラッグ中は粗いプレビュー（目安 192²/spp4）、操作停止後に
  高spp版を非同期で上書きする2段構成にする。
- 検証: 同一パラメータに対して traverse 更新経路と全再構築経路の
  レンダー結果（PIXELSTATS）が一致することを確認し、マッピング層の
  バグを検出できるようにする。

完了条件: ライト・カメラ・色系のスライダー操作でプレビューが概ね1秒以内に
追随し、traverse 経路と再構築経路の結果が一致する。

### Phase 4（オプション） — 運用改善

必要性が確認されてから着手する。候補のみ列挙し、本ロードマップでは
コミットしない。

- 複数入力（複数 `optical.zarr`）のタブ/セレクタ切替
- Blender 版デモ（`blender_template_swap.py` 等）の出力 PNG との
  横並び比較ビュー
- プリセットのギャラリー（`.local/` 内のプリセット一覧・読み込み）
- 確定レンダーのキュー実行（高spp を裏で回しつつ調整を続ける）

## 実施順序と function 切り出し

Phase 1 → 2 → 3 の順に、着手時にそれぞれ `.devdocs/function/mitsuba_gui_p1`
（等）として plan.md を切り出す。Phase 1 と 2 は連続して実施する価値が高い。
Phase 3 は Phase 2 の使用感を見てから規模を再見積もりする。Phase 4 は
必要が生じるまで着手しない。

## 全体の完了条件

- GUI で調整 → プリセット保存 → headless 再現、の往復が
  `nested_material_cube` / `marble-like` の両方で成立する。
- 引数なしの `mitsuba_stage_demo.py` の出力が本ロードマップ着手前と
  ピクセル同一のまま保たれている。
- canonical exporter・medium・境界メッシュに差分がない
  （`git status` / diff で確認）。
- 新規依存はすべて optional dependency group に隔離され、
  `uv sync`（既定 group）だけの環境が従来どおり動く。

## リスクと打ち切り条件

- **viser の画像更新レートが不足する場合**: プレビュー解像度をさらに下げる /
  JPEG 品質を落とすことで対応する。それでも不足なら Phase 3 の漸進レンダーを
  前倒しする。GUI フレームワークの乗り換えは、viser 固有の欠陥（保守停止・
  致命的バグ）が確認された場合のみ検討する。
- **`mi.traverse()` で更新できないパラメータが想定より多い場合**
  （例: sensor の `to_world` が variant によって更新不可）: 該当パラメータのみ
  全再構築フォールバックに回す。全パラメータがフォールバック行きになり
  traverse の利得が消える場合、Phase 3 は「漸進レンダーのみ」に縮小して閉じる。
- **StageConfig 抽出で既定出力のピクセル同一が保てない場合**: 差分の原因を
  特定するまで Phase 1 を完了としない。浮動小数点の evaluation 順序変更など
  正当な理由による微差のみ、PIXELSTATS の許容誤差を明記した上で受け入れる。
- **marble-like など重い入力でプレビューが数秒を超える場合**: プレビュー既定を
  さらに軽くする（解像度・spp・`max_depth` の demo 用引き下げ）。それでも
  重い場合、その入力での「ライブ」性は諦め、debounce 間隔を伸ばした
  準ライブ動作を許容する。
