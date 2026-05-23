# セットアップ手順（別 PC・Mac での環境構築）

`digital-brain`（エンジン）と `second-brain`（ボルト）を、別の PC でも同じように
動かすための手順です。Windows と Mac/Linux の両方に対応。**Windows ⇄ Mac で
完全同期して使う運用** も想定しています。

---

## 仕組み — 何が GitHub で共有され、何がされないか

| 対象 | 共有方法 |
|---|---|
| プログラムコード（エンジン・拡張機能・テンプレート等） | **GitHub で共有**（digital-brain / second-brain リポジトリ） |
| ノート本体・スラッシュコマンド・設定 (`_config/`) | **GitHub で共有**（second-brain リポジトリ） |
| `.venv`（Python 仮想環境） | 各 PC で生成（容量が大きく PC 固有のため共有しない） |
| `.env`（APIキー・パス） | 各 PC で作成（**秘密情報のため GitHub には絶対に載せない**） |
| `cookies.txt`（会員制サイト用 Cookie） | 各 PC で配置（セッション情報のため共有しない） |
| `chroma_db` / `.brain` | 各 PC で自動生成（検索索引・セッションのローカルキャッシュ） |

→ 「別 PC で同じ環境」とは **「コード・ノート・設定は GitHub から取得 + 各 PC で
セットアップ手順を1回実行」** という形になります。

---

## 前提ソフト

| | Windows | Mac | Linux |
|---|---|---|---|
| Python 3.11+ | python.org の installer | `brew install python@3.12` | `apt install python3` 等 |
| Git | git-scm.com | `brew install git` | `apt install git` |
| ffmpeg（NewsPicks 動画用） | choco / scoop / 公式 zip | `brew install ffmpeg` | `apt install ffmpeg` |

---

## 共通手順

### 1. 2 つのリポジトリをクローン（同じ親フォルダに隣同士で）

```
git clone https://github.com/chikitamfwfw/digital-brain.git
git clone https://github.com/chikitamfwfw/second-brain.git
```

推奨フォルダ構成（親フォルダの名前は任意。`genai/` でも `secondbrain/` でも可）:

```
任意の親フォルダ/
  digital-brain/   ← エンジン
  second-brain/    ← ボルト（ノート）
```

### 2. セットアップスクリプトを実行

**Windows (PowerShell):**
```powershell
cd digital-brain
.\setup.ps1
```

**Mac / Linux (bash):**
```bash
cd digital-brain
bash setup.sh
```

venv 作成・依存インストール・`.env` 生成を自動で行います（数分）。

### 3. `.env` を編集

`digital-brain/.env` を開き、以下を設定:

| 項目 | 内容 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic の API キー |
| `GITHUB_TOKEN` | GitHub トークン（`repo` + `project` スコープ） |
| `GITHUB_REPO` | `chikitamfwfw/second-brain` |
| `GITHUB_PROJECT_NUMBER` | `14`（既存のタスクボード番号を固定。**未設定だと再作成される可能性あり**） |
| `VAULT_PATH` | （任意）second-brain のフルパス。隣り合っていれば自動検出される |
| `COOKIES_FILE` | （任意・NewsPicks 用）`cookies.txt` のフルパス |

**Mac 例:**
```
VAULT_PATH=/Users/<あなた>/path/to/second-brain
COOKIES_FILE=/Users/<あなた>/path/to/digital-brain/cookies.txt
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
GITHUB_REPO=chikitamfwfw/second-brain
GITHUB_PROJECT_NUMBER=14
```

**Windows 例:**
```
VAULT_PATH=C:/Users/<あなた>/path/to/second-brain
COOKIES_FILE=C:/Users/<あなた>/path/to/digital-brain/cookies.txt
（以下同上）
```

### 4. （NewsPicks 等を使うなら）`cookies.txt` を配置

会員制サイトの記事・動画を取り込みたい場合のみ。ブラウザ拡張「**Get cookies.txt LOCALLY**」等で、ログイン状態の Cookie を Netscape 形式でエクスポートし、`.env` の `COOKIES_FILE` に指定したパスに置く。

### 5. 動作確認

**Windows:**
```powershell
.\.venv\Scripts\python.exe cli.py status
```

