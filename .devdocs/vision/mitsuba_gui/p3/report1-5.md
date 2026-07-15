# mitsuba_gui Phase 3 実施報告 — Step 1〜5

`plan.md` の順序どおり、Step 1（traverse 契約 probe）→ Step 2（preview scene
常駐化）→ Step 3（漸進 worker）→ Step 4（自動・実入力検証）→ Step 5
（文書化）まで完了した。

## 変更内容

- 更新: `vdbmat/examples/pipeline_run/demo/mitsuba_stage_viewer.py`
  - `TraversedPreviewScene` を追加。preview scene を一度 load して保持し、
    `mi.traverse()` で radiance、色、checker `to_uv`、shape / sensor の
    `to_world`、`sensor.x_fov` を更新する。
  - StageConfig の値から transform を別実装せず、既存 `apply_stage()` が作る
    scene dict を更新値の正本として使う。これにより Phase 1 の stage 幾何契約と
    差分更新の計算が乖離しない。
  - `structure_key` は backdrop / floor の enabled と pattern、key light enabled、
    camera / backlight override の有無。これが変わる場合だけ fresh scene を
    rebuild し、直後から再び traverse 更新へ戻る。
  - traverse キー欠落・型不適合・update 失敗時は理由を stderr に出し、その1回を
    `rebuild-fallback` として再構築する。古い scene のまま描画は続けない。
  - final render は Phase 2 の fresh build 経路を維持し、headless 再現の基準として
    残した。StageConfig、`mitsuba_stage.py`、canonical exporter は無変更。
  - `RenderWorker` を generation 付き immediate / settled の2段階へ変更。
    update 直後は `--interactive-spp`（既定4）、静止後は `--preview-spp`
    （既定16）で描画する。レンダー前後の generation が古い結果は publish せず、
    final job と Mitsuba render は従来どおり単一 thread で直列化する。
  - CLI に `--interactive-spp` / `--settle-delay` を追加し、正値および
    `interactive-spp <= preview-spp` を検証する。
  - GUI status は `interactive|settled / traverse|rebuild`、所要時間、
    PIXELSTATS を表示する。
- 新規: `vdbmat/tests/test_mitsuba_stage_viewer_worker.py`
  - coarse 実行中に新設定が来た場合の stale publish 防止。
  - burst の最新値だけが interactive → settled へ進むこと。
  - final job と preview の直列化、CLI の spp 組合せ検証。
- 新規: `vdbmat/tests/integration/test_mitsuba_stage_viewer.py`
  - 色、checker scale、backdrop/floor/key-light transform、key/backlight radiance、
    camera transform/FOV の traverse 経路を fresh rebuild と比較。
  - checker → solid が rebuild となり、次の solid 色変更が traverse に復帰する
    ことを検証。
- 更新: `README_QUICK.md`
  - 2段階 preview、新CLI、status の traverse / rebuild の意味を追記。
- 新規依存なし。`pyproject.toml` / `uv.lock` / `src/` 配下は無変更。

## Step 1 — traverse 契約 probe 結果

ホストの Mitsuba `llvm_ad_rgb` と `marble-like` の小解像度 scene で、以下の
更新可能キーと実際の値型を確認した。

- `stage_key_light.emitter.radiance.value` (`Color3f`)
- `stage_key_light.to_world`、backdrop / floor / sensor の `to_world`
  (`AffineTransform4f`)
- checker の `color0.value` / `color1.value` (`Color3f`) と `to_uv`
  (`ScalarAffineTransform3f`)
- `backlight.emitter.radiance.value` (`Color3f`)
- `sensor.x_fov` (`Float`)

キーを列挙しただけでなく、全項目を代入 → `params.update()` → render まで実行し、
描画へ反映されることを確認した。checker / solid と enabled 切替は予想どおり
キー集合または shape 数が変わるため rebuild 対象とした。camera / backlight の
null 切替も canonical passthrough 境界を明確に保つため rebuild 対象とした。

## Step 4 — 検証結果

動作確認の生成物は `.local/mitsuba_gui/p3/` のみに保存した。

### 自動テスト・静的検査

