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

### 2. link — 記事 / 動画 / 図解 URL を取り込んで保存
URL を取り込み、AI と議論して Literature ノートに整理する。対応するのは **通常記事 / YouTube / NewsPicks 会員制動画（音声を AI が文字起こし）/ NewsPicks 図解記事（本文画像を AI が読み取り）** の4種類。種類は自動判定される。

| 方法 | 実行 |
|---|---|
| Claude Code | `/link <URL>` |
| 拡張機能 | 「Second Brain: リンク取り込み」→ URL 入力 |
| CLI | `cli.py link "<URL>"` → `cli.py save <session_id>` |

**期待結果**: `10-notes/literature/articles/` または `youtube/` にノート作成。動画は本文末尾に `## 書き起こし全文` が付く。
**注意**: NewsPicks 動画は音声を Whisper で文字起こしするため、50分動画で **15〜30分** かかる（その間 `/link` は応答待ちになる）。

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

### 7. permanent — Permanent ノート抽出（提案ドリブン）
ノートから独立した Atomic な Permanent ノート（恒久ノート）を抽出する。`/permanent` を **引数なし** で実行すると、Claude が **全ノート種別**（fleeting / literature / research / planning）を走査し、恒久ノートにできる中身のあるものを **テーマ付きで複数提案**。あなたが選んだものを抽出する。特定のノートが対象なら引数で指定。

| 方法 | 実行 |
|---|---|
| Claude Code | `/permanent`（候補を提案）/ `/permanent <ノートID>`（指定） |
| CLI | `cli.py permanent <session_id>` |

**期待結果**: `10-notes/permanent/ZK-….md`（1アイデア1ノート、複数可）。情報の薄いノートは候補から外される。

### 8. task — タスク管理（GitHub Issue / Projects v2）
タスクを GitHub Issue として作成し、Projects v2 ボードに自動登録する。ボードには Status のほか **案件・期日・優先度（高/中/低）・工数(時間)・工数(日)** のフィールドがあり、絞り込み・並べ替えに使える。工数は時間 or 日数の片方でも両方でも指定可（タスク単位で使い分けられる）。

| 方法 | 実行 |
|---|---|
| Claude Code | `/task <やること> [案件:〜 期日:5/30 優先度:高 工数:3日 / 5時間]`（自然文OK・Claude が解釈） |
| 拡張機能 | 「Second Brain: タスク追加」/ サイドバー「Second Brain タスク」パネル |
| CLI 作成 | `cli.py task add "<タイトル>" [--project "<案件>"] [--due YYYY-MM-DD] [--priority 高\|中\|低] [--effort-hours <数値>] [--effort-days <数値>] [--note <ZK-id>]` |
| CLI 一覧 | `cli.py task list [--status Todo\|"In Progress"\|Done] [--project "<案件>"]` |
| CLI 詳細 | `cli.py task show <番号>` |
| CLI 更新 | `cli.py task update <番号> [<Todo\|"In Progress"\|Done>] [--project ...] [--due ...] [--priority ...] [--effort-hours ...] [--effort-days ...]` |
| CLI 完了 | `cli.py task done <番号>` |

**期待結果**: GitHub に Issue 作成、ボードに登録、Status=Todo、指定したフィールド（案件・期日・優先度・工数(時間)・工数(日)）に値が入る。`--note` 指定時はノートの `tasks:` に Issue 番号が逆リンクされる。

> **詳細マニュアル**: タスクの構造・ビューの作り方・ワークフロー例・既知の制限は [`docs/task-guide.md`](task-guide.md) を参照。

### 9. sync — GitHub 同期
ローカルと GitHub を双方向で同期する: 手編集の自動コミット → `pull --rebase` → push。**GitHub が常に最新版に保たれる**（手編集も自動コミット＋push で保護される）。全コマンドが実行前に自動で行うが、手動でも実行可。競合時は処理を止めて手動解決を依頼する（自動破棄しない）。

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
- 各操作の前に **GitHub と自動同期**（手編集は自動コミット＋push で保護され、GitHub が常に最新版）。
- ノートは `ZK-YYYYMMDD-HHMMSS.md` 形式。保存時に commit + push + ChromaDB 索引。
- セッションはディスク永続。デーモンや VSCode を再起動しても会話は復元できる。
- コードを更新したらデーモンを再起動する（古いコードがメモリに残ったままになるため）。
