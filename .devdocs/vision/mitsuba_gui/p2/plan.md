# mitsuba_gui Phase 2 実装計画 — viser ビューア MVP

親ロードマップ: `.devdocs/vision/mitsuba_gui/roadmap.md`（Phase 2）。
前提: Phase 1（`.devdocs/vision/mitsuba_gui/p1/report1-5.md`）完了済み。

## 前提調査（確認済み事実）

- Phase 1 により、stage は `StageConfig`（JSON round-trip 可能、既定=旧
  ハードコード値、`camera`/`backlight` は `None`=canonical passthrough）と
  `apply_stage(mi, scene_dict_copy, geometry, config)` に分離済み。
  ビューアはこの契約の上にそのまま乗れる。
- `prepare_mitsuba_scene(volume, output_dir, config)` は呼び出しごとに
  exterior/interior PLY・`capabilities.json`・`scene-summary.json` を
  `output_dir` に書き出す副作用を持つ（境界メッシュ抽出を含み、入力に
  よっては数秒かかる）。一方、得られた `prepared.scene_dict` の shallow copy
  に `apply_stage()` を適用して `mi.load_dict()` → `mi.render()` する部分は
  Phase 1 検証時の実測で `nested_material_cube` 512²/spp128 が数秒、
  `marble-like` が約2.5秒。低解像度・低sppのプレビューならさらに軽い。
- レンダー解像度・spp は canonical sensor dict 内の film/sampler に埋まって
  いるが、`mi.render(scene, spp=N)` で spp は上書きできる。**解像度は
  できない**ため、プレビュー解像度と確定解像度で別の sensor（= 別の
  `MitsubaExportConfig` で prepare した別の scene_dict）が必要になる。
- `MitsubaExportConfig` は `seed=20260628` 固定・`variant="llvm_ad_rgb"`。
  同一マシン・同一設定なら決定的な出力が得られる（Phase 1 の全画素一致
  検証で実証済み）。ビューアの確定レンダーと headless
  `mitsuba_stage_demo.py` が同じ width/height/spp/seed を使えば、
  「GUIで保存したプリセット → headless 再現」がピクセル同一で検証できる。
- vdbmat の optional 依存は `[dependency-groups]` 管理
  （`mitsuba = ["mitsuba>=3.6"]`）。uv の dependency-groups は
  `{include-group = "..."}` による包含をサポートしており、
  `mitsuba-viewer` group は `mitsuba` group を包含して `viser` を足せる。
- viser は pip インストール可能な Python サーバ＋ブラウザ GUI ライブラリで、
  スライダー・カラーピッカー（`add_gui_rgb`）・ドロップダウン・チェック
  ボックス・ボタン・フォルダ状パネル・画像表示の API を持つ。SSH 越しでも
  ポートフォワードでブラウザから使える。

## 規模判定

親ロードマップの Phase 2 のみを扱う単一 function 相当。新規ファイルは
ビューアスクリプト1本＋pyproject の dependency group 追加。
性能最適化（`mi.traverse()` 差分更新・漸進レンダー）は Phase 3 であり
本計画に含めない。

## ゴール

1. dependency group `mitsuba-viewer` を追加し、
   `uv run --group mitsuba-viewer python examples/pipeline_run/demo/
   mitsuba_stage_viewer.py -- OPTICAL_ZARR` でブラウザ GUI が起動する。
2. GUI 上のスライダー・カラーピッカー等で `StageConfig` の全フィールドを
   編集でき、変更が debounce 付きでプレビューレンダーに反映される
   （目標: 操作から数秒以内。MVP は全再構築でよい）。
3. 「Save preset」で `*.stage.json` を書き出し、「Render final」で
   確定設定の PNG を出力できる。保存したプリセットを headless の
   `mitsuba_stage_demo.py --stage-config` に渡すと、ビューアの確定
   レンダーと**ピクセル同一**の絵が再現される。

## アーキテクチャ（MVP）

