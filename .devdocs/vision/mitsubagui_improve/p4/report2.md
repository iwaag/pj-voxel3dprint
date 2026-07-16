# mitsubagui_improve Phase 4 実施報告 — Step 2

`plan.md` の Step 2（派生bundle生成とcache、pure）まで完了した。この時点で、
canonical run bundleが保持する `source/*.voxels.json` を材料入力として選択mapping
を適用し、非破壊・transactionalに派生canonical bundleを発行する契約と、科学入力
（source payload digest × mapping digest）に基づくcache再利用契約が、viewer・
viser・Mitsubaへ触れずにunit testで固定された。Step 3以降のsession schema拡張、
GUI配線、headless replayは未着手である。

## 変更内容

### 新module `mitsuba_stage_regen.py`

`vdbmat/examples/pipeline_run/demo/mitsuba_stage_regen.py` を新設した。viser・
Mitsubaはimportしない。

- `RegenError(stage, message)`、`DerivedBundle`
  （`bundle_path`／`optical_zarr`／`mapping_digest`／`source_payload_sha256`／
  `reused`）。
- `locate_bundle_source(bundle_path) -> (manifest_path, source_payload_sha256)`:
  - `run.json` の `assets` から `source/*.voxels.json` に一致するentryを1件だけ
    特定する。0件・複数件は診断付きで拒否する。
  - 特定したmanifestを `inspect_material_label_manifest()` で読み、その
    manifest自身が宣言する payload sha256 と、`run.json` 直下の
    `input_payload_sha256` を突合する。不一致は
    「bundleのsource/が改変された可能性がある」旨のメッセージで拒否する。
  - この照合は2つの宣言値（manifest内 vs run.json）を比較する軽量チェックであり、
    payload実bytesの再hashは行わない。実bytes照合は既存
    `read_material_label_manifest()` が `run_pipeline()` の `load` stage内で
    独立に行うため、二重実装しない（改変されたpayload本体は `map` stage側で
    別途捕捉される）。
- `derived_bundle_key(source_payload_sha256, mapping_digest) -> str`:
  - `sha256(source_payload_sha256 + "\n" + mapping_digest)` の16進文字列。
- `regenerate_optical(source_bundle, mapping_candidate, work_root, *, on_stage=...)
  -> DerivedBundle`:
  1. `validate`: `locate_bundle_source()` とmapping読込
     （`load_optical_mapping()` を再利用、`OpticalMappingError` を
     `RegenError` へ変換）。
  2. cache key算出後、`work_root` 配下の出力先が `source_bundle` と重なって
     いないか（一致・内包どちらの向きも）を検証する。重なる場合は
     `validate` 段階で拒否し、`run_pipeline` の `overwrite=True` が
     source側を破壊する事態を未然に防ぐ。
  3. 出力先に既存 `run.json` があり、`input_payload_sha256` と
     `mapping_digest` の両方が一致すればそのまま `reused=True` で返す
     （pipeline実行もfile書込みもしない）。
  4. 不一致・欠落なら `map` 段階で in-memory `PipelineConfig`
     （`input_kind=direct-voxel`、`input_path=<bundleのsource manifest絶対path>`、
     `mapping_path=<選択mapping絶対path>`、`mapping_digest=<現在digest>`、
     `output_path=<work_root配下のcache path>`、`overwrite=True`、
     `validate_material=True`、`validate_optical=True`）を組み立て、
     `run_pipeline()` を呼ぶだけで済ませる。GUI独自のmapping適用・混合則・
     provenance生成は一切書いていない。

### 材料再生成の実装方針（plan Step 2の決定事項の実装確認）

`plan.md` が決定した「ユーザー契約は専用経路、実装機構は `run_pipeline()` 再利用」
をそのまま実装した。`regenerate_optical()` は以下を再利用するのみで、mapping適用
ロジックを二重化していない。

- `vdbmat.optics.load_optical_mapping()`（schema検証、`external_id` 拒否）
- `vdbmat.pipeline.PipelineConfig`（file-based mapping digest宣言と一致検証、
  input/output path解決）
- `vdbmat.pipeline.run_pipeline()`
  （load→validate/persist material→map-optics→validate/persist optical→
  summarize→atomic publish の全stage、`map_material_volume_to_optical()` による
  palette coverage／名前一致検証を含む）

`PipelineConfig` へ渡す `input_path`／`mapping_path` は解決済みの絶対pathを
そのまま文字列化して渡している（`_resolve_against()` は絶対pathをbase_dirへ
join せずそのまま使うため、`base_dir` の値自体は無関係になる）。この結果、
派生bundle内の `config.json` にはserver-local絶対pathが記録されるが、
派生bundleは常に `--mapping-work-root`（`.local` 相当の非git管理領域）以下に
のみ生成されるため、Phase 3のsession portability契約（git管理サンプルへ
絶対pathを書かない）とは抵触しない。この設計判断と、それに伴う既知の限界
（環境が変わると `config_digest` が変わり、結果として派生 `optical.zarr` の
store byte全体のdigestも変わり得ること。ただし科学的な配列内容自体は不変）は
`plan.md` のリスク節「派生bundleのdigestが環境間で再現しない」に記載済みであり、
本Stepのcache判定はこの影響を受けない設計にしてある（次項）。

