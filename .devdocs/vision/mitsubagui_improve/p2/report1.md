# mitsubagui_improve Phase 2 実施報告 — Step 1

`plan.md` の Step 1（入力カタログmodule、Mitsuba/viser非依存）まで完了した。
この時点でカタログの列挙・containment検証・候補解決・概要生成の契約が
viewerに触れないunit testで固定されるため、独立したコミット境界として適切と
判断した。Step 2以降のStageCore session化、transactional load/swap、
Inputタブ配線は未着手である。

## 変更内容

### 新module `mitsuba_stage_inputs.py`

`vdbmat/examples/pipeline_run/demo/mitsuba_stage_inputs.py` を新設した。
viser・Mitsubaはimportしない。

- `InputKind`（`run-bundle` / `optical-zarr`）、`InputCandidate`、
  `InputSummary`、`InputCatalogError`。
- `resolve_input_root(cli_root, initial_input)`: `--input-root` 明示時は
  それを解決して返す（directoryでなければ拒否）。未指定時は初期入力の
  親directoryを返す（初期入力がbundle rootでも単体`optical.zarr`でも
  同じ規則）。
- `scan_input_catalog(root)`: `os.walk` で走査し、bundle
  （`run.json` が file かつ `optical.zarr` が存在するdirectory）または
  `*.zarr` かつ manifestの `asset_type` が `optical-property` のdirectoryを
  検出したら、その配下へは降下しない。containment外（resolve後の実体パスが
  root外）のsymlinkは列挙から除外する。結果はroot相対パス昇順。
- `resolve_candidate(root, user_path)`: 直接指定にも同じcontainment検証を
  適用し、root外パス・root外symlink・存在しないパス・bundleでも
  optical-property単体でもない候補を `InputCatalogError` で拒否する。
- `describe_candidate(candidate)`: `inspect_volume()`（配列データ非読込）で
  schema name/version、shape_zyx、voxel_size_xyz_mを取得し、bundleなら
  `run.json` から `run_id` を追加する。provenanceの `sources` / `notes` は
  `inspect_volume` を介さず、zarr storeのmanifest属性（`attrs["vdbmat"]`）を
  直接読んで要約する。

### 列挙と概要生成の検証コストを意図的に分離した

計画の「カタログ列挙時はdirectory名とmanifest冒頭の判定だけで済ませ、
`read_volume()` による完全検証はLoad/Rebuildまで遅延する」という決定に
沿って、`scan_input_catalog` / `resolve_candidate` の候補判別は
`zarr.open_group(...).attrs` から `asset_type` フィールドだけを読む軽量判定に
留めた。`inspect_volume()`（配列declarationの整合性まで検証する、より重い
チェック）は `describe_candidate()` にのみ呼ばせている。そのため、
manifestの `asset_type` は正しく宣言されているが配列declarationが壊れている
storeは、スキャンには現れるがdescribe時に例外を返す
（`test_describe_candidate_raises_for_scanned_but_corrupted_optical_store` で
固定）。完全に読めない・asset_typeが読めないstoreはスキャン自体から除外される
（`test_scan_excludes_broken_zarr_named_store`）。

## テスト

`vdbmat/tests/test_mitsuba_stage_inputs.py` を新設した。Mitsubaは不要で、
`vdbmat.fixtures.transparent_opaque_interface()` と
`map_material_volume_to_optical()` で実データの小さなoptical/material
storeを作って検証する。

- bundleと単体optical storeの検出、material-labelの単体store・
  `optical.zarr` を欠くbundle・無関係のディレクトリ/ファイルの除外。
- bundle・zarr store内部（decoyの `nested.zarr` や `run.json`）へ
  降下しないこと。
- 列挙順序の決定性（相対パス昇順、ネストしたパスを含む）。
- root外symlinkの列挙除外、`resolve_candidate` での直接指定・symlink
  経由のroot外拒否、存在しないパスの拒否。
- `resolve_input_root` のCLI明示・非directory拒否・初期入力（zarr/bundle
  それぞれ）からの既定値導出。
- `describe_candidate` の単体optical/bundle（run_id含む）概要生成。
- スキャンとdescribeの検証コスト分離（上記）。

## 検証結果

実行場所は `vdbmat/`。

```text
uv run pytest -q tests/test_mitsuba_stage_inputs.py
17 passed in 0.51s

uv run pytest -q --ignore=tests/integration
400 passed in 20.80s

uv run ruff check \
  examples/pipeline_run/demo/mitsuba_stage_inputs.py \
  tests/test_mitsuba_stage_inputs.py
All checks passed!

git diff --check
問題なし
```

`git status` は新規2ファイル（module本体とテスト）のみで、他の追跡ファイルへの
変更はない。

## コミット境界と未実施事項

Step 1は次の不変条件を単独で満たす。

- カタログ契約（`InputCandidate` / `InputSummary` / 列挙・containment・解決・
  概要生成のAPI）がviewer・Mitsuba・viserに依存せず固定されている。
- 列挙はbundle/zarr内部へ降下せず、決定的順序を返す。
- root外パス（直接指定・symlink双方）が拒否される。
- 列挙時の軽量判定とLoad/Rebuild時の完全検証（`inspect_volume`/
  `read_volume`）の責務分離が実装とテストの両方で表現されている。

この境界では以下は意図的に未実施で、`plan.md` の次Stepに残している。

- Step 2: `StageCore` のsession化（`InputSession` 抽出、per-input work
  directory、`session_generation` guard）。既存挙動を変えないrefactorとして
  Phase 1テスト一式を合否基準にする。
- Step 3: validate→prepare→load→smoke→swapのtransactional job。
- Step 4: Inputタブ（dropdown/Refresh/概要/Load・Rebuild button）と
  `mitsuba_stage_viewer.py` の `_parse_args()` への `--input-root` 追加・
  bundle受理。
- Step 5: 統合テスト、README追記、`.local` での実bundle往復切替の手動確認。

`mitsuba_stage.py`（stage-config契約）、`mitsuba_stage_demo.py`
（headless）、`mitsuba_stage_viewer.py`、canonical exporter・io・pipeline
（`src/vdbmat`）には変更していない。動作確認用のローカル成果物も生成して
いない。