```
起動時（1回だけ）:
  read_volume(zarr)
  prepare_mitsuba_scene(volume, work_dir/preview, preview用config)  → base_preview
  prepare_mitsuba_scene(volume, work_dir/final,   確定用config)     → base_final
    ※ PLY等の副作用ファイルは --work-dir 配下に隔離

パラメータ変更のたび（render workerスレッド、latest-wins）:
  scene_dict = dict(base_preview.scene_dict)   # shallow copy
  apply_stage(mi, scene_dict, geometry, 現在のStageConfig)
  mi.load_dict(scene_dict) → mi.render(seed固定, プレビューspp) → GUIへ画像
```

- **prepare は起動時2回だけ**: 重い境界メッシュ抽出・PLY 書き出しを
  パラメータ変更ループから排除する。変更ごとのコストは
  copy → `apply_stage` → `load_dict` → `render` のみ（MVP の「全再構築」は
  scene_dict の再組み立てを指し、prepare の再実行は含めない）。
  `apply_stage` は canonical の nested dict を変異させない（Phase 1 で
  backlight 差し替えをコピーで実装済み）ため、fresh copy への反復適用は安全。
- **解像度の扱い**: プレビューは preview 用 config（256²程度）の sensor を
  持つ `base_preview` を、確定レンダーは `StageConfig.render` の
  width/height/spp を反映した `base_final` を使う。ただし GUI で
  `render.width/height` を変更した場合、`base_final` だけは再 prepare が
  必要（camera override が有効なら sensor は `apply_stage` が差し替えるので
  再 prepare 不要という最適化は**しない** — passthrough 時と経路が分かれて
  バグの温床になるため、確定解像度の変更=再 prepare と一律に扱う）。
  spp は `mi.render(spp=...)` で上書きできるため再 prepare 不要。
- **プレビューと camera passthrough の両立**: `camera=None` のとき
  プレビューは `base_preview` の canonical sensor（preview 解像度）を
  そのまま使う。確定レンダーと headless 再現は `base_final` /
  `mitsuba_stage_demo.py` がともに `StageConfig.render` の解像度で
  canonical sensor を作るため一致する。
- **スレッド方針**: レンダーは単一 worker スレッドに直列化する
  （Mitsuba の同一 variant での並行レンダーは避ける）。GUI コールバックは
  「最新の StageConfig を置いて worker を起こす」だけにし、worker は
  常に最新値だけをレンダーする（途中の中間値は捨てる = latest-wins）。
  debounce（既定 0.3〜0.5 秒程度）で連続ドラッグ中の起動を抑える。

## 非ゴール

- `mi.traverse()` 差分更新・漸進レンダー（Phase 3）。
- 複数入力のタブ切替・Blender 版との横並び比較・プリセットギャラリー
  （Phase 4 候補）。
- canonical exporter 配下・`src/` のコード変更、medium・境界メッシュの
  BSDF/幾何の変更（従来どおり）。`mitsuba_stage.py` / `mitsuba_stage_demo.py`
  への変更も原則しない（ビューアから使って不足が判明した場合のみ、
  headless 側の挙動を変えない追加に限って許す）。
- 認証・複数ユーザー・リモート公開。ローカル開発者1人用。
- viser の 3D シーン表示機能（メッシュをブラウザに送る等）は使わない。
  表示するのは Mitsuba のレンダー画像1枚と GUI パネルのみ。

## GUI ⇔ StageConfig 対応

| StageConfig | ウィジェット |
|---|---|
| `render.width/height/spp` | 整数入力（確定レンダー用。プレビューには影響しない旨をラベルに明記） |
| `backdrop.enabled` / `floor.enabled` / `key_light.enabled` | チェックボックス |
| `backdrop.pattern` / `floor.pattern` | ドロップダウン（checker / solid） |
| `*.distance_factor` / `*.scale_factor` / `floor.drop_factor` | スライダー（範囲は既定値の 0.1〜4 倍程度、docstring に根拠を書く） |
| `*.checker_scale` | 整数スライダー（1〜32） |
| `*.color0/color1` / `key_light.radiance` / `backlight.radiance` | RGB ピッカー（radiance は 0〜1 の色 × 強度スライダーに分解し、保存時に積へ合成する。HDR 値を直接ピッカーに入れないため） |
| `key_light.direction` | 方位角・仰角の2スライダー（保存時に単位ベクトルへ変換） |
| `camera`（null 切替） | 「Override camera」チェックボックス + azimuth/elevation/distance_factor/fov スライダー（off なら `None` を保存 = canonical passthrough） |
| `backlight`（null 切替） | 「Override backlight」チェックボックス + 上記 radiance ピッカー |

