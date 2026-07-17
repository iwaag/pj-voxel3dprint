# mitsubav_refactor 実装計画 — `mitsuba_stage_viewer.py` のファイル分割

親ロードマップ: `.devdocs/vision/mitsubagui_improve/roadmap.md`。Phase 1〜5 完了後、
機能追加ではなく可読性・保守性のための構造整理として着手する。新しいフェーズ／
ロードマップは必要とせず、単一 function の実装計画として進める。

## 前提調査（確認済み事実）

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py` は現在 2816 行。
  クラス境界は次のとおり（`grep -n "^class \|^def "` で確認）。

  | 範囲 | 内容 | 行数 |
  |---|---|---|
  | 1-135 | モジュール docstring・import | 135 |
  | 136-451 | CLI引数・startup解決（`_parse_args`, `_resolve_session_root/path`, `SessionDerivation`, `_require_disjoint_roots`, `ViewerStartup`, `_startup_preset_ref`, `_resolve_viewer_startup`） | ~315 |
  | 452-1279 | scene/session/render コア（`_load_mitsuba`, `_pixel_stats`, `_structure_key`, `_preview_stage_config`, `_final_render_key`, `_resolve_initial_optical_zarr`, `_slug_for`, `_session_work_dir`, `_StageTimer`, `InputLoadError`, `_discard_session_dir`, `_sweep_stale_session_dirs`, `_nested`, `TraversedPreviewScene`, `InputSession`, `StageCore`, `RenderWorker`） | ~830 |
  | 1280-1789 | GUIバインディング（radiance/direction の decompose/compose ヘルパー、`StageBinder`） | ~510 |
  | 1790-2816 | `ViewerApp`（GUI配線・タブ構築・トランザクション）と `main()` | ~1025 |

- `StageCore`（1846-1167）は docstring 自身が「Viser-free rendering core」と明記
  しており、GUI（`StageBinder`/`ViewerApp`/viser）への依存を一切持たない。
  `TraversedPreviewScene` と `InputSession` も同様に GUI 非依存。
  `RenderWorker` は `threading` を使うが viser には触れない。
  → この4者はそのまま独立ファイルへ機械的に切り出せる。
- `StageBinder`（1331-1789）は `server`（viser）と `StageConfig` のみに依存し、
  Input/Preset タブの中身は `input_tab`/`preset_tab` という **callable引数**
  として `ViewerApp` から注入される（1883-1889行目）。つまり `StageBinder` は
  `ViewerApp` の内部状態を直接参照しない。radiance/direction の
  decompose/compose ヘルパー（`_decompose_radiance` 等、1280-1330行目）は
  `StageBinder` の内部でのみ使われる（grep で確認済み、他クラスからの参照なし）。
  → `StageBinder` も機械的に切り出せる。
- `ViewerApp`（1790-2804、約1000行）は "God Object" で、プレビュー配線・
  セッション保存/読込・最終レンダー・Presetタブ・Inputタブ（カタログ、
  digest検証、load transaction）を1クラスに同居させている。特にInput/Preset
  タブ関連だけで約20メソッド・500行超あり、roadmap Phase 2/4/5 で機能が
  積み増された結果が肥大化の主因になっている。このクラスは `self.core`,
  `self.binder`, `self.worker`, `self.server`, `self.gui.*` ハンドルなど
  多数のインスタンス状態を横断参照するため、`StageCore`/`StageBinder` ほど
  機械的には切り出せない。
- **モンキーパッチ経由の重大な制約**: `vdbmat/tests/integration/
  test_mitsuba_stage_viewer.py` は次の2箇所で `mitsuba_stage_viewer` モジュール
  属性を直接差し替えている。

  ```python
  monkeypatch.setattr(mitsuba_stage_viewer, "prepare_mitsuba_scene", _boom)  # 826行目
  monkeypatch.setattr(mitsuba_stage_viewer, "TraversedPreviewScene", _boom)  # 855行目
  ```

  これらは `StageCore`/`TraversedPreviewScene` が **今は同じモジュール内で**
  `prepare_mitsuba_scene`/`TraversedPreviewScene` というグローバル名を直接
  呼んでいるために効いている。この2つを新ファイル（例:
  `mitsuba_stage_core.py`）へ移すと、呼び出し側のグローバル名解決先も
  そのファイルに変わるため、`mitsuba_stage_viewer` 側への `setattr` は
  実行時の呼び出しに一切影響しなくなり、パッチが無言で無効化される
  （テストは `_boom` を期待する箇所で本物のレンダリングを実行してしまう）。
  一方、他の2箇所のモンキーパッチ（`regenerate_optical` 855行目付近、
  `zarr_store_sha256` 1788行目付近）は、その呼び出し箇所が両方とも
  `ViewerApp`（今回移動しない側）に閉じているため影響を受けない。
  → 分割と同じコミットで、上記2箇所の `monkeypatch.setattr` の対象を
  `mitsuba_stage_core` に変更する必要がある。**これを見落とすと分割自体は
  import エラーなく成功するが、上記2テストが偽陽性でパスし続ける
  （本来検出すべき失敗を検出しなくなる）。**
- 他に `mitsuba_stage_viewer` から個別名を import しているのは
  `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`,
  `vdbmat/tests/integration/test_mitsuba_stage_viewer_regression.py`,
  `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`,
  `vdbmat/examples/pipeline_run/demo/mitsuba_session_compat.py`。
  import している名前（`InputSession`, `RenderWorker`, `StageBinder`,
  `StageCore`, `ViewerApp`, `InputLoadError`, `TraversedPreviewScene`,
  `_discard_session_dir`, `_final_render_key`, `_fit_preview_to_aspect`,
  `_parse_args`, `_preview_stage_config`, `_resolve_initial_optical_zarr`,
  `_resolve_session_path`, `_resolve_session_root`, `_session_work_dir`,
  `_slug_for`, `_StageTimer`, `_structure_key`, `_sweep_stale_session_dirs`,
  `_AS_IS_MAPPING` 等）は、分割後も `mitsuba_stage_viewer.py` が新ファイルから
  re-export すれば、これらの import 文自体は無修正で動く。

## 規模判定

新規ロードマップ・新規フェーズ不要。既存の単一ファイルを責務ごとに
最大3ファイルへ分割する構造整理であり、単一 function の実装計画として進める。

## ゴール

1. `mitsuba_stage_viewer.py` を、GUI非依存の「scene/session/renderコア」と
   「GUIフィールドバインディング」を別ファイルへ切り出すことで、
   2816行から1300行前後まで縮小する。
2. 既存の公開import経路（`from mitsuba_stage_viewer import X`）を壊さない。
   分割後も `mitsuba_stage_viewer.py` から必要な名前を re-export する。
3. 既存テスト（unit・integration）を無改修で通す。ただし前提調査で述べた
   2箇所のモンキーパッチ対象だけは、実際に効果を持つよう新モジュールへ
   向け直す（これは「テストを壊さない」ための必須修正であり、本計画の
   スコープに含む）。
4. `ViewerApp` 自体の分割（タブごとの controller 抽出）は、今回はやらない。
   影響範囲とリスクが大きく、Input/Preset タブの委譲設計を別途検討する
   価値があるため、次段の function として切り出す（非ゴール参照）。

## スコープ

### Step 1 — `mitsuba_stage_core.py` を新設し、GUI非依存のコアを移す

移動対象（現ファイル 452-1279行相当、`ViewerApp`/`StageBinder`から使われず
StageCore/TraversedPreviewScene/InputSession/RenderWorker 内部でのみ使われる
ものに限定）:

- `_load_mitsuba`, `_pixel_stats`, `_structure_key`, `_preview_stage_config`,
  `_final_render_key`, `_resolve_initial_optical_zarr`, `_slug_for`,
  `_session_work_dir`, `_StageTimer`, `InputLoadError`,
  `_discard_session_dir`, `_sweep_stale_session_dirs`, `_nested`
- `TraversedPreviewScene`, `InputSession`, `StageCore`, `RenderWorker`

必要な import（`mitsuba_stage` の `RGB`/`StageConfig`/`RenderSettings`/
`apply_stage`、`vdbmat.core.volumes.OpticalPropertyVolume`、
`vdbmat.exporters.mitsuba.MitsubaExportConfig`/`prepare_mitsuba_scene`、
`vdbmat.io.zarr.read_volume` など）は現在の `mitsuba_stage_viewer.py` の
import ブロックから該当分だけをこのファイルへ複製する。逆方向の import
（`mitsuba_stage_core.py` が `mitsuba_stage_viewer.py` を import すること）は
発生させない — 循環importを避けるため、依存は常に
`mitsuba_stage_viewer.py → mitsuba_stage_core.py` の一方向にする。

`mitsuba_stage_viewer.py` 側は、これらの名前を
`from mitsuba_stage_core import (...)` で re-export し、既存の
`from mitsuba_stage_viewer import StageCore` 等の import 文を無改修で
動かす。

### Step 2 — `mitsuba_stage_binder.py` を新設し、GUIフィールドバインディングを移す

移動対象（現ファイル 1280-1789行相当）:

- `_decompose_radiance`, `_compose_radiance`, `_decompose_direction`,
  `_compose_direction`, `_rgb_int`
- `StageBinder`

`StageBinder.__init__` の `input_tab`/`preset_tab` callable 引数の型
（`Callable[[object], None]` 相当）はそのまま維持し、`ViewerApp` 側の
`self._build_input_tab`/`self._build_preset_tab` を束縛する現行の呼び出し
（1883-1889行目）は変更しない。`mitsuba_stage_viewer.py` から
`from mitsuba_stage_binder import StageBinder` として re-export する。

`_fit_preview_to_aspect` は `ViewerApp._update_client_preview` からしか
呼ばれていないため移動しない（`mitsuba_stage_viewer.py` に残す）。

### Step 3 — モンキーパッチ対象とテストの追随

- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py` の
  `monkeypatch.setattr(mitsuba_stage_viewer, "prepare_mitsuba_scene", _boom)`
  と `monkeypatch.setattr(mitsuba_stage_viewer, "TraversedPreviewScene", _boom)`
  を、それぞれ `mitsuba_stage_core` を対象にするよう書き換える
  （`import mitsuba_stage_core` を追加した上で
  `monkeypatch.setattr(mitsuba_stage_core, "prepare_mitsuba_scene", _boom)` 等）。
