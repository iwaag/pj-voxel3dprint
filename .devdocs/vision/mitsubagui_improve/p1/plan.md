# mitsubagui_improve Phase 1 実装計画 — Render契約と `max_depth`

親ロードマップ:
`.devdocs/vision/mitsubagui_improve/roadmap.md`（Phase 1）。

## この計画の位置づけ

本計画は Phase 1 の実装だけを対象とする。入力カタログ、`optical.zarr` の切替、
stage presetのGUI読込、viewer session、optical mapping選択は後続フェーズで扱う。

既存 `mitsuba_gui` のGUI、traverse更新、coarse/settled worker、固定ビューポート表示を
維持したまま、render transport設定として `max_depth` を次の全経路で一貫させる。

```text
stage JSON / CLI / GUI
          ↓
 RenderSettings.max_depth
          ↓
 preview scene / final scene / headless scene
```

各経路で独自の既定値や隠れた上書きを持たせず、未指定時は現在と同じ8とする。

## 前提調査（確認済み事実）

### StageConfig契約

- `examples/pipeline_run/demo/mitsuba_stage.py` の `RenderSettings` は現在
  `width=512`、`height=512`、`spp=128` の3フィールドだけを持つ。
- stage JSONは `format="vdbmat.stage-config"`、`format_version="1.0.0"`。
  parserはversionを完全一致で検証し、未知versionを拒否する。
- 各sectionは部分指定可能で、未指定fieldはdataclass既定値で補完される。
  一方、未知fieldは `_section_from_dict()` が拒否するため、現状の1.0.0文書へ
  `render.max_depth` を書くとエラーになる。
- serializerは全フィールドを明示して出力する。viewerのSave presetも同じ
  `stage_config_to_dict()` を使う。
- `StageConfig.with_cli_overrides()` はwidth/height/spp/checker scaleだけを扱う。

### Headless経路

- `mitsuba_stage_demo.py` はStageConfigを読み、width/height/sppを
  `MitsubaExportConfig` へ渡すが、`max_depth` は渡さない。このためexporter既定値8が
  常に使われる。
- `prepare_mitsuba_scene()` はscene dictへ
  `{"type": "volpath", "max_depth": config.max_depth}` を埋め込む。
- `scene-summary.json` は `MitsubaExportConfig.max_depth` を既に記録するため、
  StageConfigから正しく渡せばsummary側のschema変更は不要。

### Viewer経路

- `StageCore.__init__()` はpreview用 `MitsubaExportConfig` を一度prepareし、
  final用base sceneは `_ensure_final()` で解像度が変わった時だけprepareする。
- final sceneのcache keyは現在 `(width, height)` だけで、depthを区別しない。
- previewでは `_preview_render = RenderSettings(preview_size, preview_size,
  preview_spp)` を作り、`replace(config, render=self._preview_render)` でGUIのrender節を
  丸ごと置換する。RenderSettingsへ単純にfieldを追加すると、GUIで選んだdepthが
  previewでは既定値8へ戻る。
- `TraversedPreviewScene._stage_dict()` はbase scene dictを浅くcopyしてstageだけを
  適用する。integratorは変更しない。
- `_structure_key()` はstage graphの有効/無効、pattern、camera/backlight override
  だけを含み、render設定を含まない。
- GUI Renderタブはwidth/height/sppのみ。`StageBinder.current()` もその3値から
  RenderSettingsを再構築する。

### Mitsubaの更新能力

- ローカルの Mitsuba `llvm_ad_rgb` で `volpath(max_depth=8)` をloadし、
  `mi.traverse(scene)` のkeyを確認した。
- integratorまたはdepthに対応するtraverse keyは存在しなかった。確認されたkeyは
  sensor、film、light等で、`max_depth` は含まれない。
- よって `max_depth` 変更をcontinuous traverse更新として扱わない。明示的なscene
  rebuildが必要であり、`rebuild-fallback` ではなく予定された `rebuild` とする。

## 規模判定

単一フェーズの実装計画として扱える。主な変更は既存3ファイル
（stage契約、headless CLI、viewer）とテスト／preset／文書で、canonical volume、
boundary mesh、material mapping、exporterの既定値は変更しない。

ただし、field追加だけではpreviewで値が失われるため、render overrideとscene rebuild
境界を同時に修正する必要がある。GUI widgetだけを先行追加して完了とはしない。

## ゴール

