# designlab ロードマップ — 入力モデルをGUIから設計・生成する input builder

## 背景

`mitsuba_gui` / `mitsubagui_improve` の両visionにより、`mitsuba_stage_viewer.py` は
既存のcanonical run bundle / `optical.zarr` を選択・検証・再構築し、mapping比較、
preset/session再現、headless再生まで行えるようになった。

一方、そのviewerへ渡す入力そのもの（material-label volume → bundle）は、現在も
`vdbmat-utils` の各CLI（`generate-formation`、`voxelize-mesh`、`convert-image-stack`、
`morph-stack`）へ手書きのconfig JSONを渡して作る前提である。configの雛形を探し、
フィールドを調べ、CLIを数段呼ぶ手順は、モデルを1つ試すたびの摩擦になっている。

**designlab** は、この入力生成側を穴埋めフォームのブラウザGUIにする新機能である。

- 生成方式のパラメータをフォームで入力し、configとしてsave/loadする。
- 生成 → `import-voxels` → `run`（optical mapping）→ bundle化までを一括実行する。
- 出力bundleを既存viewerの `--input-root` 配下へ置き、viewerのカタログ +
  Load/Rebuild をそのまま目視確認手段にする（リアルタイム連動はしない）。
- 生成方式を「1方式 = configスキーマ + フォーム + 実行コマンド」のレジストリとして
  抽象化し、方式を段階的に追加できるフレームワークを確立する。

最初のマイルストーンには、既存方式のGUI化ではなく、**新規の最小ジェネレータ
（primitive array）** を置く。透明母材の中に不透明な第二材料のcube/sphereを
A×B×C個リピート配置するだけの方式で、入力ファイルがゼロ、configが完全にフラット、
結果が「数を数えられる」形で目視検証できる。これでフォーム実装に工数を取られずに
パイプライン全体の動線を確立し、その後に既存方式をGUI化コストの低い順
（voxelize-mesh → convert-image-stack → morph-stack → generate-formation）で追加する。

本ロードマップはフェーズ境界を定める。各フェーズの具体的な変更箇所、API、
テストケースは、着手時に個別の実装planとして作成する。

## 破壊的変更の方針（このvision期間中の全フェーズに適用）

現在は破壊的変更のフェーズである。既存機能に変更が必要になった場合、
**後方互換性のためだけのアーティファクトを残さない**。

- 旧スキーマの読み込み経路、deprecatedエイリアス、互換shim、移行用フラグ、
  「旧動作を残すためだけの分岐」を追加しない。
- 変更するときは、呼び出し側・config・ドキュメント・テスト・examplesを
  同一フェーズ内で新契約へ一本化する。
- format versionは「現行契約の識別」のために維持するが、旧versionの受理を
  互換目的で温存しない。旧versionのファイルは明示的なエラーで拒否してよい。
- `.local` 配下のローカル成果物（過去に生成したbundle、session、preset）は
  再生成可能とみなし、読めなくなることを変更の妨げにしない。

この方針は「無断で壊してよい」ではない。壊す変更は実装planに明記し、
何が読めなくなるか・どう再生成するかを1行で書けることを条件とする。

## 用語と境界

### 生成方式（generator method）

designlabにおける1方式は次の3点で定義される。

1. **configスキーマ**: 既存CLIが受け取るconfig JSONそのもの
   （例: `MeshVoxelizeConfig`、formation config）。GUI専用の別形式を発明しない。
2. **フォーム定義**: configスキーマをGUIウィジェットへ対応付けたもの。
3. **実行コマンド**: `uv run vdbmat-utils <subcommand> ...` のサブプロセス呼び出し。

### 実行パイプライン

方式によらず、実行は共通の段を通る。

```text
form → config JSON（save/load対象）
     → vdbmat-utils <generator>（.voxels.json + .material_id.npy）
     → vdbmat import-voxels（material.zarr）
     → vdbmat run（optical.zarr、canonical bundle）
     → 出力root（= viewerの --input-root 配下）へ発行
```

GUIが保存したconfigをCLIで再実行すると同一digestの成果物が得られること
（**GUI=CLI再現契約**）を、stage preset / session と同じ思想で全方式に要求する。

### パッケージ境界

- ジェネレータ本体と契約テストは `vdbmat-utils` に置く。
- designlab GUIは独立したviserアプリとして作り、既存viewerへタブとして
  同居させない。vdbmat-utilsの実行はサブプロセス経由とし、`src/vdbmat` coreへ
  viser依存を追加しない。
- viewerとの連携は「出力rootを共有し、viewer側でRefresh + Load/Rebuild」の
  疎結合に限る。プロセス間通知や自動リロードは本visionの範囲外とする。

## 全体ゴール

ローカル開発者がブラウザGUI上で次を行えるようにする。

