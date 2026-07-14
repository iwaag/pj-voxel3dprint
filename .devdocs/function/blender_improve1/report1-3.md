# blender_improve1 実装報告 — Step 1〜3

- **対象計画**: `.devdocs/function/blender_improve1/plan.md`
- **実施範囲**: Step 1〜3
- **ステータス**: 完了
- **コミット相当の境界**: PLY 外表面 + OpenVDB 内部媒質を
  1 回の Blender 実行でテンプレートへ配置し、保存・レンダーできるところまで

## 実施結果

新規に次を追加した。

- `vdbmat/examples/pipeline_run/demo/blender_template_hybrid.py`

既存の `blender_template_swap.py` は変更していない。外表面だけの従来経路と
ハイブリッド経路を分離し、後方互換を維持した。

## Step 1 — 入力契約と transform

デモ CLI は次を入力とする。

```text
TEMPLATE_BLEND MITSUBA_EXPORT_DIR OPENVDB_MANIFEST OUTPUT_PNG
[--target-object exterior-000] [--samples N] [--save-blend OUTPUT_BLEND]
```

実装したガード:

- Blender template、OpenVDB manifest、manifest が参照する VDB の存在確認。
- Mitsuba export ディレクトリの `exterior-*.ply` は正確に 1 個だけ受理。
  0 個/複数個は明示エラー。
- target は mesh object であること、collection に link されていることを確認。
- target transform は並進・回転・正の一様 scale のみ受理。
  zero scale、非一様 scale、shear、reflection は拒否。
- 入出力パスは `.blend` を開く前に絶対パス化。保存した `.blend` を
  別 working directory から開いても VDB を再ロードできるようにした。

## Step 2 — OpenVDB と Cycles volume material

- `openvdb-manifest.json` の `vdb`, `grid_names`, `phase_g`, `cycles.engine`
  を検証して読み込む。
- manifest 上と VDB 実体の両方で次の required grids を確認する。
  - `cycles_absorption`
  - `cycles_scattering`
- `vdbmat-cycles-volume` マテリアルに次のノード構成を作る。
  - Volume Absorption density ← `cycles_absorption`
  - Volume Scatter density ← `cycles_scattering`
  - Volume Scatter anisotropy ← manifest の `phase_g`
  - 両 shader を Add Shader で合成し Material Output / Volume へ接続
- VDB object/data は `vdbmat-volume`、マテリアルは
  `vdbmat-cycles-volume` の固定名とした。

## Step 3 — 外表面 + VDB の同時配置

- target の mesh data だけを `exterior-*.ply` と差し替える。テンプレート側の
  Glass material、object name、collection、transform は維持する。
- VDB object を target と同じ collection へ link し、target の `matrix_world`
  をコピーする。VDB 内の index-to-world transform は変更しない。
- template の camera、lighting、resolution、color management は維持する。
  render engine が Cycles 以外のテンプレートは拒否する。
- samples のみ CLI 指定時に上書きする。
- PNG に加え、`--save-blend` 指定時は調査用 `.blend` を保存する。
- `HYBRID` ログに target、PLY、VDB、scale、読み込んだ grid 一覧、
  `qualitative-uncalibrated` を出力する。レンダー後は `PIXELSTATS` も出力する。

## 検証結果

### 静的検査

```text
uv run --directory vdbmat ruff check \
  examples/pipeline_run/demo/blender_template_hybrid.py
All checks passed!

python3 -m py_compile \
  vdbmat/examples/pipeline_run/demo/blender_template_hybrid.py
exit 0
```

### 複数 exterior の拒否

外面が 3 group に分かれる既存 marble export を与え、レンダー前に
意図どおり拒否することを確認した。

```text
expected exactly one exterior-*.ply in .../marble_mitsuba, found 3
exit 1
```

### Blender 4.5.11 LTS success smoke

pinned Docker image 内で既存 `homogeneous-transparent` の対応する
Mitsuba/OpenVDB export を使用した。

```text
HYBRID target=exterior-000 exterior=exterior-000.ply
vdb=homogeneous-transparent.vdb scale=20
grids=cycles_absorption,cycles_scattering,g,ior,
      sigma_a_b,sigma_a_g,sigma_a_r,sigma_s_b,sigma_s_g,sigma_s_r
mode=qualitative-uncalibrated
PIXELSTATS target=exterior-000 volume=vdbmat-volume
min=0.0000 max=0.0039 mean=0.0003 std=0.0011
exit 0
```

成果物:

- PNG: 2048 x 2048 RGBA、909,363 bytes
- `.blend`: 11,205,645 bytes

保存した `.blend` を `/tmp` working directory から再オープンし、次を確認した。

- `exterior-000` は `MESH`、`vdbmat-volume` は `VOLUME`。
- 両 object の `matrix_world` は一致。
- VDB filepath は絶対パスで保存。
- VDB を再 load でき、required grids を含む 10 grids が復元される。
- volume material に Output / Absorption / Scatter / Add / Attribute x2 が残る。

### 既存 Cycles 統合テスト

```text
docker ... python3 -m pytest -q tests/integration/test_blender_cycles.py
1 passed, 1 warning in 2.23s
```

warning は `numcodecs` の crc32c deprecation であり、今回の実装とは無関係。

## 判明した既存テンプレート側の注意点

`.local/local_demo/template_scene/cube_diorama.blend` は Blender 5.1 系で保存された
ファイルで、pinned Blender 4.5.11 LTS では次の warning が出る。

```text
Warning: File written by newer Blender binary (501.30), expect loss of data!
```

この環境で生成した smoke PNG はほぼ黒い。ただし、既存の
`blender_template_swap.py` で外表面だけを同条件でレンダーしても、
次の完全に同じ `PIXELSTATS` になった。

```text
min=0.0000 max=0.0039 mean=0.0003 std=0.0011
```

したがって、ハイブリッド追加による退行ではなく、新しい Blender で作成した
テンプレートを 4.5.11 で開いた際の互換性またはテンプレートの光量設定に
由来する既存事項と判断した。

Step 1〜3 の完了条件は「テンプレートへの PLY/VDB 配置、ノード接続、
保存、Cycles レンダー完走」であり、これらは達成している。
不透明コアの視認性は Step 4 の代表入力追加後に判定する。

## 次の実装境界

Step 4 で決定的な入れ子キューブ入力を追加する。その入力から
`optical.zarr` / Mitsuba exterior / OpenVDB を生成し、Step 5 で外表面だけと
ハイブリッドの差分、不透明コアの視認性、テンプレート互換性を確認する。