1. `RenderSettings.max_depth` を正規の設定値とし、既定値を8にする。
2. GUI Renderタブから正の整数として変更できるようにする。
3. GUI preview、GUI final、headless renderの全てで同じ値を使用する。
4. stage presetへ保存し、新readerで旧1.0.0 presetも読み込めるようにする。
5. depth変更をpreviewの予定されたscene rebuildとして扱い、traverse fallbackに
   依存しない。
6. 実効depthをpreset、scene summary、GUI status／ログから確認できるようにする。

## 決定事項

### 設定field

`RenderSettings` を次の形へ拡張する。

```text
RenderSettings
├── width: int = 512
├── height: int = 512
├── spp: int = 128
└── max_depth: int = 8
```

- 型はboolを除くint。
- 値は `> 0`。Mitsuba固有の `-1` 等の特殊値は本GUI契約へ持ち込まない。
- 科学的な固定上限は設けない。GUIはnumber inputで `min=1`, `step=1` とし、
  任意の正整数presetを不要にclampしない。
- `MitsubaExportConfig.max_depth` の既定値8は変更しない。

### stage JSON version

- writerが出力する現行versionを `1.1.0` に上げる。
- 新readerは `1.0.0` と `1.1.0` を受理する。
- 1.0.0の `render` に `max_depth` は許可しない。旧schemaの未知field拒否を維持する。
- 1.0.0を読む場合、`max_depth=8` を補完する。
- 1.1.0では `render.max_depth` を任意fieldとして許可し、省略時は8を補完する。
- serializerは1.1.0と全render fieldを明示する。
- 1.0.0/1.1.0以外は従来どおり明示的に拒否する。

minor versionを使う理由は、既存fieldの意味を変えずoptional fieldを追加するため。
旧readerは1.1.0を読めないが、新readerによる旧presetの後方互換を保証する。

### CLI precedence

headless CLIへ `--max-depth N` を追加し、既存規則と同様に

```text
built-in default < stage preset < explicit CLI override
```

の順で決定する。`StageConfig.with_cli_overrides(max_depth=...)` を共通経路とし、
CLI側でStageConfigを迂回して `MitsubaExportConfig` だけを変更しない。

### Previewのdepth適用

previewの固定width/height/sppと、ユーザーが選んだmax depthを分離する。

- `_preview_render` をそのままStageConfigへ丸ごと代入する実装をやめる。
- preview configは現在config.renderを基に、width/height/sppだけpreview値へ
  `replace()` し、`max_depth` は保持する。
- startup時のinitial previewにも同じhelper／同じ規則を使い、初期presetのdepthを
  落とさない。

### Previewのrebuild分類

- `_structure_key()` に `config.render.max_depth` を含める。
- depthが変わると `TraversedPreviewScene.render()` は直接 `rebuild()` を選ぶ。
- `_stage_dict()` はbase sceneのtop-level copyに加えてintegrator dictもcopyし、
  `max_depth` を現在configの値へ差し替える。base sceneのnested dictは変異させない。
- depth以外のstage連続値は従来どおりtraverse経路を維持する。
- depth変更後の次の色・ライト変更が再びtraverseへ戻ることを検証する。

`prepare_mitsuba_scene()` の再実行はpreview depth変更には不要とする。integratorだけを
差し替えたscene dictを `mi.load_dict()` すればよく、PLYとgrid変換を繰り返さない。

### Finalとheadless

- `StageCore._ensure_final()` のcache keyを `(width, height, max_depth)` にする。
- final用 `MitsubaExportConfig` へmax depthを渡す。
- max depth変更だけではGUI操作時にfinal prepareを先行実行せず、`Render final` 時に
  必要ならprepareする。interactive previewを重くしない。
- finalの `scene-summary.json` はprepare時の実効depthをそのまま記録する。
- headlessも同じStageConfig値を `MitsubaExportConfig` へ渡す。

finalでdepth変更時にPLYが再生成される点はPhase 1では許容する。入力切替を扱う
Phase 2でwork directoryとscene lifecycleを再設計するため、ここでcacheを過度に
一般化しない。

## 対象ファイル

### 主変更

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage.py`
  - RenderSettings field／validation
  - stage JSON 1.0/1.1 reader
  - 1.1 writer
  - CLI override helper
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_demo.py`
  - `--max-depth`
  - MitsubaExportConfig伝播
  - 実効値ログ
- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
  - preview render override修正
  - structure key／integrator rebuild
  - final cache key／MitsubaExportConfig伝播
  - Renderタブwidget／StageBinder round-trip
  - status表示

### テスト・サンプル・文書

