---
name: gatherer
description: search、extract、validateを組み合わせた情報収集オーケストレーションスキル。Use when gathering comprehensive information about a domain.
---

# Gatherer Skill

search → extract → validate の反復処理で情報を網羅的に収集する。

## 入力

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| ドメイン | 検索対象の機能領域 | 必須 |
| --path | コードベースのパス | 必須 |
| --recall | 目標完全性 (50-100) | 90 |
| --level | 抽出の抽象レベル | なし |
| --max-cycles | 最大サイクル数 (1-5) | 3 |

## 出力

| ファイル | 説明 |
|----------|------|
| `workspace/search-result.json` | 検索結果（累積） |
| `workspace/extraction-result.json` | 抽出結果 |
| `workspace/validation-result.json` | 検証結果 |

---

## 実行手順

以下の手順を**順番に実行**してください。

### Step 1: パラメータ確認

入力パラメータを確認：
- ドメイン: 必須
- 対象パス: 必須
- 目標完全性: デフォルト 90
- 最大サイクル: デフォルト 3

### Step 2: Cycle 1 - 検索

`/search` スキルを実行：

```
/search <ドメイン> --path <対象パス>
```

結果: `workspace/search-result.json` が生成される

### Step 3: Cycle 1 - 抽出

`/extract` スキルを実行：

```
/extract --level "<抽象レベル>"
```

（--level が指定されていない場合は省略可）

結果: `workspace/extraction-result.json` が生成される

### Step 4: Cycle 1 - 検証

`/validate` スキルを実行：

```
/validate
```

結果: `workspace/validation-result.json` が生成される

### Step 5: 完全性チェック

`workspace/validation-result.json` を読み込み、`completeness` を確認：

| 条件 | アクション |
|------|-----------|
| `completeness >= 目標完全性` | **Step 8 へ進む（完了）** |
| `completeness < 目標完全性` かつ `現在サイクル < 最大サイクル` | **Step 6 へ進む** |
| `completeness < 目標完全性` かつ `現在サイクル >= 最大サイクル` | **Step 8 へ進む（上限到達）** |

### Step 6: 追加検索準備

`validation-result.json` から `additional_search.keywords` を取得。

### Step 7: 追加サイクル

Step 2〜5 を繰り返す。ただし：

- `/search` では追加キーワードを使用
- サイクル番号をインクリメント

**注意**: 最大サイクル数に達したら Step 8 へ

### Step 8: 完了報告

最終結果をサマリー：

```
完了サマリー:
- 実行サイクル数: N
- 最終完全性: XX%
- 検出ファイル数: XX
- 出力ファイル:
  - workspace/search-result.json
  - workspace/extraction-result.json
  - workspace/validation-result.json
```
