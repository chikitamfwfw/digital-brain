# コマンド・機能一覧（自己テスト用）

このシステムは **3つの操作方法**があり、どれも同じエンジンが動きます。
各機能を、3つの方法それぞれでどう実行するかをまとめます。

## 操作方法の起動

| 方法 | 起動手順 |
|---|---|
| **Claude Code** | VSCode で `second-brain` フォルダを開く → Claude Code パネルで `/コマンド` |
| **VSCode 拡張機能** | `Ctrl+Shift+P` →「Second Brain: …」（初回のみ「Developer: Reload Window」）|
| **CLI** | `digital-brain` フォルダで `.\.venv\Scripts\python.exe cli.py …` |

> 以下、CLI 欄の `cli.py` は `.\.venv\Scripts\python.exe cli.py` の略記です。

---

## 機能一覧

### 1. memo — メモを会話で深掘りして保存
短いメモを起点に AI と会話し、保存で Fleeting ノートに整理する。実行時に生メモが `00-inbox/` にも残る。

| 方法 | 実行 |
|---|---|
| Claude Code | `/memo <内容>` |
| 拡張機能 | 「Second Brain: メモ」→ 入力 → チャットパネルで会話 →「保存」 |
| CLI | `cli.py memo "<内容>"` → `cli.py continue <session_id> "<追加>"` → `cli.py save <session_id>` |

**期待結果**: `10-notes/fleeting/ZK-….md` が作成され、GitHub に push される。

### 2. link — 記事・YouTube を取り込んで保存
URL（記事 or YouTube）を取り込み、本文/字幕を AI と議論し、Literature ノートに整理する。

| 方法 | 実行 |
|---|---|
| Claude Code | `/link <URL>` |
| 拡張機能 | 「Second Brain: リンク取り込み」→ URL 入力 |
| CLI | `cli.py link "<URL>"` → `cli.py save <session_id>` |

**期待結果**: `10-notes/literature/articles/` または `youtube/` にノート作成。

### 3. research — Web 検索つき調査
トピックを Web 検索＋蓄積知識で調査し、Research ノートにまとめる。

| 方法 | 実行 |
|---|---|
| Claude Code | `/research <トピック>` |
| 拡張機能 | 「Second Brain: リサーチ」 |
| CLI | `cli.py research "<トピック>"` → `cli.py save <session_id>` |

**期待結果**: `20-research/ZK-….md` が作成される。

### 4. planning — 企画・目標のブレスト
アイデアや目標について AI とブレストし、Planning ノートにまとめる。

| 方法 | 実行 |
|---|---|
| Claude Code | `/planning <テーマ>` |
| 拡張機能 | 「Second Brain: プランニング」 |
| CLI | `cli.py planning "<テーマ>"` → `cli.py save <session_id>` |

**期待結果**: `30-planning/ZK-….md` が作成される。

### 5. chat — 自由会話
Web 検索＋過去ノート参照つきの自由会話。任意で保存できる。

| 方法 | 実行 |
|---|---|
| Claude Code | `/chat <メッセージ>` |
| 拡張機能 | 「Second Brain: チャット」 |
| CLI | `cli.py chat "<メッセージ>"` →（任意で）`cli.py save <session_id>` |

### 6. search — 意味検索
蓄積した全ノートを、意味的な近さで検索する。

| 方法 | 実行 |
|---|---|
| Claude Code | `/search <クエリ>` |
| 拡張機能 | 「Second Brain: 検索」→ 結果を選ぶとノートが開く |
| CLI | `cli.py search "<クエリ>"` |

### 7. permanent — Permanent ノート抽出
保存済み Fleeting ノートから、独立した Atomic な Permanent ノートを抽出する。

| 方法 | 実行 |
|---|---|
| Claude Code | `/permanent`（直前に保存した内容から） |
| CLI | `cli.py permanent <session_id>` |

**期待結果**: `10-notes/permanent/ZK-….md`（1アイデア1ノート、複数可）。

### 8. task — タスク管理（GitHub Issue / Projects v2）
タスクを GitHub Issue として作成。Projects v2 ボードに自動登録される。

| 方法 | 実行 |
|---|---|
| Claude Code | `/task <内容>` |
| 拡張機能 | 「Second Brain: タスク追加」/ サイドバー「Second Brain タスク」パネル |
| CLI | `cli.py task add "<タイトル>" [--project "<案件>"] [--note <ZK-id>]` |
| | `cli.py task list` / `task show <番号>` / `task update <番号> <状態>` / `task done <番号>` |

**期待結果**: GitHub に Issue 作成、ボードに登録。`--note` 指定時はノートの `tasks:` に Issue 番号が逆リンクされる。

### 9. sync — GitHub 同期
ローカルと GitHub を同期する（全コマンドが実行前に自動で行うが、手動実行も可）。

| 方法 | 実行 |
|---|---|
| Claude Code | `/sync` |
| 拡張機能 | 「Second Brain: 同期」 |
| CLI | `cli.py sync` |

---

## CLI 専用のユーティリティコマンド

| コマンド | 機能 |
|---|---|
| `cli.py status` | 同期状態・セッション数・索引数を表示 |
| `cli.py index` | ローカルノートから ChromaDB を再構築 |
| `cli.py fetch-url "<URL>"` | 記事本文を取得（保存はしない） |
| `cli.py fetch-youtube "<URL>"` | YouTube 字幕を取得（保存はしない） |
| `cli.py sessions` | セッション一覧 |
| `cli.py session <id>` | セッション詳細（履歴）|
| `cli.py continue <id> "<msg>"` | セッションを継続 |
| `cli.py save <id>` | セッションをノートとして保存 |
| `cli.py discard <id>` | セッションを破棄 |
| `cli.py daemon` | 常駐デーモンをフォアグラウンドで起動 |

---

## 共通の動作

- **会話 → 保存** の流れ。コマンド実行直後はテンプレートを出さず、自然な会話で深掘り
  した後に保存操作で構造化ノートに整理される。
- 各操作の前に **GitHub と自動同期**。手編集は自動コミットで保護される。
- ノートは `ZK-YYYYMMDD-HHMMSS.md` 形式。保存時に commit + push + ChromaDB 索引。
- セッションはディスク永続。デーモンや VSCode を再起動しても会話は復元できる。
