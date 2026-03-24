---
name: doc-generator
description: planner、gatherer、writerを統合するドキュメント生成オーケストレーター。
---

# Doc-Generator Skill

planner → gatherer → writer の流れを管理し、ドキュメントを生成する。

## 入力

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| ユーザー指示 | ドキュメント生成の要求 | 必須 |
| --target-path | 対象コードベースのパス | カレントディレクトリ |
| --template | テンプレートファイルのパス | なし |
| --output | 出力ファイル名 | document.md |

## 出力

| ファイル | 説明 |
|----------|------|
| `workspace/doc-plan.md` | ドキュメント計画（planner出力） |
| `workspace/gatherer-results/{item-id}/` | 各セクションの収集結果 |
| `workspace/{output}` | 最終ドキュメント（writer出力） |

---

## 実行手順

以下の手順を**順番に実行**してください。

### Step 1: パラメータ確認

入力パラメータを確認：
- ユーザー指示: 必須
- 対象パス: デフォルトはカレントディレクトリ
- テンプレート: オプション
- 出力ファイル名: デフォルトは `document.md`

### Step 2: ワークスペース準備

```bash
mkdir -p workspace/gatherer-results
```

### Step 3: Planner実行

`/planner` スキルを実行：

```
/planner "{ユーザー指示}" --template {テンプレート}
```

（--templateが指定されていない場合は省略）

**結果確認**:
- `workspace/doc-plan.md` が生成されていることを確認
- 質問が返された場合は、ユーザーに質問を伝えて**終了**

### Step 4: 計画の読み込み

`workspace/doc-plan.md` を読み込み、以下を抽出：
- メタ情報（対象読者、記述レベル、対象範囲、目的、対象パス）
- セクション一覧（id, title, domain, abstractionLevel, examples）

### Step 5: 各セクションのGatherer実行

セクションごとに `/gatherer` を実行：

```
/gatherer "{domain}" --path {target-path} --level "{abstractionLevel}"
```

実行後、結果をセクション別ディレクトリに移動：

```bash
mv workspace/search-result.json workspace/gatherer-results/{item-id}/
mv workspace/extraction-result.json workspace/gatherer-results/{item-id}/
mv workspace/validation-result.json workspace/gatherer-results/{item-id}/
```

**注意**: 各セクションを順番に処理し、前のセクションの結果を移動してから次を処理する。

### Step 6: Writer実行

`/writer` スキルを実行：

```
/writer --output {output}
```

Writerは以下を読み込んで文書を生成：
- `workspace/doc-plan.md`（計画・メタ情報）
- `workspace/gatherer-results/*/extraction-result.json`（収集結果）

### Step 7: 完了報告

最終結果をサマリー：

```
ドキュメント生成完了:
- 計画: workspace/doc-plan.md
- セクション数: N
- 各セクションの完全性:
  - sec-1: XX%
  - sec-2: XX%
  ...
- 出力: workspace/{output}
```

---

## エラーハンドリング

| 状況 | 対応 |
|------|------|
| Plannerが質問を返した | ユーザーに質問を伝えて終了 |
| Gathererが失敗 | エラーを報告し、該当セクションをスキップ |
| Writerが失敗 | エラーを報告して終了 |

---

## 使用例

```bash
# 基本的な使用
/doc-generator "認証機能のアーキテクチャドキュメントを新規参画者向けに書いて" --target-path /path/to/project

# テンプレート使用
/doc-generator "このプロジェクトのドキュメント" --template my-template.md --target-path /path/to/project

# 出力ファイル名指定
/doc-generator "API仕様書を開発者向けに書いて" --target-path /path/to/project --output api-spec.md
```
