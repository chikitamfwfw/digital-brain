# Discord Second Brain Bot 🧠

DiscordをZettelkasten × GTDのセカンドブレインとして活用するAI Botです。

Claude AI（Web検索付き）+ ChromaDB（意味検索）+ GitHub（ノート保存）を組み合わせ、Discordで話した内容を自動的に構造化ノートとして蓄積します。

## 機能

| コマンド | 説明 |
|---|---|
| `/memo <テキスト>` | メモを共有してAIと深掘り会話。保存ボタンでFleetingノートに整理。Permanent Note化も可能。 |
| `/link <URL>` | 記事・YouTube URLを取り込んでAIと議論。保存でLiteratureノートに整理。 |
| `/research <トピック>` | Web検索＋蓄積知識を使って徹底調査。会話でさらに深掘りしてResearchノートに保存。 |
| `/planning <テーマ>` | アイデアや目標についてAIとブレスト。会話をPlanningノートに保存。 |
| `/search <クエリ>` | 蓄積した全ノートをセマンティック検索（意味的な近さで検索）。 |
| `/chat <メッセージ>` | Web検索＋過去ノートを参照した自由会話。会話を任意でノートに保存可能。 |

### 会話フロー

全コマンド共通で「**会話 → 保存**」の流れです。コマンド実行直後にMarkdownテンプレートは出力されません。自然な会話で深掘りした後、`💾 保存` ボタンを押した時点で会話全体がノートに整理されます。

```
/research 仁王3
  → AIがWeb検索して会話形式で話す
  → 追加で質問・議論できる
  → 💾 保存 → GitHubにResearchノートとしてコミット + ChromaDBに登録
```

## アーキテクチャ

```
Discord
  └── bot.py (discord.py 2.x, slash commands + on_message followup)
        ├── handlers/
        │     ├── memo.py      — /memo
        │     ├── link.py      — /link (記事 + YouTube)
        │     ├── research.py  — /research
        │     ├── planning.py  — /planning
        │     ├── search.py    — /search
        │     └── chat.py      — /chat
        └── services/
              ├── claude_client.py    — Claude API (web_search_20250305)
              ├── github_client.py    — ノートのGitHub保存 (5分TTLキャッシュ)
              ├── knowledge_store.py  — ChromaDB意味検索
              ├── scraper.py          — 記事スクレイピング
              └── youtube_client.py   — 字幕取得 → Whisperフォールバック
```

**Web検索:** Anthropic公式の `web_search_20250305` ツール（Claude.aiと同じ検索エンジン）を使用。APIキー不要。

**ノートID:** `ZK-20260504-143022` 形式（Zettelkasten準拠）

**GitHub構造:**
```
second-brain/
  00-inbox/           — 生メモ（/memo実行時に自動コミット）
  10-notes/
    fleeting/         — /memo, /chat 保存先
    literature/
      articles/       — /link 記事
      youtube/        — /link YouTube
    permanent/        — /memo の Permanent化
  20-research/        — /research
  30-planning/        — /planning
  _config/
    system-prompt.md  — Claudeの基本人格
    prompts/          — コマンドごとの振る舞い指示
    user-profile.md   — ユーザー設定（5分以内に反映）
  _templates/         — ノートテンプレート
```

## セットアップ

### 前提条件

- Python 3.11+
- ffmpeg（YouTube Whisper書き起こしに必要）
- Discord Bot（Message Content Intent 有効化済み）
- Anthropic API key
- GitHub PAT（`repo` スコープ）+ private リポジトリ

### インストール

```powershell
git clone <this-repo>
cd discord-second-brain

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### 環境変数の設定

```powershell
copy .env.example .env
```

`.env` を編集して各値を入力：

```
DISCORD_TOKEN=         # BotトークンDISCORD_GUILD_ID=       # サーバーID（右クリック→IDをコピー）
ANTHROPIC_API_KEY=     # Anthropic Console から取得
GITHUB_TOKEN=          # PAT（repoスコープ）
GITHUB_REPO=username/second-brain
CHROMA_DB_PATH=./chroma_db
TAVILY_API_KEY=        # 任意。未設定でもAnthropic Web Searchで動作
```

### GitHub リポジトリの初期化

GitHubで `second-brain` プライベートリポジトリを作成し、以下のフォルダを `.gitkeep` で初期化：

```
00-inbox/
10-notes/fleeting/
10-notes/literature/articles/
10-notes/literature/youtube/
10-notes/permanent/
20-research/
30-planning/
```

### プロンプト・テンプレートをプッシュ

```powershell
python update_all_content.py
```

これで `_config/` と `_templates/` の全ファイルがGitHubにコミットされます。

### 起動

```powershell
python bot.py
```

初回起動時はChromaDB埋め込みモデル（約420MB）がダウンロードされます。

## カスタマイズ

GitHub上の `_config/user-profile.md` を編集すると、Claudeの振る舞い（呼び名・話し方・興味分野など）をカスタマイズできます。変更は最大5分以内に自動反映されます（再起動不要）。

```yaml
## 基本情報
- 呼び名: shiki
- 話しかけ方: タメ口でフランクに

## 興味・専門分野
- VTuber・配信文化
- AI・機械学習
```

## 主要な依存パッケージ

| パッケージ | 用途 |
|---|---|
| `discord.py` | Discord Bot フレームワーク |
| `anthropic` | Claude API（Web検索ツール付き）|
| `PyGitHub` | GitHubへのノート保存 |
| `chromadb` | ベクトルDBによる意味検索 |
| `sentence-transformers` | 多言語埋め込みモデル |
| `trafilatura` | 記事スクレイピング |
| `youtube-transcript-api` | YouTube字幕取得（高速パス）|
| `yt-dlp` + `faster-whisper` | 字幕なし動画のWhisper書き起こし |
