# digital-brain — Second Brain エンジン

Zettelkasten 形式の個人知識ベース（セカンドブレイン）を運用するエンジンです。
記事・動画・メモ・調査・企画を、AI との会話を通じて構造化ノートとして蓄積します。

旧 Discord Bot から移行し、現在は **VSCode 上で 3 通りの方法**で操作できます。

## 構成（2 リポジトリ）

| リポジトリ | 役割 |
|---|---|
| **digital-brain**（本リポジトリ） | エンジン本体。常駐デーモン・CLI・VSCode 拡張機能 |
| **second-brain** | ボルト（ノートの保管庫）。Markdown ノート + テンプレート + 設定 |

2 つは同じ親フォルダに隣り合わせて配置します:

```
任意の親フォルダ/
  digital-brain/   ← エンジン（このリポジトリ）
  second-brain/    ← ボルト（ノート）
```

処理の中心は **常駐ローカルデーモン**（`daemon.py`）で、ChromaDB の埋め込みモデルを
ウォーム保持して高速に動作します。初回のコマンド実行時に自動起動します。

## セットアップ

別 PC での構築を含む手順は **[SETUP.md](SETUP.md)** を参照してください。

要約: 両リポジトリを clone → `digital-brain` で `.\setup.ps1` を実行 →
`.env` に API キーを設定。

---

## 操作方法は 3 通り

> 全機能 × 3 操作方法の早見表（自己テスト用リファレンス）は
> **[docs/commands.md](docs/commands.md)** を参照してください。

### 方法 1: Claude Code（手軽）

VSCode で `second-brain` フォルダを開き、Claude Code のスラッシュコマンドを使います。
会話は Claude Code 自身が担当し、保存・同期・検索はエンジンが担当します。

| コマンド | 機能 |
|---|---|
| `/memo <内容>` | メモを会話で深掘り → 保存で Fleeting ノート化 |
| `/link <URL>` | 記事・YouTube を取り込んで議論 → Literature ノート化 |
| `/research <トピック>` | Web 検索 + 蓄積知識で調査 → Research ノート化 |
| `/planning <テーマ>` | 企画・目標をブレスト → Planning ノート化 |
| `/chat <メッセージ>` | 自由会話（任意で保存） |
| `/search <クエリ>` | 蓄積ノートを意味検索 |
| `/task <内容>` | GitHub Issue としてタスク作成・一覧・完了 |
| `/sync` | ボルトと GitHub を同期 |
| `/permanent` | Fleeting から Permanent ノートを抽出 |

Claude Code 向けの詳細な動作指針は `second-brain/CLAUDE.md` に記載されています。

### 方法 2: VSCode 拡張機能（GUI）

「Second Brain」拡張機能をインストールすると、コマンドパレットやパネルで操作できます。

インストール:

```powershell
cd vscode-extension
npm install
npm run compile
npx @vscode/vsce package          # second-brain-x.y.z.vsix を生成
code --install-extension second-brain-0.1.0.vsix
```

VSCode を再読み込み（`Developer: Reload Window`）すると有効になります。

- コマンドパレット（`Ctrl+Shift+P`）→「Second Brain: メモ / リサーチ / 検索 …」
- 会話は横の **チャットパネル**、保存はパネルの「保存」ボタン
- タスクはサイドバーの **「Second Brain タスク」パネル**

### 方法 3: CLI（土台）

エンジンを直接コマンドで操作します。上の 2 つも内部でこの CLI を使っています。

```powershell
.venv\Scripts\python.exe cli.py <サブコマンド>
```

| サブコマンド | 機能 |
|---|---|
| `sync` / `status` | GitHub 同期 / 状態表示 |
| `search <query>` | 意味検索 |
| `index` | ChromaDB を再構築 |
| `fetch-url <url>` / `fetch-youtube <url>` | 記事 / 字幕の取得 |
| `memo｜link｜research｜planning｜chat <input>` | 会話セッションを開始 |
| `continue <id> <msg>` / `save <id>` / `permanent <id>` / `discard <id>` | セッション操作 |
| `sessions` / `session <id>` | セッション一覧 / 詳細 |
| `task add｜list｜show｜update｜done` | タスク（GitHub Issue / Projects v2） |

---

## ノートの種類と保存先（ボルト内）

- `00-inbox/` 生メモ
- `10-notes/fleeting/` フリーティングノート / `10-notes/permanent/` 恒久（Atomic）ノート
- `10-notes/literature/{articles,youtube}/` 文献ノート
- `20-research/` 調査ノート / `30-planning/` 企画ノート

ノートは `ZK-YYYYMMDD-HHMMSS.md` 形式。YAML フロントマター + Markdown 本文。

## タスク管理

タスクは **GitHub Issue が実体**、**Projects v2 ボードがビュー**です。
`/task` または `cli.py task` で作成・一覧・更新します。`--note <ZK-id>` を付けると、
Issue とノートが双方向にリンクされます（ノートの frontmatter `tasks:` に Issue 番号）。

## アーキテクチャ

```
VSCode
  ├─ Claude Code（second-brain/.claude/commands）─┐
  └─ VSCode 拡張機能（vscode-extension）──────────┤
                                                  ▼
              常駐デーモン daemon.py（localhost:8765）
                - ChromaDB + 埋め込みモデル（ウォーム保持）
                - セッション永続化 / Git 同期ガード
                - スクレイピング / YouTube 書き起こし
                - Claude API（拡張機能モードの会話）
                                                  ▼
                 second-brain ボルト（ローカル git）⇄ GitHub
```

## 主要な依存パッケージ

| パッケージ | 用途 |
|---|---|
| `anthropic` | Claude API（拡張機能モードの会話）|
| `chromadb` + `sentence-transformers` | 意味検索（多言語埋め込み）|
| `PyGitHub` | タスク管理（GitHub Issues）|
| `trafilatura` | 記事スクレイピング |
| `youtube-transcript-api` | YouTube 字幕取得（高速パス）|
| `yt-dlp` + `faster-whisper` | 字幕なし動画の書き起こし |

前提ソフトや別 PC でのセットアップ手順は [SETUP.md](SETUP.md) を参照してください。
