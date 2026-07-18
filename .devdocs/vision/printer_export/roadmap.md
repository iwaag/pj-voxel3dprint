# printer_export ロードマップ — 3Dプリンタ向けスライスデータ出力ルート

## 背景

本ツールチェーンのボクセルデータ出力先は、現在レンダラ（Mitsuba / OpenVDB /
Blender Cycles）のみである。一方、本システムの主目的は material-jetting 3Dプリント
であり、ボクセルモデルを実機プリントへ渡すルート — GrabCAD Print の voxel printing
が受け取るスライス画像スタックの生成 — が欠けている。

**printer_export** は、material-label ボクセル（`.voxels.json` +
`.material_id.npy`）からプリンタ固有格子のスライスPNG群を生成する新しい
出力ルートである。

設計上の要点は次の2つ。

1. **入力は material-label ボクセルであり、optical volume ではない。**
   プリンタに渡すのは「各ボクセルがどの材料か」であって光学特性ではないため、
   `vdbmat run`（optical mapping）を通す必要がない。したがってこのエクスポータは
   `vdbmat` の renderer exporters（mitsuba / openvdb）とは別系統であり、
   **`vdbmat-utils` に置く**。
2. **既存の `convert-image-stack`（画像→ボクセル）の逆変換である。**
   `image/` モジュール（PNG書き出し）を再利用でき、往復テスト
   （export → convert-image-stack → 元配列と一致）が既存コマンドだけで組める。

```text
既存:  slices/ → convert-image-stack → .voxels.json      （入力ルート）
新設:  .voxels.json → export-print-slices → slices/ PNG   （出力ルート）
```

## ターゲット仕様（GrabCAD Print voxel printing）

Stratasys公式ガイド
（<https://support.stratasys.com/en/Software/GrabCAD-Print/Tips-Guides-and-FAQs/Guide-to-Voxel-Printing>）
より、実装を規定する制約は次のとおり。

- **PNGメソッドのみ推奨**（BMP + txtマニフェストはレガシー）。
  1レイヤー = 1 PNG、連番 + 共通プレフィックス命名（例: `slice_0000.png`）。
- **異方性解像度**: X = 600 dpi（25.4/600 ≈ 42.33 µm）、
  Y = 300 dpi（25.4/300 ≈ 84.67 µm）。
- **レイヤー厚**: High Quality = 14 µm、High Speed / High Mix = 27 µm。
  プリンタ側設定と一致させる必要がある。
- **色数制限**: 背景を除き1画像あたり最大6色（High Speedは3色）。
  中間色が1ピクセルでも混じると "Too many colors" エラーになる。
- 色→材料の対応付けはGrabCAD GUI側で行う（PNG側に機械可読マニフェストは無い）。
- 最低30スライス。

この制約群から導かれる実装原則:

- **材料IDは絶対に補間・平均しない**（morph-stackのSDF原則と同じ）。
  リサンプリングは最近傍のみ。
- **インデックスパレットPNG**で書き出し、アンチエイリアス由来の中間色を
  構造的に排除する。
- プリンタピッチは非整数（25.4/600 mm）なので、整数比リサンプルではなく
  **物理空間での最近傍サンプリング**（出力ピクセル中心の物理座標 →
  最近傍ソースボクセル）で出力格子を導出する。

## 破壊的変更の方針

designlab visionと同じ方針を適用する。後方互換のためだけのアーティファクト
（旧スキーマ読み込み、deprecatedエイリアス、互換shim）を残さない。壊す変更は
実装planに明記し、何が読めなくなるか・どう再生成するかを1行で書けることを
条件とする。`.local` 配下のローカル成果物は再生成可能とみなす。

## 用語と境界

### プリンタプロファイル（printer profile）

出力格子を定義する数値の組: `dpi_x`、`dpi_y`、`layer_thickness_m`。
Phase 1ではconfig内の生数値とし、名前付きプリセット化は必要が確認されてから
（Phase 4）扱う。

### パレット（palette）

material ID → RGB色の対応。背景（`role: "background"` の材料）は
`background_rgb` として別扱いする。色の選択は「GrabCAD GUIで人間が区別して
材料へ対応付けるためのラベル」であり、色自体に物理的意味はない。

### サイドカーマニフェスト（`<name>.printslices.json`）

GrabCADは読まないが、本リポジトリのprovenance規約に沿って出力する:
ソース `.voxels.json` のdigest、プリンタプロファイル、パレット、スライス数、
物理寸法（mm）、各PNGのsha256。GrabCAD GUIでの色→材料対応付けの手順書を兼ねる。

### パッケージ境界

- エクスポータ本体・契約テストは `vdbmat-utils` に置く。
- `vdbmat` core / renderer exportersへは変更を加えない。
- 入力は canonical な `.voxels.json` 契約のみに依存し、Zarr / optical bundleを
  読まない。

## 全体ゴール

ローカル開発者が次を行えるようにする。

1. 任意のジェネレータ（voxelize-mesh、formation、primitive array等）で作った
   material-labelボクセルから、1コマンドでGrabCAD Print voxel printing用の
   スライスPNG群を生成する。