- direction / radiance の GUI 分解表現は**GUI 内部だけ**の都合とし、
  保存される JSON は Phase 1 のスキーマそのまま（スキーマ変更なし）。
  読み込んだプリセットの direction / radiance は逆変換して GUI に反映する
  （非可逆な丸めが出る場合は保存値を優先し、GUI 表示だけ近似する）。

## 実装ステップ

### Step 1 — dependency group と起動骨格

- `vdbmat/pyproject.toml` の `[dependency-groups]` に
  `mitsuba-viewer = [{include-group = "mitsuba"}, "viser>=0.2"]` を追加し、
  `uv lock` を更新する（本体 `dependencies` は不変）。
- `examples/pipeline_run/demo/mitsuba_stage_viewer.py` を新設。
  CLI: `OPTICAL_ZARR [--stage-config PATH] [--port 8080]
  [--work-dir PATH] [--preview-size 256] [--preview-spp 16]`。
  `--work-dir` 既定はリポジトリ外の tempfile ディレクトリ
  （`.local/` を既定にすると CWD 依存になるため。明示指定で `.local/` 配下を
  使う運用は README で案内する）。
- 起動時に zarr 読み込み → preview/final の2回 prepare → viser サーバ起動
  → 初回プレビューを表示、まで通す（GUI パネルはまだ最小限でよい）。

### Step 2 — GUI パネルと StageConfig 双方向バインディング

- 上表のとおり StageConfig の全フィールドをフォルダ状パネル
  （Render / Backdrop / Floor / Key light / Camera / Backlight）で生やす。
- `--stage-config` 指定時はそのプリセット値で GUI を初期化する。
- どのウィジェット変更も「現在値から StageConfig を組み立て直して
  worker に渡す」一本の経路に集約する（ウィジェット→フィールドの
  個別更新コードを散らさない）。組み立ては Phase 1 の dataclass
  バリデーションを通るため、GUI がスキーマ外の値を作れないことが
  構造的に保証される。

### Step 3 — レンダー worker と画像更新

- 単一 worker スレッド＋latest-wins＋debounce（前掲アーキテクチャ）。
- プレビュー画像は viser の画像表示（GUI 画像または背景画像）で差し替える。
- レンダー中インジケータ（「rendering…」表示）と、直近プレビューの
  PIXELSTATS・所要秒数をパネルに表示する（体感速度の判断材料）。
- 例外（不正な組み合わせで Mitsuba がロードに失敗する等）は GUI に
  メッセージ表示し、サーバは落とさない。

### Step 4 — Save preset / Render final

- 「Save preset」: `stage_config_to_dict()` で現在の StageConfig を
  `--work-dir`（または `--preset-out` で明示したパス）へ
  `*.stage.json` として書き出し、保存先をパネルに表示する。
- 「Render final」: `StageConfig.render` の width/height/spp と
  canonical 既定 seed で `base_final` からレンダーし、PNG を書き出して
  PIXELSTATS をログ・パネル両方に出す。width/height が起動時から
  変わっていれば `base_final` を再 prepare してから行う。
- 確定レンダー中もプレビュー操作を受け付ける必要はない（worker は
  1本なので自然に直列化される。「queued」表示だけ出す）。

### Step 5 — 検証

- `nested_material_cube`: GUI 起動 → ライト・カメラ・背景を操作して
  プレビューが数秒以内に追随することを確認 → プリセット保存 →
  Render final → 同プリセットで headless
  `mitsuba_stage_demo.py --stage-config`（同じ width/height/spp）を実行し、
  `np.array_equal` で**全画素一致**を確認する。
