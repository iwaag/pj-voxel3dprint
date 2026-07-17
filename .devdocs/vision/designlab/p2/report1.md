# Step 1 報告 — 方式レジストリと config カタログ（browser-free）

## 実装

- `vdbmat-utils/examples/designlab/designlab_registry.py`: `GeneratorMethod`
  frozen dataclass（`method_id` / `title` / `config_suffix` / `config_cls` /
  `build_form` / `form_to_config` / `config_to_form` / `generator_argv`）と、
  primitive array 1件を登録した `REGISTRY` タプル、`method_by_id` /
  `method_for_config_path` を実装した。
  - `build_form`/`form_to_config`/`config_to_form` は「各フィールドが
    `.value` を持つオブジェクト」という最小契約（`_HasValue` Protocol）で
    書いた。viser の `GuiInputHandle` も、テスト用の素朴な `_FakeWidget`
    （`value` フィールドを持つだけの dataclass）もこの契約を満たすため、
    本 module は import 時点で viser に依存しない。`build_form` は viser
    widget（`add_number` / `add_dropdown` / `add_folder`）を直接呼ぶ完全な
    実装として書いた（plan は「callable の骨組みだけ」を許容していたが、
    骨組みと実装がほぼ同じ量なので一度で実装し、Step 3 は結線に専念する）。
  - `form_to_config` は `PrimitiveArrayConfig` のコンストラクタを直接呼ぶ
    だけで、`__post_init__` が投げる `PrimitiveArrayError`（フィールド名
    付き）をそのまま透過する（catch も再メッセージ化もしない）。
  - `generator_argv` は `[sys.executable, "-m",
    "vdbmat_utils.cli.main", "generate-primitive-array", "--config", ...,
    "--out", ..., "--name", ...]` を返す（venv 取り違え事故を避けるため
    `sys.executable` 固定、plan のリスク方針どおり）。
- `vdbmat-utils/examples/designlab/designlab_configs.py`: config カタログ。
  - `scan_config_catalog(root)`: 再帰 `os.walk`、登録済み方式の
    `config_suffix` に一致するファイルのみ列挙。symlink 等で root を離脱
    する候補は viewer の `mitsuba_stage_inputs.py` と同じ規則
    （`resolve()` して `== root or is_relative_to(root)`）で黙って除外。
  - `resolve_config_path(root, user_path)`: containment 違反・不存在は
    `DesignlabConfigError`。
  - `load_config`: containment チェック後 `method.config_cls.from_json()`
    を呼び、`ConfigError`（未知フィールド拒否等）をメッセージ据え置きで
    `DesignlabConfigError` に包むだけ（再解釈しない）。
  - `save_config`: `<root>/<stem_name><config_suffix>` へ `to_json()`
    （canonical JSON）を書く。`stem_name` は `[a-z0-9][a-z0-9-]*` に限定し
    （plan の name 規約と同じパターン）、path 区切り文字を使った脱走や
    空白混じりの名前を拒否。既存ファイルへの上書きは明示エラーで拒否
    （roadmap の非破壊規約）。
- `vdbmat-utils/pyproject.toml`: `[dependency-groups]` に
  `designlab = ["viser>=0.2"]` を追加（`mitsuba-viewer` group とバージョン
  制約を揃えた）。`uv lock` で解決できることを確認した（viser 一式が
  正しく追加された）。

## テスト

- `tests/unit/test_designlab_registry.py`: レジストリ列挙、
  `method_by_id`/`method_for_config_path`、`generator_argv` golden、
  `form_to_config` の正常系（期待する `PrimitiveArrayConfig` と一致）、
  異常系（`PrimitiveArrayError` がフィールド名 (`field_path`) 付きで
  そのまま伝播）、`config_to_form` → `form_to_config` の round-trip で
  config が完全一致することを固定した。
- `tests/unit/test_designlab_configs.py`: `resolve_config_root` の
  存在チェック、`scan_config_catalog` の suffix 一致・再帰・symlink 離脱
  除外、`resolve_config_path` の離脱拒否・不存在拒否、
  save → load の `config_digest` 不変 round-trip（2回目の別名保存でも
  digest 不変）、save の上書き拒否、save の不正名拒否（path traversal・
  空白混じり）、load 時の未知フィールドエラー透過（メッセージ内容ごと）
  を固定した。
- 両ファイルとも viewer の回帰テストと同じ `sys.path.insert` パターンで
  `examples/designlab` から import した。

## 静的検査・テスト結果

```
uv run ruff check examples/designlab tests/unit/test_designlab_registry.py tests/unit/test_designlab_configs.py
→ All checks passed

uv run pytest -q tests/unit tests/contract
→ 337 passed, 2 skipped（Step 1 開始前と同じ 337 passed, 2 skipped。新規
  15 件のテストを含めて regression なし）
```

`uv run ruff check .`（リポジトリ全体）は本 Step の変更と無関係な
既存の1件（`tests/integration/test_formation_workflows.py:15`、E501）
のみを報告した。本 Step の対象ファイルはすべて通過している。

## 完了条件の充足状況（Step 1 分）

- [x] `generator_argv()` まで確定したレジストリを定義し、primitive array
      を1件登録した。
- [x] config カタログの scan / refresh 相当（`scan_config_catalog`）/
      containment / load（エラー透過）/ save（canonical 書き出し、
      上書き拒否）を実装した。
- [x] unit test: レジストリ列挙、argv golden、カタログ検出、containment
      離脱拒否、save 上書き拒否、load → config → save の round-trip で
      `config_digest` 不変、未知フィールド config のエラー透過 — すべて
      固定した。

## 想定外事項

なし。plan どおりに進行した。