2. プリンタプロファイル（dpi、レイヤー厚）とパレットをconfigで指定し、
   同一config・同一入力から常にbyte-identicalな出力を得る。
3. 色数超過・スライス数不足等のプリンタ制約違反を、出力前の明示的エラーとして
   検出する。
4. サイドカーマニフェストから、出力の物理寸法とGUIでの材料対応付け手順を
   確認できる。
5. 生成したスライスをGrabCAD Voxel Print Utilityに読み込ませ、GCVF生成が
   通ることを実機ソフトで確認する。

## 設計原則

### 1. 変換は純粋関数、出力はatomicに

サンプリング・パレット適用は入力配列とconfigのみに依存する決定論的変換とする。
出力は一時ディレクトリで組み立て、全PNG + マニフェストの書き出しと検証が
成功してから出力先へatomicに移す。失敗時は部分成果物を残さない。

### 2. バリデーションは二重化する

色数制限は「パレット定義時点の材料数チェック」と「出力PNGの実色数の再検査」の
両方で保証する。前者はfail-fast、後者は実装バグ（補間混入等）に対する防波堤。

### 3. 軸対応はconfigで明示し、マニフェストで検算可能にする

PNGの行/列をプリンタX（600 dpi・細かい方）/ Y（300 dpi）のどちらへ対応させるかを
configで明示する。取り違えると物理寸法が2倍狂うため、マニフェストに各軸の
物理寸法（mm）とピクセル数を記録し、人間が検算できるようにする。

### 4. 往復契約を正しさの基準にする

`export-print-slices → convert-image-stack → プリンタ格子上の材料配列と一致`
の往復テストを契約テストに含める。既存コマンドだけで組める最強の検証手段であり、
これが通る限りサンプリング・エンコードの対称性が保証される。

## フェーズ構成

### Phase 1 — export-print-slices CLI本体

#### 目的

material-labelボクセル → スライスPNG群の変換を、契約テストつきCLIとして
完成させる。

#### スコープ

- `vdbmat-utils export-print-slices`（名称は実装planで確定）を追加する。
  入力は `.voxels.json`、`--config` + `--out` + `--name` の既存CLI規約に従う。
- config（フラット）:
  - `printer_profile`: `dpi_x`、`dpi_y`、`layer_thickness_m`（生数値）
  - `palette`: material ID → RGB
  - `background_rgb`
  - `slice_axis`（既定 `z`）と面内軸対応（X/Y flip・転置の明示指定）
  - `name_prefix`、開始index
- 物理空間最近傍サンプリング: 出力形状を物理バウンドとプリンタピッチから導出し、
  軸ごとの最近傍インデックス配列を事前計算して `np.take` で引く。
  補間・平均は行わない。
- インデックスパレットPNG書き出し（`image/png.py` 基盤を再利用）。
- バリデーション（すべて明示エラー）:
  - 非背景材料数 > 6（High Speedプロファイル時は 3）
  - スライス数 < 30（警告 + 背景パディングのオプションは実装planで判断）
  - パレット未定義のmaterial IDが入力に存在
  - 出力PNGごとの実色数再検査
- サイドカーマニフェスト `<name>.printslices.json` の出力。
- 契約テスト: payload digest固定、double-run byte equality、
  異方性ピッチでの形状導出、軸対応の各組み合わせ。
- docs（`vdbmat-utils/docs/`）へ方式ドキュメントを追加する。

#### 非ゴール

- ハーフトーン/ディザリング（連続材料混合の表現）。
- BMPレガシーメソッド。
- 名前付きプリンタプリセット。
- GUI。

#### 完了条件

- 既存フィクスチャ（`nested_material_cube` 級、primitive array）から
  スライスPNG群 + マニフェストが生成される。
- 同一入力・同一configの2回実行がbyte-identical。
- 色数超過・パレット欠落・スライス不足が明示エラーになる。
- 契約テストが既存ジェネレータと同水準で揃っている。

### Phase 2 — 往復契約テストとドキュメント統合

#### 目的

出力の正しさを既存入力ルートとの往復で固定し、ユースケースとして公開する。

#### スコープ

- 往復契約テスト: `export-print-slices` の出力を `convert-image-stack` へ
  読み戻し、プリンタ格子上の材料配列と完全一致することをテストで固定する
  （levels configはパレットから機械的に導出する）。
- 異方性が効くケース（等方100µmソース → 42.33×84.67×27µm格子）を含む
  リサンプリング感度テスト。
- README_QUICK.md へ新Use Case（「プリンタ向けスライス出力」）を追加する。
- `preview-slices` での目視確認手順を方式ドキュメントに記載する。

#### 非ゴール

- 新機能の追加。往復で発見された欠陥の修正はPhase 1へのfixとして扱う。

#### 完了条件

- 往復テストがCIで通る。
- README_QUICKのUse Caseどおりに、STLまたはprimitive arrayから
  スライスPNG群まで手動CLIで通る。

### Phase 3 — 実機ソフト検証（GrabCAD Voxel Print Utility）

#### 目的