- stage config用unit test（既存適切ファイルへ追加、無ければ専用fileを新設）
- `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`
- `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
- `vdbmat/examples/pipeline_run/demo/presets/*.stage.json`
- `README_QUICK.md`
- 関連module docstring／CLI help

canonical exporter `vdbmat/src/vdbmat/exporters/mitsuba.py` は変更対象にしない。既に
config受取、integrator生成、summary記録を満たしているためである。

## 実装ステップ

### Step 1 — StageConfig schemaと互換reader

1. `RenderSettings.max_depth=8` と正整数validationを追加する。
2. current writer versionとaccepted versionsを分けて表現し、parserをversion別に
   検証する。単にversion checkを削除して全versionを許可しない。
3. 1.0.0では従来のrender keysだけ、1.1.0ではmax_depthを含むkeysを許可する。
4. serializerを1.1.0＋全field明示へ更新する。
5. `with_cli_overrides()` へmax_depthを追加する。
6. dataclass docstringとstage JSON説明を更新する。

このstep終了時点でMitsubaなしのunit testを通し、GUI変更前に設定契約を固定する。

### Step 2 — Headless経路

1. `mitsuba_stage_demo.py` に `--max-depth` を追加する。
2. StageConfigへのCLI最終上書きに接続する。
3. `MitsubaExportConfig(max_depth=stage.render.max_depth)` としてprepareする。
4. PIXELSTATSログへ `max_depth=N` を併記するか、直前に実効render設定を出す。
5. `scene-summary.json.render.max_depth` が選択値になることを検証する。

このstepで旧preset、1.1 preset、CLI overrideの3経路をheadlessで確認できる状態にする。

### Step 3 — Viewer coreと更新分類

1. preview用width/height/spp overrideをhelper化し、現在configのmax depthを保持する。
2. startup initial、interactive、settledの全preview経路で同じhelperを使用する。
3. preview scene dictのintegratorをcopyしてdepthを明示上書きする。
4. structure keyへmax depthを追加し、depth変更を予定されたrebuildにする。
5. final cache keyとfinal MitsubaExportConfigへdepthを追加する。
6. preview/finalのstatusまたは返却statsへ実効depthを含める。

既存traverse updaterへ存在しないintegrator keyを足さない。fallback例外を利用して
偶然rebuildさせる実装も採用しない。

### Step 4 — GUI binding

1. Renderタブへ `max depth` number inputを追加する。
2. 初期値はloaded StageConfigの値とする。
3. widget updateを既存 `_on_change()` へ接続する。
4. `StageBinder.current()` がwidth/height/spp/max depthを全て保持するようにする。
5. Save preset後のJSONとbinder currentのround-tripを確認する。

width/height/sppと同様のexact integer widgetとして扱い、lossy dirty trackingは
使用しない。

### Step 5 — Preset・文書

1. committed sample presetを1.1.0へ更新する。
2. `stage-default.stage.json` は `max_depth: 8` を明示する。
3. highkey sampleにも実効depthを明示するか、1.1.0の部分指定例として省略するかを
   実装時に統一する。少なくともdefaultは完全schema例とする。
4. README_QUICKのheadless/viewer例にmax depthとCLI precedenceを追加する。
5. viewer/module docstringの「render resolution/spp」を
   「resolution/spp/max depth」へ更新する。

## テスト計画

### Mitsuba不要のunit test

- `RenderSettings()` の既定depthが8。
- 正整数を受理し、0、負数、float、boolを拒否する。
- 1.0.0の旧presetを読むとdepth=8になる。
- 1.0.0に `render.max_depth` がある場合は未知fieldとして拒否する。
- 1.1.0で明示depthを読み、未指定時は8になる。
- serializerは1.1.0とmax depthを出力し、round-tripで同値になる。
- 未知versionを拒否する。
- CLI overrideはpreset値より優先し、未指定時はpreset値を保持する。
- preview render override helperがwidth/height/sppだけを変え、depthを保持する。
- structure keyはdepth差を構造変更として判定する。
- final cache keyは同解像度でもdepth差を区別する。
- workerのlatest-wins、final直列化、例外回復の既存テストを維持する。

### Mitsuba integration test

- `TraversedPreviewScene` でdepth変更時のrouteが `rebuild` になる。
- depth変更後の色変更は `traverse` に戻る。
- depth変更後のscene dict integratorが指定値を持つ。
- 指定depthのpreview rebuildと、同じdepthでfresh `mi.load_dict()` した結果を
  同一seed/sppで比較する。PIXELSTATSだけでなくHDR配列を比較する。
- final prepare後の `scene-summary.json.render.max_depth` が指定値になる。
- default depth=8の既存traverse/rebuild一致テストを壊さない。

### End-to-end回帰

- `nested_material_cube` でGUI相当のpreset保存→final render→headless replayを行い、
  同一variant/seedでPNGまたはHDRを比較する。
- depth=8で着手前と同じ既定出力になることを確認する。
- depth=16等の非既定値でGUI finalとheadlessが一致することを確認する。
- ガラス経路への効果確認として、depth=8と非既定depthの画像／PIXELSTATSを記録する。
  差が小さい場合でも設定伝播テストに合格していれば実装失敗とはしない。
- CPU/GPU variant間の画素一致は要求しない。同一variant内で比較する。

### 静的検査

- 変更Pythonへの `ruff check`
- 関連unit tests
- Mitsuba integration tests
- `git diff --check`

動作確認成果物は `.local/mitsubagui_improve/p1/` に置き、git管理しない。

## 実施順序

```text
StageConfig 1.1契約
    ↓
headless伝播
    ↓
viewer coreのrebuild境界
    ↓
GUI binding
    ↓
preset・統合検証・文書
```

設定契約を最初に固定し、headlessを基準実装として成立させてからviewerへ接続する。
GUIを先に変更して、保存できない／headless再現できない状態を中間成果としない。

## 非ゴール

- 入力 `optical.zarr` のGUI切替。
- optical mapping、material parameter、IOR、absorption、scatteringの変更。
- exterior/interior BSDF、roughness、surface modelの変更。
- OpenVDB入力。
- preview size、preview spp、variant、seedの新しいGUI widget。
- viewer session manifest。
- integrator plugin種別の切替。
- canonical exporterの既定max depth変更。
- `max_depth` の連続slider化やtraverse更新の模索。

## 完了条件

- `RenderSettings.max_depth` が既定8の正整数契約として存在する。
- stage config 1.1 writerと、1.0/1.1を読める後方互換readerがある。
- GUI Renderタブでmax depthを変更でき、Save presetへ保存される。
- previewのinteractive/settled双方、final、headlessへ同じ値が反映される。
- preview depth変更が `rebuild`、その後の連続stage変更が `traverse` になる。
- final scene summaryとGUI/headlessログから実効depthを確認できる。
- 旧1.0.0 presetはdepth=8で動作する。
- depth=8の既定挙動が維持される。
- 非既定depthでGUI finalとheadless replayが同一条件・同一結果になる。
- canonical exporter、volume、boundary mesh、material mappingに変更がない。
- unit/integration/static checksが通り、検証成果物が `.local` に隔離される。

## リスクと打ち切り条件

### StageConfigにrender transportを置く責務上の違和感

現行StageConfigが既にwidth/height/sppを所有し、GUI/headless presetの唯一契約として
運用されているため、Phase 1ではmax depthも同じrender節へ追加する。render設定を
独立schemaへ分離するのはPhase 3のsession manifest設計時に再評価し、本フェーズで
二重契約を作らない。

### 旧readerが1.1.0を読めない

新readerによる旧preset互換は保証するが、旧コードへのforward compatibilityは
保証できない。writer versionを偽って1.0.0のままfield追加するより、minor versionで
契約差を明示する。必要なら移行手順として `max_depth` field削除＋version 1.0.0への
書換えを文書化するが、自動downgrade writerは作らない。

### Previewのbase summaryと実効depthが異なる

previewは性能上、depth変更ごとに `prepare_mitsuba_scene()` を再実行せずintegrator
dictだけを再loadする。このためstartup時に書かれた `preview_scene/scene-summary.json`
は変更後depthを表さない可能性がある。GUI statusをpreviewの実効値の正とし、final
summaryは必ず実効値で再prepareする。この区別を文書化する。

### Final depth変更でPLYが再生成される

Phase 1では正しいsummaryと単純なcache keyを優先して許容する。実測で重大な遅延が
ある場合も、canonical exporterへ特殊cacheを追加せず、Phase 2のsession core計画へ
測定結果を引き継ぐ。

### depthを上げても見た目が期待ほど変わらない

max depthは光路上限であり、Fresnel反射率やsurface roughnessを直接変更しない。
見た目の改善量をPhase 1の合否条件にしない。設定伝播と再現性を合否条件とし、
roughness／surface modelはロードマップPhase 6の独立課題として残す。

### 非常に大きいdepthでレンダーが遅くなる

正整数上限をschemaに設けず、GUI statusと文書でコストを示す。workerは既存の
latest-winsとfinal直列化を維持する。操作不能になる実測が得られた場合のみ、
GUI側の警告閾値またはApply操作を追加し、科学設定を黙ってclampしない。