1. 生成方式を選び、パラメータを穴埋めフォームで入力する。
2. configをsave/loadし、既存configをテンプレートとして読み込む。
3. 一括実行で検証済みcanonical bundleを出力rootへ非破壊に発行する。
4. 既存viewerでその出力を選択し、目視確認する。
5. 保存したconfigをCLIで再実行し、同一成果物を再現する。
6. 新しい生成方式を、フレームワークの規約に沿って小さい差分で追加できる。

## 設計原則

### 1. configファイルが唯一の永続形式

save/loadの対象は既存CLIのconfig JSONそのものとする。GUIだけに存在する
永続設定を作らない。フォームで表現できないフィールドがある間は、
JSONテキスト編集とのハイブリッドを許す。

### 2. 実行はtransactionalに、発行はatomicに

生成〜bundle化は一時work directoryで行い、検証まで成功してから出力rootへ
atomicに発行する。失敗時は段階名を表示し、部分成果物を出力rootへ残さない。
viewerで確立したSTAGE表示（`validate → generate → import → map → publish`）の
パターンを踏襲する。

### 3. パスはserver-localな許可rootから選ぶ

config・入力アセット（STL、スライス画像）・出力は、起動引数で指定した
root以下に限定し、resolved pathがrootを離脱する候補は拒否する。
ブラウザからのファイルuploadはしない。viewerと同じcontainment規約を使う。

### 4. 最初の方式群はbuilt-in材料名に固定する

palette・optical-mapping生成の複雑さ（marble-likeで経験済みの材料名整合）を
初期フェーズから排除するため、Phase 1〜4の方式はvdbmat built-in材料名のみを
使い、チェックイン済みmappingで `vdbmat run` が通ることを保証する。
非built-in材料と `optical-mapping.json` の受け渡しはPhase 5（procedural）で扱う。

### 5. 方式追加のコストを毎フェーズ実測する

フレームワークの価値は「次の方式が安く足せるか」で測る。各方式追加フェーズの
報告に、レジストリ登録・フォーム定義・テスト以外に何を触ったかを記録し、
共通部への漏れを次フェーズ前に潰す。

## フェーズ構成

### Phase 1 — primitive array ジェネレータ（CLIのみ）

#### 目的

GUIより先にジェネレータをCLIとして完成させ、契約テストで枯らす。
「透明母材 + 不透明プリミティブのリピート配置」という、数個の穴埋めで
成立する最小方式を新設する。

#### スコープ

- `vdbmat-utils generate-primitive-array`（名称は実装planで確定）を追加する。
- config（完全フラット）:
  - `voxel_size_xyz_m`
  - `primitive`: `"cube" | "sphere"`
  - `counts_xyz`: 配置数 A×B×C
  - `primitive_size_m`、`gap_m`、`margin_m`
  - 材料: built-in名から選ぶ母材（既定 `transparent-resin`）と
    包含材（既定は既存の不透明built-in）
- グリッド形状はcounts・size・gap・marginから導出し、手入力させない。
  既存のサイズガード（`max_axis_cells` 等）を適用する。
- 乱数なし・完全決定論。既存規約どおり契約テストでpayload digest固定、
  double-run byte equality、ASCII previewを固定する。
- 出力は通常の `<name>.voxels.json` + `<name>.material_id.npy`。
- docs（`vdbmat-utils/docs/`）へ方式ドキュメントを追加する。

#### 非ゴール

- GUI。
- 非built-in材料、optical-mapping出力。
- 配置の乱択・ジッタ・グラデーション等の拡張パラメータ。

#### 完了条件

- config 1枚から `preview-slices` でA×B×C個のプリミティブが確認できる。
- 生成 → `import-voxels` → `run` → 既存viewerでの目視確認が手動CLIで通る。
- 契約テストが既存ジェネレータと同水準で揃っている。

### Phase 2 — designlab GUI最小成立（primitive array 1方式）

#### 目的

最初のマイルストーン。フォーム → save/load → 一括実行 → viewer確認の
動線全体を、1方式で端から端まで成立させ、方式レジストリの骨格を確立する。

#### スコープ

- 独立したviserアプリ `designlab`（配置は実装planで確定）を新設する。
  起動引数で `--config-root`（config save/load先）と `--output-root`
  （bundle発行先 = viewerの `--input-root` に指定する想定）を受け取る。
- 方式レジストリの最小骨格: 方式の列挙、方式選択ドロップダウン、
  方式ごとのフォーム構築・config round-trip・実行コマンド組み立ての
  インターフェースを定義する。登録は当面primitive arrayの1件。
- primitive arrayのフォーム（フラットウィジェットのみ）と、
  configのsave/load（`--config-root` 配下のカタログ + Refresh + containment）。
- Generateボタンで実行パイプライン（生成 → import → run → publish）を
  background jobとして走らせ、STAGE進行と失敗段階をstatusへ表示する。