生成物が実際にGrabCAD Print voxel printingパイプラインへ受理されることを、
本リポジトリの外にあるソフトで確認する。ここだけは自動化できず、
仕様書の解釈違い（命名、色検出、背景の扱い等）が露見しうる唯一の段。

#### スコープ

- primitive array の小フィクスチャ（数を数えられる形状）で実データを生成し、
  GrabCAD Voxel Print UtilityでGCVF生成が通るかを確認する。
- 発見された仕様解釈の齟齬（背景色の扱い、命名規則の細部、色検出の挙動等）を
  Phase 1実装へ反映し、方式ドキュメントに「実機確認済みの解釈」として記録する。
- 検証に使った入出力は `.local/printer_export/` に置き、git管理しない。
  結果は報告書の記述のみとする。

#### 非ゴール

- 実プリント（物理造形）の実施。GCVF生成の受理までを本フェーズの範囲とする。
  実プリントの結果評価は将来の較正visionで扱う。

#### 完了条件

- GCVF生成が通ること、または通らない原因が特定され修正されたことが
  報告に記録されている。
- 実機確認で判明した仕様解釈がドキュメントへ反映されている。

### Phase 4（オプション） — 運用性の強化

Phase 1〜3の運用で必要性が確認されたものだけを個別に計画する。候補:

- 名前付きプリンタプリセット（J750等、機種別のdpi/レイヤー厚/色数上限の組）
- High Speedモード（3色制限）のプロファイル切り替え
- 30スライス未満入力の自動背景パディング
- designlabへの統合（publish先の一つとしてスライス出力を追加）
- BMPレガシーメソッドのライター追加（同じ中間表現から分岐）
- 連続材料混合のためのディザリング前段ステージ
  （optical/濃度データ → 誤差拡散 → 離散ラベル。境界付近のディザ禁止制約を
  含む独立した設計が必要なため、着手する場合は独立visionとする）

このフェーズは一括実装しない。

## フェーズ間の依存関係

```text
Phase 1: export-print-slices CLI（契約テスト）
    ↓
Phase 2: 往復契約テスト・ドキュメント統合
    ↓
Phase 3: 実機ソフト検証（GrabCAD Voxel Print Utility）
    ↓
Phase 4: 必要になった強化だけを選択実装
```

## 全フェーズ共通の非ゴール

- optical volume（optical.zarr）を入力に取ること。スライス出力は
  material-labelボクセルのみを消費する。
- `vdbmat` core / renderer exportersへの変更。
- GUI・リアルタイムプレビュー（目視確認は `preview-slices` と既存viewerの責務）。
- 実プリントの物理的品質評価・材料較正。
- `.local` の成果物やローカル絶対パスのgit管理成果物への混入。

## 検証方針

- エクスポータ本体はvdbmat-utils既存規約の契約テスト
  （digest固定、double-run byte equality、パラメータ感度、境界ケース）。
- サンプリング・パレット適用・バリデーションはPNG書き出しなしの
  unit testを優先する。
- 往復契約（Phase 2）を正しさの中心的検証とする。
- 実機ソフト受理（Phase 3）は手動検証とし、結果を報告書に記録する。
- 動作確認の入出力は `.local/printer_export/pN/` に置き、git管理しない。

## 主要リスクと方針

### 仕様書の解釈違いが実機まで発覚しない

GrabCADのPNGメソッドは機械可読な仕様（スキーマ）を持たず、公式ガイドの記述が
唯一の根拠である。背景の色、命名の細部、色検出の挙動は実機ソフトでしか
確定できない。Phase 3を独立フェーズとして早期に置き、判明した解釈を
ドキュメントへ「実機確認済み」として固定する。

### 軸対応の取り違え

X=600dpi / Y=300dpiの取り違えは、出力が生成でき目視でもそれらしく見えるのに
物理寸法が2倍狂う、発見しづらい欠陥になる。configでの明示指定 +
マニフェストへの物理寸法記録 + Phase 3での実寸確認の三重で防ぐ。

### 中間色の混入による "Too many colors"

最近傍サンプリング + インデックスパレットPNGで構造的に排除するが、
将来の変更（リサイズ処理の追加等）で崩れうる。出力PNGの実色数再検査を
契約テストに含め、回帰を機械的に検出する。

### 巨大出力によるメモリ・ディスク圧迫

600dpiのプリンタ格子は、実寸の大きいモデルでスライスあたり数千×数千ピクセル、
数千スライスになりうる。Phase 1ではスライス単位のストリーミング書き出しと
既存のサイズガード相当（出力総ピクセル数の上限 + 明示エラー）を入れ、
上限緩和は必要が確認されてから扱う。

## ロードマップ全体の完了条件

- material-labelボクセルから1コマンドでGrabCAD Print voxel printing用
  スライスPNG群 + サイドカーマニフェストを生成できる。
- 同一入力・同一configからbyte-identicalな出力が再現できる。
- 往復契約テスト（export → convert-image-stack → 一致）がCIで固定されている。
- プリンタ制約違反（色数、スライス数、パレット欠落）が出力前の
  明示エラーになる。
- GrabCAD Voxel Print UtilityでのGCVF生成受理が実機ソフトで確認され、
  判明した仕様解釈がドキュメントに記録されている。