- `ruff check`: `All checks passed!`
- `py_compile`: 成功。
- worker unit + Phase 3 integration + 既存 Mitsuba integration:
  **15 passed**。リポジトリ全体は **375 passed, 2 skipped**（ホストにない
  `pyopenvdb` を必要とする既知の2件のみskip）。
- traverse / fresh rebuild の HDR 比較は多くの要素が完全一致し、transform 等を
  含む最大絶対差は synthetic fixture で `1e-5` 未満、ローカル marble probe で
  `2.4e-7` 以下だった。Mitsuba の scene 再構築と in-place update による float
  evaluation の差として十分小さく、テストは `rtol=0`, `atol=1e-5` で固定した。
  PIXELSTATS だけの比較にはしていない。

### 漸進レンダーと実測

既定 preview 解像度 256²、interactive spp4、settled spp16 で、key-light radiance
を traverse 更新した実測:

| input | interactive | settled | route |
|---|---:|---:|---|
| nested_material_cube | 0.064 秒 | 0.194 秒 | traverse |
| marble-like | 0.234 秒 | 0.054 秒 | traverse |

初回 JIT / scene の状態で前後するため settled が常に遅いとは限らないが、双方とも
目標の1秒以内を十分満たした。worker テストでは、古い interactive 完了後に新しい
generation が存在する場合、その画像が一度も publish されないことを確認した。

### GUI起動・プリセット往復

- marble-like を 32²/spp2 で実GUIサーバ起動し、viser の HTTP / WebSocket
  endpoint が立ち、初回 interactive / settled render がエラーなく完了した。
- camera override を含む設定を保存し、viewer final と
  `mitsuba_stage_demo.py --stage-config` を別々に実行した。
  PIXELSTATS は双方
  `min=0 max=2.83554 mean=0.0719031 std=0.183676`、PNG は
  `np.array_equal=True`（最大差0）だった。
- `nested_material_cube` / `marble-like` の双方で256²の traverse preview を実行し、
  エラーや fallback は発生しなかった。Phase 2 で確立した final/headless 経路は
  本フェーズでは変更していない。

## 完了条件との対応

- 同一構造内で `mi.load_dict()` せず params update: 達成。
- 構造変更だけ rebuild、次の連続値で traverse 復帰: 達成。
- immediate → settled、latest-wins、stale publish 防止: 達成。
- traverse / rebuild HDR 一致: 厳しい絶対許容差 `1e-5` 内で達成。
- preset → viewer final → headless の全画素一致: 達成。
- interactive preview 概ね1秒以内: 実測0.06〜0.23秒で達成。
- canonical exporter / medium / geometry / StageConfig schema / dependency group
  不変: 達成。

## 制約・留意事項

- Mitsuba の実行中 render 自体は cancel しない。新しい generation が来た場合は
  完了済みの古い画像を破棄して最新値へ進む。このため極端に重い入力では現在の
  coarse render 1回分の待ち時間は残る。
- preview は段階間で同じ解像度を使い、spp のみを変更する。低解像度を望む場合は
  `--preview-size 192` 等を指定する。段階ごとの film 再構築は導入していない。
- traverse / rebuild 間には最大 `1e-5` 未満のHDR浮動小数差があり得るが、final と
  headless は同じ fresh build 経路なのでPNG再現性には影響しない。
- GUI callback を含む実ブラウザの長時間ドラッグ試験は自動化していない。
  generation / worker の競合部分は決定的な単体テストで検証し、viser server の
  起動と初回描画は実プロセスで smoke test した。

## 未実施・保留事項

- render cancel、段階別解像度、adaptive sampling は非ゴールのため未実施。
- すべての予定 traverse 項目が更新可能だったため、項目単位の恒久 rebuild 化や
  Phase 3 の縮小打ち切りは不要だった。

## 動作確認後の追補 — CUDA backend

Quadro RTX 8000 搭載環境でGPU利用を選択できるよう、viewer と headless demo に
`--variant llvm_ad_rgb|cuda_ad_rgb` を追加した。既定はGPUのない環境との互換性を
保つためCPUの `llvm_ad_rgb` のままとした。64²/spp4 の
`nested_material_cube` を `cuda_ad_rgb` で実レンダーし、scene summary の variant
が `cuda_ad_rgb`、PNG出力とPIXELSTATS生成が成功することを確認した。canonical
`MitsubaExportConfig` の既定値は変更していない。