- `--stage-config presets/stage-highkey.stage.json` で起動し、GUI 初期値が
  プリセットどおりであること（読み込み方向のバインディング）を確認する。
- `marble-like`: 起動・操作・保存・headless 再現の同じ往復がエラーなく
  成立することを確認する。プレビューが重い場合は `--preview-size` /
  `--preview-spp` を下げた運用値を README に記す。
- 静的検査: `ruff check` / `py_compile`。`git status` で差分が
  `examples/` と `pyproject.toml` / `uv.lock` に限られること、
  既定 group だけの `uv sync` 環境が従来どおり壊れていないこと
  （`uv run python -c "import vdbmat"` 程度）を確認する。
- 動作確認の入出力・保存プリセット・PNG は `.local/mitsuba_gui/p2/` に
  まとめ、git 管理しない。

### Step 6 — 文書化

- `README_QUICK.md` の Mitsuba stage 節に、ビューアの起動コマンド・
  「GUI で探索 → プリセット保存 → headless 再現」のワークフロー・
  qualitative demo である旨を追記する。
- ビューアのモジュール docstring に、アーキテクチャ（起動時2回 prepare、
  worker 直列化、GUI 分解表現は JSON スキーマ不変）を記す。

## 実施順序

Step 1 → 2 → 3 で「動くビューア」を成立させ、Step 4 で保存・確定レンダー、
Step 5 で往復検証、Step 6 で文書化して閉じる。1コミット単位は
[[mitsuba_improve1]] / Phase 1 と同様、全ステップまとめてでよい。

## 完了条件

- `uv run --group mitsuba-viewer` でビューアが起動し、StageConfig の
  全フィールドを GUI から編集でき、プレビューが数秒以内に追随する。
- GUI で保存したプリセット → headless `mitsuba_stage_demo.py` の再現が
  `nested_material_cube` / `marble-like` の両方で全画素一致する。
- `--stage-config` で与えたプリセットが GUI 初期値に反映される（双方向）。
- 保存される JSON は Phase 1 スキーマ（`format_version: 1.0.0`）のまま。
- canonical exporter・`src/`・`mitsuba_stage.py` / `mitsuba_stage_demo.py` の
  headless 挙動に差分がない。新規依存は `mitsuba-viewer` group に隔離され、
  既定 group の `uv sync` 環境は不変。

## リスクと打ち切り条件

- **viser の API がここでの想定と異なる場合**（ウィジェット種類・画像
  更新方法）: 同等機能の別ウィジェットで代替する。RGB ピッカーが HDR を
  扱えない前提は設計に織り込み済み（強度スライダー分解）。画像更新レートが
  不足する場合はプレビュー解像度を下げ、JPEG 品質を落とす。それでも
  実用にならない場合のみ、ロードマップのリスク欄に従い Phase 3 の
  漸進レンダーを前倒しする。
- **`load_dict` がプレビューでも遅い入力（marble-like 等）**: MVP は
  準ライブ（debounce を 1〜2 秒へ延長）を許容する。`load_dict` 回避は
  Phase 3 の `mi.traverse()` の主目的であり、本フェーズでは追わない。
- **GUI 分解表現（強度×色、方位角/仰角）の往復で数値が微妙に変わり、
  「読み込んだプリセットを無変更で保存したら差分が出る」場合**:
  無変更保存の同一性を完了条件にはしない。ただし直感に反するため、
  変更があったフィールドだけ GUI 値から取り、未操作フィールドは
  読み込み値をそのまま保持する実装を優先的に試みる。
- **viser のバージョン固定が困難（頻繁な breaking change）な場合**:
  `mitsuba-viewer` group で上限付き固定（`viser>=X,<Y`）にする。
  demo-track ツールなので、将来壊れたら group の pin 更新で追随する。
- **プレビューと確定でノイズ以外の見た目差が出る場合**（spp 以外の要因、
  例: 解像度依存のエイリアシング）: プレビューは構図・露出の判断用と
  割り切り、最終判断は Render final で行う旨を GUI とドキュメントに明記
  する。ピクセル同一の完了条件は「確定レンダー vs headless」にのみ課す。