- 発行されたbundleが既存viewerのInputカタログに現れ、Load/Rebuildで
  目視確認できることを確認する。
- GUI=CLI再現契約: GUIが保存したconfigをCLIで再実行し、payload digestが
  一致することをテストで固定する。

#### 非ゴール

- 2方式目以降。
- 入力アセット（ファイル/ディレクトリ）を取る方式への対応。
- viewerへの自動通知・自動リロード。
- designlab内でのレンダリングプレビュー。

#### 完了条件

- フォーム穴埋めだけで、viewerで数を数えられるbundleが出力rootに発行される。
- config save → load → 再実行で同一成果物になる。
- 実行失敗（不正パラメータ、サイズガード超過等）で部分成果物が
  出力rootへ残らず、失敗段階がGUIに表示される。
- 方式レジストリのインターフェースが文書化され、2方式目の追加手順が
  READMEレベルで書ける状態になっている。

### Phase 3 — voxelize-mesh 方式の追加（入力ファイルカタログの導入）

#### 目的

2方式目で「入力アセットを取る方式」への拡張点を確立する。configはフラットの
ままなので、新規UI概念はファイルカタログのみ。

#### スコープ

- 方式レジストリへ `voxelize-mesh` を登録する。フォームは
  `MeshVoxelizeConfig` のフラットフィールド（source_unit、voxel_size、
  材料、padding等）。
- `--asset-root` 配下のSTLカタログ（ドロップダウン + Refresh + containment）を
  フレームワーク共通部品として実装する。
- watertight違反・サイズガード等、CLIのactionableなエラーをGUIの失敗表示へ
  そのまま通す（メッセージの二重定義をしない）。
- Phase 2の再現契約・transactional発行をこの方式でも満たす。

#### 非ゴール

- STL以外のメッシュ形式、multi-mesh合成。
- domain明示指定等、CLIにある全フィールドの網羅（実装planで最小集合を選ぶ）。

#### 完了条件

- STLを選び、フォーム入力だけでbundleが発行され、viewerで確認できる。
- root外・非STL・非watertightの入力が段階名付きで拒否される。
- 方式追加で共通部に入った変更が報告に記録されている。

### Phase 4 — convert-image-stack / morph-stack 方式の追加（テーブル導入）

#### 目的

「均質な可変長テーブル」（`levels`）とディレクトリ入力を導入し、
morph-stackをほぼ差分ゼロで足すことでフレームワークの拡張容易性を実証する。

#### スコープ

- `levels`（gray → material）の行追加/削除つきテーブルウィジェットを
  共通部品として実装する。材料名はbuilt-in名のドロップダウンとする。
- `--asset-root` 配下のスライスディレクトリカタログ。
- `convert-image-stack` を登録し、続けて `morph-stack`
  （追加スカラー: `background`、`z_count`、`edge_policy` 等）を登録する。
- 2方式で共通化できなかった差分を計測し、レジストリ規約へ還元する。

#### 非ゴール

- スライス画像の内容プレビュー。
- PNG extra未導入環境でのPNG対応の作り込み（CLIのエラーを通すだけでよい）。

#### 完了条件

- 画像スタックとスパースキー・スライスの両方からbundleを発行し、
  viewerで確認できる。
- morph-stackの追加差分が「レジストリ登録 + フォーム定義 + テスト」に
  収まっている（収まらなければ理由と是正を報告に残す）。

### Phase 5 — generate-formation 方式の追加（型付き動的リストとmapping受け渡し）

#### 目的

最難の2要素 — `layers` の型付き可変長フォームと、非built-in材料の
`optical-mapping.json` 受け渡し — を、枯れたフレームワークの上で扱う。

#### スコープ

- 第1段: トップレベル（seed、shape、voxel_size、palette）はフォーム、
  `layers` はJSONテキスト編集 + Validate のハイブリッドで登録する。
  既存の `examples/formation_generation/*.formation.json` を
  テンプレートとしてloadできるようにする。
- 第2段: 層タイプ選択 → タイプ別フォームを動的生成する層エディタ
  （追加/削除/並べ替え）。着手可否は第1段の運用結果で判断し、
  独立planとする。
- 非built-in材料時に出力される `optical-mapping.json` を実行パイプラインの
  `run` 段へ自動で受け渡し、palette名整合エラーを発行前に検出する。
- `formation-stats` の要約を実行結果表示へ含める。

#### 非ゴール

- `sweep-formation` のGUI化。
- constraints・mappingスキーマの拡張。
- 新しい層タイプの追加。

#### 完了条件

- marble-like相当のformationをGUI経由で発行し、viewerでmapping込みで
  確認できる。
- 保存configのCLI再実行でdigest一致（ハイブリッド編集を含む）。
- palette名とmappingの不整合が発行前の明示的エラーになる。

