---
name: search
description: ドメイン指定に基づいて関連ソースファイルを発見する検索スキル。Use when searching for source files related to a domain.
---

# Search Skill

ドメイン指定に基づいて関連ファイルを発見する（目標: Recall 80%+）。

## 入力

| パラメータ | 説明 | 例 |
|-----------|------|-----|
| ドメイン | 検索対象の機能領域 | `認証`, `HTTP処理`, `配信優先度` |
| 対象パス | コードベースのルートパス | `/path/to/nginx` |

## 出力

`workspace/search-result.json`

---

## 実行手順

以下の手順を**順番に実行**してください。

### Step 1: インデックス確認

`workspace/structure-index.json` と `workspace/vector-index.sqlite` が存在するか確認。

**存在しない場合のみ**、以下を実行：

```bash
# 構造インデックス作成
skills/search/bin/structure-index -P <対象パス> -o workspace/structure-index.json

# ベクトルインデックス作成（Embedding APIが利用可能な場合）
skills/search/bin/vector-index -P <対象パス> -o workspace/vector-index.sqlite
```

### Step 2: キーワード展開

ドメインから検索キーワードを展開する。以下の観点で考える：

| 観点 | 例（認証ドメイン） |
|------|-------------------|
| 類義語 | auth, login, credential, verify, password |
| 依存技術 | crypt, md5, sha1, hash |
| エラー処理 | 401, 403, forbidden |
| 前後フロー | session, logout |

**キーワードパターンを作成**（正規表現のOR結合）：
```
auth|login|credential|verify|password
```

### Step 3: キーワード検索

以下のコマンドを実行：

```bash
skills/search/bin/keyword-search \
  -p "<Step 2で作成したパターン>" \
  -P <対象パス> \
  -t c \
  -d "<ドメイン>" \
  -o workspace/keyword-result.json
```

### Step 4: ベクトル検索（オプション）

ベクトルインデックスが存在し、Embedding APIが利用可能な場合のみ実行。

Step 2の「依存技術」を概念的フレーズに変換してクエリを作成：
```
例: crypt, md5, sha1 → "cryptographic hash digest computation"
```

以下のコマンドを実行：

```bash
skills/search/bin/vector-search \
  -q "<概念的フレーズ>" \
  -i workspace/vector-index.sqlite \
  -d "<ドメイン>" \
  -t 0.55 \
  -o workspace/vector-result.json
```

### Step 5: 構造検索（オプション）

構造インデックスが存在する場合のみ実行。

```bash
skills/search/bin/structure-search \
  --index workspace/structure-index.json \
  --input workspace/keyword-result.json \
  -o workspace/structure-result.json
```

### Step 6: 結果マージ

実行した検索結果をマージ：

```bash
# キーワード結果のみの場合
skills/search/bin/merge-results \
  --base workspace/keyword-result.json \
  -d "<ドメイン>" \
  -o workspace/search-result.json

# ベクトル結果もある場合
skills/search/bin/merge-results \
  --base workspace/keyword-result.json \
  --input workspace/vector-result.json:0.85 \
  -d "<ドメイン>" \
  -o workspace/search-result.json

# 構造検索結果もある場合
skills/search/bin/merge-results \
  --base workspace/keyword-result.json \
  --input workspace/vector-result.json:0.85 \
  --input workspace/structure-result.json:0.8 \
  -d "<ドメイン>" \
  -o workspace/search-result.json
```

### Step 7: 完了確認

`workspace/search-result.json` が生成されていることを確認。

---

## コマンドリファレンス

### skills/search/bin/keyword-search

| オプション | 説明 |
|-----------|------|
| `-p, --pattern` | 検索パターン（正規表現） |
| `-P, --path` | 検索対象パス |
| `-t, --type` | ファイル種別フィルタ（c, h） |
| `-i, --ignore-case` | 大文字小文字を無視 |
| `-d, --domain` | ドメイン名 |
| `-o, --output` | 出力ファイル |

### skills/search/bin/vector-search

| オプション | 説明 |
|-----------|------|
| `-q, --query` | 検索クエリ |
| `-i, --index` | ベクトルインデックスファイル |
| `-d, --domain` | ドメイン名 |
| `-t, --threshold` | 類似度閾値（0.55-0.65推奨） |
| `-l, --limit` | 最大結果数（デフォルト: 20） |
| `-o, --output` | 出力ファイル |

### skills/search/bin/structure-search

| オプション | 説明 |
|-----------|------|
| `--index` | 構造インデックスファイル |
| `--input` | 検索結果ファイル（リファレンス元） |
| `-t, --threshold` | 類似度閾値（デフォルト: 0.5） |
| `-d, --domain` | ドメイン名 |
| `-o, --output` | 出力ファイル |

### skills/search/bin/merge-results

| オプション | 説明 |
|-----------|------|
| `--base` | ベース結果ファイル |
| `--input` | マージするファイル（`path:likelihood` 形式） |
| `-d, --domain` | ドメイン名 |
| `-o, --output` | 出力ファイル |

### skills/search/bin/structure-index

| オプション | 説明 |
|-----------|------|
| `-P, --path` | インデックス対象パス |
| `-o, --output` | 出力ファイル |
| `-u, --update` | 差分更新 |

### skills/search/bin/vector-index

| オプション | 説明 |
|-----------|------|
| `-P, --path` | インデックス対象パス |
| `-o, --output` | 出力SQLiteファイル |
| `-u, --update` | 差分更新 |
| `--api-url` | Embedding API URL |
| `--model` | モデル名 |