### Cache判定は宣言digestの突合のみで行う

`plan.md` の決定事項どおり、cache有効性は出力先bundleの `run.json` に記録された
`input_payload_sha256`／`mapping_digest` の宣言値を読むだけで判定し、派生
`optical.zarr` の実bytesを再hashしない。壊れた・欠落した・不一致な既存出力先は
無条件で「cache無効」として扱い、`run_pipeline(..., overwrite=True)` の
atomic publishに委ねる（`run_pipeline` 自身が中断時に旧bundleを保全する）ため、
本module側で明示的なcleanup処理は持たない。

## テスト

`vdbmat/tests/test_mitsuba_stage_regen.py` を新設し、15ケースを追加した。
`vdbmat.fixtures.write_phase1_fixtures()` の決定的な `window_coupon` fixture
（材料ID 0/1/2/3、checked-inの `phase0-provisional-materials-v1` mappingで
palette coverageを満たす）を実際に `run_pipeline()` へ通して作った本物のcanonical
bundleに対してテストする。Mitsuba／viserは不要である。

主な検証:

- `locate_bundle_source()`: 正しいmanifest特定とdigest返却、`run.json` 欠落、
  改変されたouter digestの拒否、`source/*.voxels.json` 0件・複数件の拒否。
- `regenerate_optical()`:
  - 派生bundleの発行、`run.json`／`diagnostics/summary.json` への
    mapping digest記録。
  - 生成呼出しが元bundleの `optical.zarr`／`material.zarr` を一切変更しない
    （前後でdigest比較）。
  - 同一source×mappingの2回目呼出しが `reused=True` になり、出力先
    `run.json` のmtimeが変化しない（再実行していないことの直接証拠）。
  - mapping file編集後は新しいcache pathへ再生成され、digestが変わる。
  - `derived_bundle_key()` がsource／mapping片方だけの変更でも変わる。
  - 2種類のmappingが異なる派生 `optical.zarr` digestを生む。
  - 壊れたmapping JSON、材料不足（`material_id` 3欠落）、材料名不一致が
    それぞれ正しい段階名（`validate` または `map`）付きで拒否される。
  - `work_root` が `source_bundle` の内側を指す構成が `validate` 段階で
    拒否される。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q tests/test_mitsuba_stage_regen.py tests/test_mitsuba_stage_mappings.py
33 passed in 15.24s

uv run pytest -q --ignore=tests/integration
529 passed in 37.18s

uv run ruff check \
  examples/pipeline_run/demo/mitsuba_stage_regen.py \
  tests/test_mitsuba_stage_regen.py
All checks passed!

git diff --check
問題なし
```

本StepはMitsuba sceneやviewerへ配線しないpure pipeline呼出し処理であるため、
Mitsuba integration test、ブラウザ操作、ローカルrender成果物生成は実施していない。
既存のMitsuba不要suite全件（Phase 1〜3およびPhase 4 Step 1の回帰分を含む）を
通しで実行し、新規15件を加えた529件全てが通ることを確認した。

## コミット境界としての判断

Step 2完了地点を独立したコミット境界として適切と判断する。

この境界で次の不変条件が単独で成立する。

- bundle sourceの特定と、bundle内2箇所の宣言digestの整合性検証が独立して動作する。
- mapping適用は既存 `vdbmat.optics`／`vdbmat.pipeline` の再利用のみで実現され、
  GUI独自のmapping処理・簡易混合則・provenance生成を一切持たない。
- 派生bundleの生成は選択bundleとmapping fileのどちらへも書き込まない
  （unit testで前後digest比較により固定）。
- cache判定は宣言digestの突合のみで行われ、決定的な科学入力の組み合わせに対して
  無駄な再生成をしない契約がmtime不変テストで固定されている。
- mapping fileの外部編集がcache keyの変化として正しく反映される。
- source／work root衝突、mapping不正、材料不足、名前不一致がすべて段階名付きで
  拒否される。
- 新moduleはviser／Mitsuba非依存で、viewerやcanonical coreの挙動を変更していない。

変更対象は次の2fileだけである。

- `vdbmat/examples/pipeline_run/demo/mitsuba_stage_regen.py`
- `vdbmat/tests/test_mitsuba_stage_regen.py`

## 未実施事項

以下は計画どおり次のコミット境界以降に残している。

- Step 3: viewer session schema 1.1、`mapping` section、resolverのmapping-root／
  digest検証、派生digest照合の共通化。
- Step 4: `--mapping-root`／`--mapping-work-root` CLI、Inputタブのmapping選択、
  Load/Rebuildの `map` 段階配線、`InputSession.derivation`、Save/Load sessionの
  mapping対応。
- Step 5: headless session replayのmapping対応、サンプルmapping追加、統合検証、
  README。

`mitsuba_stage_mappings.py`、`mitsuba_viewer_session.py`、`mitsuba_stage_viewer.py`、
`mitsuba_stage_demo.py`、`mitsuba_stage_inputs.py`、canonical exporter／pipeline／
`src/vdbmat` は変更していない。動作確認用 `.local` 成果物も生成していない。
