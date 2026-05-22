# セットアップ手順（別PCでの環境構築）

digital-brain（エンジン）と second-brain（ボルト）を、別のPCでも同じように
動かすための手順です。

## 仕組み — 何が GitHub で共有され、何がされないか

| 対象 | 共有方法 |
|---|---|
| プログラムコード（エンジン・拡張機能・テンプレート等） | **GitHub で共有**（digital-brain / second-brain リポジトリ） |
| ノート本体 | **GitHub で共有**（second-brain リポジトリ） |
| `.venv`（依存パッケージ） | 各PCで生成（容量が大きく PC 固有のため共有しない） |
| `.env`（APIキー） | 各PCで作成（**秘密情報のため GitHub には絶対に載せない**） |
| `chroma_db` / `.brain` | 各PCで自動生成（索引・セッションのローカルキャッシュ） |

→ 「別PCで同じ環境」とは **「コードとノートは GitHub から取得 + 各PCでセット
アップ手順を1回実行」** という形になります。

## 前提ソフト

- Python 3.11 以上
- Git
- （任意）Node.js — VSCode 拡張機能をビルドする場合のみ

## 手順

### 1. 2つのリポジトリをクローン（同じ親フォルダに隣同士で）

```
git clone https://github.com/chikitamfwfw/digital-brain.git
git clone https://github.com/chikitamfwfw/second-brain.git
```

推奨フォルダ構成:

```
任意の親フォルダ/
  digital-brain/   ← エンジン（このリポジトリ）
  second-brain/    ← ボルト（ノート）
```

### 2. セットアップスクリプトを実行

```
cd digital-brain
.\setup.ps1
```

venv 作成・依存インストール・`.env` 生成を自動で行います（数分かかります）。

### 3. .env を編集

`digital-brain/.env` を開き、以下を設定します。

| 項目 | 内容 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic の API キー |
| `GITHUB_TOKEN` | GitHub トークン（`repo` + `project` スコープ） |
| `GITHUB_REPO` | `chikitamfwfw/second-brain` |
| `VAULT_PATH` | 通常は設定不要。digital-brain と second-brain が隣同士なら自動検出 |

### 4. 動作確認

```
.\.venv\Scripts\python.exe cli.py status
```

`root` に second-brain のパス、`branch` などが表示されれば成功です。

### 5. （任意）VSCode 拡張機能のビルド

```
cd vscode-extension
npm install
npm run compile
```

VSCode で `vscode-extension` フォルダを開き、F5 でデバッグ起動できます。

## 使い方

- **CLI**: `.\.venv\Scripts\python.exe cli.py <コマンド>`
  （`sync` / `memo` / `research` / `search` / `task` など）
- **Claude Code**: `second-brain` フォルダを開き、`.claude/commands` の
  スラッシュコマンド（`/memo` `/research` `/task` など）を使用

操作の詳細は second-brain 側の `CLAUDE.md` を参照してください。
