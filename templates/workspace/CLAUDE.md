# Second Brain — 操作ガイド（このワークスペース）

このフォルダには Second Brain システムの 2 リポジトリがある:

- `digital-brain/` — エンジン（保存・Git 同期・意味検索・スクレイピング・YouTube 書き起こし）
- `second-brain/` — ボルト（ノート本体・設定 `_config/`・テンプレート `_templates/`）

`/memo` `/link` `/research` `/planning` `/chat` `/search` `/sync` `/permanent` `/task`
のスラッシュコマンドでこのシステムを操作する。

## エンジンの呼び出し（手順中の `brain` の読み替え）

各コマンド手順に出てくる `brain <サブコマンド>` は、次のコマンドの略記:

```
digital-brain\.venv\Scripts\python.exe digital-brain\cli.py <サブコマンド>
```

（Mac/Linux は `digital-brain/.venv/bin/python digital-brain/cli.py`）
初回呼び出し時に常駐デーモンが自動起動し、以後の操作は高速になる。

## パスの読み替え

各コマンド手順に出てくる `_config/...`・`_templates/...` などのボルト内パスは、
このワークスペースでは **`second-brain/` 配下**を指す。
例: `_config/prompts/memo.md` → `second-brain/_config/prompts/memo.md`

## 役割分担（Claude Code モード）

- 会話・ノート整形・タグ付け・Web 検索は Claude Code（あなた）が担当する。
- エンジンは処理専用: `sync` / `search` / `fetch-url` / `fetch-youtube` / `note`。
- ノートの保存はエンジンに任せる（ローカル書き込み → commit → push → ChromaDB 索引）。

## 基本ワークフロー（全コマンド共通）

1. `brain sync` で同期する。競合が報告されたら処理を止め、ユーザーに手動解決を依頼する
   （自動破棄しない）。
2. `second-brain/_config/` の `system-prompt.md`・`user-profile.md`・
   `prompts/<command>.md` を読み、その人格・会話スタイルで対話する。
3. ユーザーと自然に会話する。事実確認は WebSearch、関連する過去ノートは
   `brain search "<クエリ>"` で参照する。
4. ユーザーが保存を望んだら、`second-brain/_templates/` の該当テンプレートに沿って
   Markdown ノートを整形し、一時ファイルに書き出して
   `brain note <note_type> --file <path>` で保存する。

## ノート形式・タスク管理

- ノートは `ZK-YYYYMMDD-HHMMSS.md` 形式、YAML フロントマター + Markdown 本文。
- タスクは GitHub Issue（実体）+ Projects v2 ボード（ビュー）で管理する。
- 詳細は `second-brain/CLAUDE.md` を参照。
