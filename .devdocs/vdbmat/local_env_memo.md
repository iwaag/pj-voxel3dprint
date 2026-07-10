# ローカル開発環境メモ

## OpenVDB / Blender Cycles

OpenVDBとBlenderはホストへ直接インストールせず、Dockerイメージに隔離してある。
イメージ名・Dockerfileパスは開発フェーズ番号に依存させず、ツール内容ベースで
固定している（フェーズが進むたびに新旧イメージが並立して混乱するのを避けるため）。
以降の作業では次のイメージを使用すること。

```text
vdbmat-openvdb-cycles:blender4.5.11
```

venv入りのため、zarrが必要な場面（下記「Phase 1以降（zarr経由）のワークフロー」）も
system-site-packages経由でpyopenvdbも参照できるため、Phase 0のnative統合テストも
このイメージ1つで問題なく通る。

収録環境:

- Ubuntu 24.04
- OpenVDB 10.0.1（Python module名は `pyopenvdb`）
- Blender 4.5.11 LTS公式Linux build
- Cycles CPU renderer
- Python 3.12 / NumPy / pytest

ホストには`openvdb`/`pyopenvdb` Python moduleと`blender`コマンドはない。
通常の`uv run`ではnative integration testがskipされるため、次のDockerコマンドを使う。

### Native integration test

リポジトリルートで実行する。

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/work/src \
  -v "$PWD:/work" \
  -w /work \
  vdbmat-openvdb-cycles:blender4.5.11 \
  python3 -m pytest -q \
  tests/integration/test_openvdb.py \
  tests/integration/test_blender_cycles.py
```

確認済み結果は`2 passed`。

### 全fixtureのOpenVDB export

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONPATH=/work/src \
  -v "$PWD:/work" \
  -w /work \
  vdbmat-openvdb-cycles:blender4.5.11 \
  python3 examples/phase0/export_openvdb_fixtures.py \
  .local/phase0/openvdb-step10-native
```

### 全fixtureのBlender Cycles render

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/work" \
  -w /work \
  vdbmat-openvdb-cycles:blender4.5.11 \
  python3 examples/phase0/render_blender_fixtures.py \
  .local/phase0/openvdb-step10-native \
  .local/phase0/cycles-step10-native \
  --blender blender
```

生成済み成果物:

- `.local/phase0/openvdb-step10-native/`: 6個のVDBとmanifest/diagnostics
- `.local/phase0/cycles-step10-native/`: 6個のPNG、6個の`.blend`、hash report

### イメージを再構築する場合

```bash
docker build \
  -t vdbmat-openvdb-cycles:blender4.5.11 \
  -f tools/Dockerfile.openvdb-cycles \
  .
```

## Phase 1以降（zarr経由）のワークフロー

`vdbmat run`が生成する`optical.zarr`を読む`vdbmat export openvdb`には、
イメージ内の`numpy==1.26.4` / `zarr==3.0.10`入りvenv（system-site-packages経由で
`pyopenvdb`も参照可能）を使う必要がある（システムの`python3`にはzarrが無く
`ModuleNotFoundError`になる）。このvenvは`ENV PATH`で最優先に通してあるので、
コンテナ内では単に`python3`と呼べばよい（venvの絶対パスをコマンドに書かない —
再buildのタイミングでディレクトリ名が変わることがあるため）。

例：`vdbmat-utils generate-formation` → `vdbmat run` → `vdbmat export openvdb`
→ Blenderレンダー、という一連の流れ。

```bash
# export openvdb（zarr → VDB）
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/work" -w /work/vdbmat \
  vdbmat-openvdb-cycles:blender4.5.11 bash -c "
    PYTHONPATH=/work/vdbmat/src python3 \
      -m vdbmat.cli.main export openvdb <OPTICAL_ZARR> <OUT_DIR> --overwrite
  "

# Blenderレンダー
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/work" -w /work \
  vdbmat-openvdb-cycles:blender4.5.11 \
  blender --background --python <RENDER_SCRIPT.py> -- <MANIFEST> <OUTPUT_PNG>
```

`--user "$(id -u):$(id -g)"`を忘れると生成物がroot所有になるので必ず付ける。
イメージが手元に無ければ`vdbmat/tools/Dockerfile.openvdb-cycles`から
同名でbuildし直せばよい（新規タグで作り直す必要はない）。

### 注意事項

- Ubuntu package版Blender 4.0.2は、最小VDBでもCycles開始時にSIGSEGVした。
  検証には必ず公式Blender 4.5.11 LTSを含む上記イメージを使う。
- CPU-only buildとの互換性のためproof sceneではdenoisingを無効化している。
- Docker volume内でroot所有ファイルを作らないよう、必ず
  `--user "$(id -u):$(id -g)"`を指定する。
- renderer依存をcore packageへ追加しない。OpenVDB/Blenderの利用はoptional
  integration境界に留める。
- 詳細は`docs/openvdb/phase0-cycles-proof.md`と
  `.local/phase0/report10.md`を参照する。
