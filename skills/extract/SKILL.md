---
name: extract
description: ソースファイルから抽象レベルに応じた情報を抽出するスキル。Use when extracting structured information from source files after search.
---

# Extract Skill

検索結果のファイルから、指定された抽象レベルで情報を抽出する。

## 入力

| パラメータ | 説明 | 例 |
|-----------|------|-----|
| 抽象レベル | 抽出の視点 | `ビジネスフロー`, `技術実装` |

## 前提条件

`workspace/search-result.json` が存在すること（/search 実行後）

## 出力

`workspace/extraction-result.json`

---

## 実行手順

以下の手順を**順番に実行**してください。

### Step 1: 検索結果の確認

`workspace/search-result.json` が存在することを確認。

存在しない場合はエラー終了。

### Step 2: ファイル読み込み

以下のコマンドを実行：

```bash
skills/extract/bin/file-reader \
  -i workspace/search-result.json \
  -o workspace/extraction-input.json \
  --max-files 20 \
  --chunk-size 100
```

### Step 3: 抽出入力の確認

`workspace/extraction-input.json` を読み込み、内容を確認。

ファイル構造：
```json
{
  "domain": "ドメイン名",
  "files": [
    {
      "path": "ファイルパス",
      "chunks": [
        {"id": 1, "content": "コード内容..."}
      ]
    }
  ]
}
```

### Step 4: 情報抽出

`extraction-input.json` の各チャンクから、指定された抽象レベルで情報を抽出。

**抽象レベル別の抽出観点**：

| レベル | 観点 | 出力例 |
|--------|------|--------|
| ビジネスフロー | ユーザー視点で機能説明 | 「ユーザーがログインすると認証サービスがパスワードを検証」 |
| 技術実装 | 技術的な実装詳細 | 「auth_init() は ngx_auth_t 構造体を初期化」 |

**抽出ガイドライン**：
- summary は source.text から導出可能であること
- 指定されたレベルに沿った粒度で抽出
- ドメインに無関係な部分は抽出しない
- 同内容を複数回抽出しない

### Step 5: 結果出力

抽出結果を以下の形式で `workspace/extraction-result.json` に保存：

```json
{
  "domain": "ドメイン名",
  "abstraction_level": "指定されたレベル",
  "extractions": [
    {
      "source": {
        "path": "ファイルパス",
        "start_line": 10,
        "end_line": 25,
        "text": "対象コード"
      },
      "summary": "抽出された説明"
    }
  ]
}
```

### Step 6: 完了確認

`workspace/extraction-result.json` が生成されていることを確認。

---

## コマンドリファレンス

### skills/extract/bin/file-reader

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `-i, --input` | 入力ファイル（search-result.json） | 必須 |
| `-o, --output` | 出力ファイル | 必須 |
| `--max-files` | 処理する最大ファイル数 | 20 |
| `-d, --domain` | ドメイン指定 | search-resultから継承 |
| `--chunk-size` | チャンクあたりの行数 | 100 |
