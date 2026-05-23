#!/usr/bin/env bash
# digital-brain — セットアップスクリプト（Mac / Linux）
#
# 別 PC（Mac 含む）での環境構築用。venv 作成・依存インストール・.env 生成を
# 自動化する。使い方:  bash setup.sh
#
# .venv / .env / chroma_db / .brain は PC 固有 or 秘密情報のため GitHub には
# 含まれない（.gitignore 済み）。本スクリプトでローカルに用意する。

set -euo pipefail
cd "$(dirname "$0")"

# Python ランチャ（python3 優先、無ければ python）
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[ERROR] python3 が見つかりません。先に Python 3.11+ を入れてください。" >&2
    echo "  Mac:  brew install python@3.12" >&2
    exit 1
fi

# ffmpeg のチェック（Whisper 音声処理に必要）
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "[WARN] ffmpeg が見つかりません。NewsPicks 動画の文字起こしに必要です。"
    echo "  Mac:    brew install ffmpeg"
    echo "  Ubuntu: sudo apt install ffmpeg"
    echo ""
fi

echo "[1/3] Python 仮想環境 (.venv) を作成..."
if [ ! -d ".venv" ]; then
    "$PY" -m venv .venv
else
    echo "  .venv は既に存在します（スキップ）。"
fi

echo "[2/3] 依存パッケージをインストール（数分かかります）..."
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo "[3/3] .env を準備..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  .env を作成しました。"
    echo "  → .env を開き ANTHROPIC_API_KEY / GITHUB_TOKEN / GITHUB_REPO を設定してください。"
else
    echo "  .env は既に存在します（スキップ）。"
fi

echo ""
echo "セットアップ完了。"
echo "次の手順:"
echo "  1. .env を編集して API キー等を設定"
echo "  2. 動作確認:  ./.venv/bin/python cli.py status"