**Mac / Linux:**
```bash
./.venv/bin/python cli.py status
```

`root` に second-brain のパス、`branch: main` などが表示されれば成功。
初回はモデルロードで30〜60秒かかります。

### 6. （任意）VSCode 拡張機能のビルド

```
cd vscode-extension
npm install
npm run compile
```

VSCode で `vscode-extension` フォルダを開いて F5 でデバッグ起動できます。

---

## Windows ⇄ Mac での完全同期運用

両 PC で同じ環境を保ち、どちらで作業しても同じノート・タスクが見える状態を作るための運用フロー。

### 同期の流れ（自動）

両 PC でデーモンが起動していれば、以下が自動で動きます:

1. PC A で作業（ノート保存・タスク追加・編集など）
2. PC A のデーモンが**自動コミット＋push** で GitHub に反映（保存時 + 定期 sync）
3. PC B 側で次に何かコマンド実行 → `brain sync` が走り、PC A の更新を取り込む

**手動で同期したいときは**:
```
brain sync       # ローカルとリモートを揃える
```

### PC 切り替え時の手順

たとえば PC（Windows）で作業して Mac に移るとき:

| 順序 | PC（Windows） | Mac |
|---|---|---|
| 1 | 作業終了。`brain sync` を1回叩いてもよい（普段は不要、デーモンが面倒を見る） | — |
| 2 | — | **`brain sync` を最初に1回**（PC の最新を取り込む） |
| 3 | — | 作業を続ける |
| 4 | — | 終了 |

「`brain sync` を最初に」は git pull に相当します。**コマンドを実行すれば自動で sync が走る** ので、明示的に叩く必要はあまりありません。

### 各 PC ローカルな状態の扱い

GitHub 経由では同期されないもの:

- **検索インデックス（`chroma_db`）**: ノートが GitHub から落ちてきたら、Mac 側で
  `brain index` を1回実行すれば再構築されます。
- **進行中のセッション**: PC ごとに独立。片方の PC で /memo を始めて未保存のまま
  もう片方に移ると、続きはできません（普通は save してから移る）。
- **`.env` の API キー**: 各 PC で個別に設定。
- **`cookies.txt`**: 各 PC のブラウザから個別にエクスポート。

---

## Mac 特有の調整ポイント

| 項目 | 内容 |
|---|---|
| **Python 実行パス** | `./.venv/bin/python`（Windows は `.\.venv\Scripts\python.exe`） |
| **ffmpeg** | `brew install ffmpeg`。Whisper による NewsPicks 動画文字起こしに必須 |
| **`.env` のパス** | スラッシュ `/` 区切りで。`/Users/<name>/...` 形式 |
| **改行コード** | `setup.sh` を git clone した直後はそのまま `bash setup.sh` で動く。`chmod +x setup.sh` で実行可能化してもよい |
| **コンソール** | デフォルトで UTF-8 なので Windows のような cp932 対策は不要（コードは入っているが無害） |
| **VSCode 拡張機能** | Mac でも同じビルド手順（`npm install && npm run compile`）。プラットフォーム差は無し |

### Claude Code でスラッシュコマンドを使うとき

このリポジトリのスラッシュコマンド本体は `second-brain/.claude/commands/` にあり、**GitHub 経由で同期されます**。Mac でも VSCode で `second-brain/` をワークスペースとして開けば `/memo` `/link` `/task` 等が即使えます。

複数リポジトリを横断して使いたい場合（親フォルダを VSCode で開きたい場合）は、親フォルダに `CLAUDE.md` と `.claude/commands/` の薄い委譲ファイルが必要です。これは PC ごとに作成（Windows でも Mac でも同じ手順）。詳細は親フォルダの `CLAUDE.md` を参照。

---

## 使い方

- **CLI**: `<venv 内 python> cli.py <コマンド>`
  （`sync` / `memo` / `research` / `search` / `task` など）
- **Claude Code**: `second-brain` フォルダを開き、`.claude/commands` の
  スラッシュコマンド（`/memo` `/research` `/task` など）を使用

詳細は:
- `digital-brain/docs/commands.md` — 全コマンド一覧
- `digital-brain/docs/task-guide.md` — タスク管理の詳細マニュアル
- `second-brain/CLAUDE.md` — Claude Code 向け操作指針
