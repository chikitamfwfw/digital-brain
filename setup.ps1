# digital-brain — セットアップスクリプト（Windows / PowerShell）
#
# 別PCでの環境構築用。venv 作成・依存インストール・.env 生成を自動化する。
# 使い方:  PowerShell で  .\setup.ps1
#
# .venv / .env / chroma_db / .brain は PC固有 or 秘密情報のため GitHub には
# 含まれない（.gitignore 済み）。本スクリプトでローカルに用意する。

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Python ランチャ（py 優先、無ければ python）
$pyCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "[1/3] Python 仮想環境 (.venv) を作成..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    & $pyCmd -3 -m venv .venv
} else {
    Write-Host "  .venv は既に存在します（スキップ）。"
}

Write-Host "[2/3] 依存パッケージをインストール（数分かかります）..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "[3/3] .env を準備..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  .env を作成しました。" -ForegroundColor Yellow
    Write-Host "  → .env を開き ANTHROPIC_API_KEY / GITHUB_TOKEN / GITHUB_REPO を設定してください。" -ForegroundColor Yellow
} else {
    Write-Host "  .env は既に存在します（スキップ）。"
}

Write-Host ""
Write-Host "セットアップ完了。" -ForegroundColor Green
Write-Host "次の手順:"
Write-Host "  1. .env を編集して API キーを設定"
Write-Host "  2. 動作確認:  .\.venv\Scripts\python.exe cli.py status"
