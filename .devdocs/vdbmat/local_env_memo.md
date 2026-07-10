# ローカル開発環境メモ

## OpenVDB / Blender Cycles（Phase 0 Step 10）

OpenVDBとBlenderはホストへ直接インストールせず、Dockerイメージに隔離してある。
以降の作業では次のイメージを使用すること。

```text
vbdmat-phase0-step10:blender4.5.11
```

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
  vbdmat-phase0-step10:blender4.5.11 \
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
  vbdmat-phase0-step10:blender4.5.11 \
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
  vbdmat-phase0-step10:blender4.5.11 \
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
  -t vbdmat-phase0-step10:blender4.5.11 \
  -f tools/phase0/Dockerfile.openvdb-cycles \
  .
```

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