- 他の import 文（`from mitsuba_stage_viewer import InputSession, StageCore,
  TraversedPreviewScene, ...` 等、複数ファイルに分散）は re-export のおかげで
  無改修のまま通ることを確認する。無改修で通らないものが見つかった場合のみ、
  import元をピンポイントで新モジュールに直す。

### Step 4 — ドキュメント更新

- `mitsuba_stage_viewer.py` 冒頭の docstring（Architecture節、
  `.devdocs/vision/mitsuba_gui/p3/plan.md` 参照）に、コアとGUIバインディングが
  別ファイルへ分離されたことを一文で追記する。
- 本ファイル完了後、`README_QUICK.md` にファイル一覧の記載があれば
  実体と齟齬がないか確認する（記載があれば更新、なければ何もしない）。

## 非ゴール

- `ViewerApp` 自体のタブ単位分割（Input/Preset タブの controller クラス化）。
  `self.core`/`self.binder`/`self.worker`/`self.server`/GUIハンドルを跨いだ
  委譲設計が必要で、今回の機械的分割より設計判断とリスクが大きいため別 function
  とする。
- `StageConfig`/`RenderSettings` 等のスキーマ変更。
- Input/Preset/Mappingタブの挙動・API・GUIレイアウトの変更。
- `mitsuba_viewer_session.py` / `mitsuba_stage_inputs.py` /
  `mitsuba_stage_mappings.py` / `mitsuba_stage_presets.py` /
  `mitsuba_stage_regen.py` など既に分離済みの周辺ファイルの再構成。
