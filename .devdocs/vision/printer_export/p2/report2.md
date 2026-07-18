# Step 2 報告 — levels の rgb 対応（`image/stack.py`）

## 実施内容

`ImageStackConfig.levels` の各エントリが `gray`（既存）または `rgb`
（新規、`[r, g, b]` 各 0..255）のどちらか一方を持てるよう `_parse_levels`
を拡張した。

- `_parse_levels` の戻り値を `(gray_to_id, palette)` から
  `(mode, key_to_id, palette)` に変更（`mode` は `"gray"` / `"rgb"`）。
  `key_to_id` は gray モードなら gray 値、rgb モードなら packed RGB
  （`r<<16 | g<<8 | b`）をキーとする。
- 排他検証: エントリ単位で `gray`/`rgb` の両方または欠落はエラー、
  config 単位で gray/rgb エントリの混在はエラー（plan の決定事項どおり）。
- rgb 重複は gray 重複と対称なエラー文言。
- rgb モードは `config.format == "png"` のみ許可（PGM 指定時は
  `require config.format 'png'` を含む明示エラー）。
- 読込・パック・lookup: `_read_color_slice()` が `read_png_rgb()` で
  `(H, W, 3)` を読み `(H, W)` packed int64 へ変換。`_apply_lookup()` は
  gray/rgb 共通の searchsorted ベースの lookup（gray も同じ経路に統一）。
- undeclared 検出: `_first_undeclared_pixel()` を値表示コールバック
  （`_describe_gray` / `_describe_rgb`）でパラメータ化し、rgb の場合は
  `RGB [r, g, b]` 形式でエラーに出す。
- provenance `notes` は rgb モードで
  `"layered color-label image stack; rows=+Y, columns=+X"` に変更（軸規約は
  共通のまま）。

### 既存呼び出し元の追従（想定外の発見）

`morph/keyslices.py::load_key_slices()` が `_parse_levels()` を直接呼んで
おり、戻り値のタプル形が変わったことで壊れた（`ValueError: too many
values to unpack`）。plan では `image/stack.py` と契約テストのみが対象
だったが、`_parse_levels` は private とはいえパッケージ内共有ヘルパ
だったため、呼び出し側の追従が必要だった。

morph は rgb levels を扱う設計ではない（plan の非ゴール外・往復契約は
`convert-image-stack` 専用）ため、`mode == "rgb"` の場合は
`"config.levels: 'rgb' entries are not supported by morph-stack; use
'gray' levels"` を明示エラーとして返すようにし、`gray` モードの既存動作は
無変更にした。既存 `test_morph.py` / `test_morph_pipeline_contract.py`
がすべて無変更で通ることを確認済み。

## テスト

### unit（`tests/unit/test_image_stack.py`）

rgb 版の受理/拒否境界を追加（gray 系既存テストは無変更）:

1. rgb levels で等価な gray スタックと同一の material_id 配列
   （`write_indexed_png()` で書いた P モード PNG の読み戻し検証込み）。
2. gray/rgb 混在禁止、エントリ単位の両方/欠落禁止。
3. rgb 重複、値域外（`rgb.r` 等）。
4. rgb + PGM 拒否。
5. undeclared RGB 値の位置つきエラー（`RGB [r, g, b]` 表示）。

### contract（`tests/contract/test_image_stack_contract.py`）

既存 gray ケースはすべて無変更で通過（純追加の証明）。rgb 版を追加:

1. `test_rgb_double_run_is_byte_equal`
2. `test_rgb_golden_digests`（payload/manifest sha256 pin）
3. `test_rgb_config_digest_stable`
   （plan では canonical JSON round-trip の等価性比較を想定していたが、
   `GeneratorConfig` の JSON 復元は `voxel_size_xyz_m` 等をリストのまま
   保持し dataclass の tuple フィールドと `==` で一致しない実装済みの
   挙動があり、既存 gray 契約テストにも同種の等価性テストは無いため、
   代わりに configuration digest の安定性で契約水準を揃えた）。
4. `test_rgb_material_count_conservation`

## 実行結果

```text
uv run pytest -q tests/unit tests/contract   # 449 passed（p2 step1完了時 436 + 13、回帰なし）
uv run ruff check src/vdbmat_utils/image/stack.py src/vdbmat_utils/morph/keyslices.py \
  tests/unit/test_image_stack.py tests/contract/test_image_stack_contract.py   # clean
```

## 次ステップへの申し送り

Step 3（`printer/roundtrip.py`）はサイドカーマニフェストの `palette` から
`rgb` levels エントリを機械導出する。本ステップで固定した rgb levels
スキーマ・エラー文言をそのまま利用できる状態になっている。
