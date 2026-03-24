---
name: validate
description: 抽出結果の完全性と正確性を検証し、追加検索が必要かを判断するスキル。Use when validating extraction results or checking if gathered information is complete.
---

# Validate Skill

抽出結果を検証し、追加検索が必要かを判断する。

## 前提条件

`workspace/extraction-result.json` が存在すること（/extract 実行後）

## 出力

`workspace/validation-result.json`

---

## 実行手順

以下の手順を**順番に実行**してください。

### Step 1: 抽出結果の読み込み

`workspace/extraction-result.json` を読み込む。

存在しない場合はエラー終了。

### Step 2: 検証観点の確認

以下の観点で抽出結果をチェック：

| 観点 | チェック内容 |
|------|-------------|
| ファイル妥当性 | キーワード・パスがドメインと関連しているか |
| 完全性 | 主要機能、エントリーポイント、依存関係がカバーされているか |
| 正確性 | source.text と summary が整合しているか |
| 関連性 | 無関係ファイル・内容が混入していないか |
| 抽象レベル適合 | 指定されたビジネス/技術視点と合っているか |
| 呼び出し元網羅性 | `_init`, `_handler` 関数の呼び出し元が含まれているか |
| 関連モジュール網羅性 | 同一ディレクトリ・同一プレフィックスのファイルが含まれているか |

### Step 3: スコア計算

完全性スコアを計算：

```
completeness = カバーされている要素数 / 必要な要素数 × 100
```

### Step 4: 判定

| スコア | 判定 | アクション |
|--------|------|-----------|
| 80% 以上 | OK | 検証完了 |
| 80% 未満 | NG | 追加検索キーワードを生成 |

### Step 5: 結果出力

検証結果を以下の形式で `workspace/validation-result.json` に保存：

```json
{
  "status": "OK または NG",
  "completeness": 85,
  "issues": [
    "検出された問題点1",
    "検出された問題点2"
  ],
  "additional_search": {
    "keywords": ["追加キーワード1", "追加キーワード2"],
    "reason": "追加検索が必要な理由"
  }
}
```

**注意**：
- `status` が `OK` の場合、`additional_search` は空でよい
- `status` が `NG` の場合、`additional_search.keywords` を必ず含める

### Step 6: 完了確認

`workspace/validation-result.json` が生成されていることを確認。