### Phase 6（オプション） — 運用性と連携の強化

Phase 1〜5の運用で必要性が確認されたものだけを個別に計画する。候補:

- 出力bundleの世代管理・命名規則・cleanup規則の整備
- designlab → viewer の軽量連携（発行完了の通知、ワンクリックで開く等）
- `sweep-formation` / パラメータスイープのGUI化
- primitive arrayの拡張（配置ジッタ、サイズ勾配、複数包含材）
- 代表configのsession replay型自動回帰

このフェーズは一括実装しない。

## フェーズ間の依存関係

```text
Phase 1: primitive array（CLI・契約テスト）
    ↓
Phase 2: designlab GUI最小成立（1方式・レジストリ骨格・再現契約）
    ↓
Phase 3: voxelize-mesh（入力ファイルカタログ）
    ↓
Phase 4: image-stack / morph-stack（可変長テーブル・拡張容易性の実証）
    ↓
Phase 5: generate-formation（動的リスト・mapping受け渡し）
    ↓
Phase 6: 必要になった強化だけを選択実装
```

各段で新しいUI概念を1つずつしか増やさない。順序を入れ替える場合は、
その段で増える概念が1つに保たれることを実装planで示す。

## 全フェーズ共通の非ゴール

- designlab内でのMitsubaレンダリング・リアルタイムプレビュー
  （目視確認は既存viewerの責務のまま）。
- GUI専用のconfig形式・GUIだけに存在する永続設定。
- `src/vdbmat` core / `vdbmat-utils` coreへのviser依存の追加。
- ブラウザからのファイルupload。
- 既存bundle・config・入力アセットの破壊的上書き（発行は常に新規パスへ）。
- `.local` の成果物やローカル絶対パスのgit管理成果物への混入。
- リモート公開、認証、複数ユーザーの編集競合。

## 検証方針

各フェーズの個別planで詳細化するが、共通して次を守る。

- ジェネレータ本体はvdbmat-utils既存規約の契約テスト
  （digest固定、double-run byte equality、seed/パラメータ感度、ASCII preview）。
- レジストリ、config round-trip、カタログ、containment、コマンド組み立ては
  viser・Mitsubaなしのunit testを優先する。
- 実行パイプラインはfixture級の小入力でのintegration test
  （生成 → import → run → 発行、失敗時の非発行）。
- GUI=CLI再現契約は方式追加ごとにテストへ固定する。
- 動作確認の入出力は `.local/designlab/pN/` に置き、git管理しない。

## 主要リスクと方針

### フォーム自動生成に早期に踏み込みすぎる

configスキーマ → フォームの完全自動生成は魅力的だが、方式が2〜3件の間は
過剰抽象になりやすい。Phase 4完了までは方式ごとの手書きフォーム定義を許し、
共通化はテーブル・カタログ等の部品単位に留める。自動化はPhase 5以降に
実測差分を根拠として判断する。

### サブプロセス実行の失敗がGUIで不透明になる

CLIのstderr/exit codeを段階名つきでstatusへ透過する。designlab側で
エラーメッセージを再解釈・再定義しない。CLIのエラーが不親切なら
CLI側を直す（破壊的変更方針の範囲内で）。

### 生成が重くGUIが固まって見える

実行はbackground job 1本に直列化し、STAGE進行を表示する。連続クリックは
実行中ジョブがある間は拒否する。cancelはviewer同様、実測してから判断する。

### 出力rootにゴミが蓄積する

一時work directoryで組み立ててからatomicに発行し、失敗時は出力rootへ
何も置かない。発行済みbundleのcleanupはPhase 6の世代管理で扱い、
それまでは手動削除可能な命名規則（方式名 + config digest等）を守る。

### viewer側の契約変更と衝突する

designlabはviewerの公開契約（canonical bundleの構造、Inputカタログの
検出規則）だけに依存し、viewer内部moduleをimportしない。契約を変える
必要が出たら、破壊的変更方針に従い両側を同一フェーズで更新する。

## ロードマップ全体の完了条件

- viewerの入力となるbundleを、CLIのconfig手書きなしにGUIの穴埋めだけで
  作成できる。
- 5方式（primitive array、voxelize-mesh、convert-image-stack、morph-stack、
  generate-formation）がレジストリに登録され、同じsave/load・実行・発行・
  再現契約に従う。
- GUIが保存したconfigはCLIで同一digestに再現でき、GUIだけに存在する
  永続状態がない。
- 実行失敗が出力rootを汚さず、失敗段階をユーザーが特定できる。
- 方式追加の標準手順が文書化され、追加コストが「レジストリ登録 + フォーム定義 +
  テスト」に収束している。
- 期間中の既存機能変更は互換アーティファクトなしで一本化されている。
