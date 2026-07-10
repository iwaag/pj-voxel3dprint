# Step 10 実施報告: OpenVDB / Blender Cycles Consumer Proof

実施日: 2026-06-29

## 結果

Step 10 の実装を完了した。canonical `OpticalPropertyVolume` から OpenVDB の
named `FloatGrid` 群へ変換するアダプター、固定設定の Blender Cycles シーン、
全 Phase 0 fixture の export/render ランナー、capability diagnostics、単体テスト、
optional integration test、再現手順を追加した。

ホストへのAPT導入にはsudoパスワードが必要だったため、Docker内にoptional native
runtimeを導入した。OpenVDB 10.0.1とBlender公式4.5.11 LTSを使用し、native `.vdb`
書き込み・再読込、全fixtureのBlender load、Cycles CPU renderを完了した。Step 10の
native runtime verification gateは通過した。

## 実装内容

- `src/vbdmat/exporters/openvdb.py`
  - canonical ZYX 配列を OpenVDB XYZ 配列へ明示的に転置する pure conversion
  - cell center を整数 VDB index に対応させる affine transform
  - anisotropic voxel size、rigid rotation、translation、metre unit の保持
  - `sigma_a_r/g/b`、`sigma_s_r/g/b`、`g`、`ior` の named grid
  - Cycles 用の明示的な RGB scalar reduction である
    `cycles_absorption` と `cycles_scattering`
  - `openvdb` / `pyopenvdb` の lazy import と `.vdb` writer
  - stable manifest と共通 `CapabilityReport`
- `examples/phase0/blender_cycles_volume.py`
  - VDB Volume object、Attribute nodes、Volume Absorption、Volume Scatter の構築
  - scattering-weighted global `g`
  - camera、area light、Cycles CPU、resolution、samples、seed、bounce limit、unit、
    PNG output の固定
  - required grid のロード確認、`.blend` 保存、headless render
- `examples/phase0/export_openvdb_fixtures.py`
  - 全 synthetic fixture の optical mapping と OpenVDB export
- `examples/phase0/render_blender_fixtures.py`
  - 全 exported fixture の Blender background render と PNG SHA-256 report
- `docs/openvdb/phase0-cycles-proof.md`
  - grid/transform/node contract、再現コマンド、制約、native gate を記録
- `docs/adr/0005-exporter-boundary.md`
  - OpenVDB/Cycles 固有の approximation と unsupported semantics を追記
- `tools/phase0/Dockerfile.openvdb-cycles`
  - OpenVDB 10.0.1とBlender公式4.5.11 LTSの再現可能なoptional runtime

## Adapter mapping と診断

| canonical semantic | OpenVDB / Cycles mapping | status |
| --- | --- | --- |
| geometry | XYZ grids + cell-centred affine in metres | transformed |
| coefficient units | Blender unit scale 1 m、density は `m^-1` | represented |
| optical basis | RGB grids は保持、Cycles は equal-weight scalar reduction | approximated |
| `sigma_a` | RGB component grids + `cycles_absorption` | approximated |
| `sigma_s` | RGB component grids + `cycles_scattering` | approximated |
| `g` | spatial grid を保持、Cycles node は scattering-weighted global scalar | approximated |
| `ior` | grid を保持するが Cycles volume shading には未接続 | unsupported |
| derived IOR interfaces | internal dielectric surface は生成しない | unsupported |
| provenance | VDB metadata + capability JSON | represented |

空間 `ior` と internal interface を黙って捨てず、artifact 内の `ior` grid と
machine-readable diagnostics に残した。renderer-specific reduction は exporter 内に隔離し、
core volume は変更しない。

## 自動検証

実行コマンド:

```text
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run python -m py_compile examples/phase0/blender_cycles_volume.py \
  examples/phase0/export_openvdb_fixtures.py \
  examples/phase0/render_blender_fixtures.py
git diff --check
```

結果:

- uv lock: success
- Ruff format/lint: success
- mypy strict: success (`27 source files`)
- host pytest: `232 passed, 3 skipped`（hostにはoptional runtimeを入れない設計）
- native container integration: `2 passed`
- Blender/export/render scripts の bytecode compile: success
- whitespace error: none

Step 10 で追加した常時実行テストは以下を確認する。

- grid 名、`float32`、XYZ dimensions、selected axis-marker values
- VDB integer index から canonical world-space cell center への affine mapping
- Cycles scalar reduction と scattering-weighted `g`
- 全 canonical semantic を網羅する capability report
- invalid export configuration の拒否
- fake OpenVDB binding を使った grid type、metadata、transform、write call、artifact
- optional native binding がある場合の grid readback、type、bounds、selected value、
  `indexToWorld`
- OpenVDB と Blender がある場合の全 fixture headless load/render

host側skipの内訳:

- `tests/integration/test_openvdb.py`: `openvdb` module なし
- `tests/integration/test_blender_cycles.py`: `openvdb` module なし
- `tests/integration/test_mitsuba.py`: Step 9 optional dependency なし

core package importはOpenVDB、Blender、Mitsubaを要求しない。optional runtimeは
`vbdmat-phase0-step10:blender4.5.11` Docker imageに隔離した。

## Native runtime gate の再現コマンド

導入済みDocker imageで次を実行する。

```bash
docker build -t vbdmat-phase0-step10:blender4.5.11 \
  -f tools/phase0/Dockerfile.openvdb-cycles .

docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e PYTHONPATH=/work/src -v "$PWD:/work" -w /work \
  vbdmat-phase0-step10:blender4.5.11 \
  python3 -m pytest -q tests/integration/test_openvdb.py \
  tests/integration/test_blender_cycles.py
```

native gateでは全fixtureのgrid inspection、Blender load/render、axis-markerの
orientation/scale、生成PNGと`.blend`、render reportを確認し、すべて通過した。

## Native実行結果

- OpenVDB: 10.0.1、module名 `pyopenvdb`
- Blender: 4.5.11 LTS official Linux build、Cycles CPU
- image: `vbdmat-phase0-step10:blender4.5.11`
- OpenVDB integration: `1 passed`
- Blender/Cycles integration: `1 passed`（全6fixtures）
- 生成先:
  - `.local/phase0/openvdb-step10-native/`
  - `.local/phase0/cycles-step10-native/`
- 全6fixtureについて`.vdb`、PNG、`.blend`を生成
- `render-report.json`にPNG SHA-256を記録

Ubuntu package版Blender 4.0.2は、標準`density`だけの最小VDBでもCycles開始時に
SIGSEGVした。アダプター由来ではないことを切り分け、公式4.5.11 LTSへ変更して解決した。
またCPU-only buildで不要なdenoiserエラーを避けるため、proof sceneではdenoisingを
明示的に無効化した。