- 新しい抽象化層やプラグイン機構の導入。分割は既存クラス境界に沿って行い、
  新しい設計パターンは持ち込まない。

## 検証方針

- `mitsuba_stage_core.py`/`mitsuba_stage_binder.py` は import 専用の
  機械的移動なので、まず両ファイルが単独で import エラーなく読み込めることを
  確認する（`python -c "import mitsuba_stage_core, mitsuba_stage_binder"`
  相当、`sys.path` に demo ディレクトリを通した状態で）。
- 既存のunit test（`vdbmat/tests/test_mitsuba_stage_viewer_worker.py`）と
  integration test（`vdbmat/tests/integration/test_mitsuba_stage_viewer.py`,
  `test_mitsuba_stage_viewer_regression.py`）を分割前後で実行し、
  分割前と分割後でPASS/FAILが完全一致することを確認する
  （Mitsuba依存テストは `pytest.importorskip("mitsuba")` によりMitsuba無し
  環境ではskipされる点に注意——CIまたはローカルのMitsuba導入環境で実行する）。
- 前提調査で特定した2箇所のモンキーパッチについては、書き換え後に
  意図どおり動作していることを明示的に確認する。具体的には、該当テストの
  アサーションを一時的に反転させる（あるいは対象を意図的に
  `mitsuba_stage_viewer` のまま残す）ことで、パッチが効いていない場合に
  そのテストが正しく失敗することを一度確認してから、正しい対象に戻す。
- `main()` から実際にviewerを起動する手動確認は必須としない
  （Mitsuba/viserを要するGUI起動確認であり、対象は import 経路の整理に
  限られるため）。ただし可能であれば起動して1回のプレビュー生成が
  分割前と同じ `PIXELSTATS` を返すことを確認する。

## 完了条件

- `mitsuba_stage_viewer.py` が 1300〜1400行程度まで縮小し、
  `mitsuba_stage_core.py`（scene/session/render コア）と
  `mitsuba_stage_binder.py`（GUIフィールドバインディング）が新設される。
- 分割前後で `vdbmat/tests/test_mitsuba_stage_viewer_worker.py` および
  `vdbmat/tests/integration/test_mitsuba_stage_viewer*.py` のPASS/FAILが
  完全に一致する。
- `prepare_mitsuba_scene`/`TraversedPreviewScene` のモンキーパッチが
  新モジュールに対して行われ、意図どおり失敗系テストを検出できることを
  確認済み。
- `mitsuba_stage_demo.py`/`mitsuba_session_compat.py` など他ファイルからの
  既存import文が無改修で動く（re-exportにより）。
- `mitsuba_stage_viewer.py` の循環importが発生していない
  （`mitsuba_stage_core.py`/`mitsuba_stage_binder.py` はどちらも
  `mitsuba_stage_viewer.py` を import しない）。
