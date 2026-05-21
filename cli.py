"""`brain` CLI — 常駐デーモンの薄いクライアント。

Claude Code（スラッシュコマンドから）と人間の双方が使う。デーモンが起動していなければ
自動起動する。デーモンを介すことで埋め込みモデルがウォーム保持され、操作が高速になる。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import config

_BASE = f"http://{config.DAEMON_HOST}:{config.DAEMON_PORT}"
_ENGINE_DIR = Path(__file__).resolve().parent


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body or {}).encode("utf-8") if method == "POST" else None
    req = urllib.request.Request(_BASE + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}


def _daemon_up() -> bool:
    try:
        status, _ = _request("GET", "/health")
        return status == 200
    except urllib.error.URLError:
        return False


def _ensure_daemon() -> None:
    if _daemon_up():
        return
    print("[brain] starting daemon...", file=sys.stderr)
    subprocess.Popen(
        [sys.executable, str(_ENGINE_DIR / "daemon.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(120):  # 最大 ~60s（初回はモデルロードで時間がかかる）
        time.sleep(0.5)
        if _daemon_up():
            return
    print("[brain] daemon did not become ready in time", file=sys.stderr)
    sys.exit(1)


def _call(method: str, path: str, body: dict | None = None) -> dict:
    _ensure_daemon()
    status, payload = _request(method, path, body)
    if status >= 400:
        print(f"[brain] error {status}: {payload.get('error', payload)}", file=sys.stderr)
        if payload.get("conflict"):
            print("  競合ファイル: " + ", ".join(payload["conflict"]), file=sys.stderr)
        sys.exit(1)
    return payload


def _print(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brain", description="Second Brain engine CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("daemon", help="デーモンをフォアグラウンドで起動")
    sub.add_parser("sync", help="ローカル⇄GitHub を同期")
    sub.add_parser("status", help="同期・セッション状態を表示")
    sub.add_parser("index", help="ローカルノートから ChromaDB を再構築")

    p = sub.add_parser("search", help="意味検索")
    p.add_argument("query")
    p.add_argument("-n", type=int, default=5)

    p = sub.add_parser("fetch-url", help="記事をスクレイピング")
    p.add_argument("url")
    p = sub.add_parser("fetch-youtube", help="YouTube 書き起こしを取得")
    p.add_argument("url")

    p = sub.add_parser("note", help="整形済みノートを保存（Claude Code モード）")
    p.add_argument("note_type", choices=["fleeting", "article", "youtube", "research", "planning", "permanent"])
    p.add_argument("--file", help="ノート本文の Markdown ファイル（省略時は標準入力）")
    p.add_argument("--tag", action="append", default=[], help="タグ（複数指定可）")

    for name in ("memo", "research", "planning", "chat"):
        p = sub.add_parser(name, help=f"{name} セッションを開始")
        p.add_argument("text")
    p = sub.add_parser("link", help="URL を取り込んでセッション開始")
    p.add_argument("url")

    p = sub.add_parser("continue", help="セッションを継続")
    p.add_argument("session_id")
    p.add_argument("message")
    for name in ("save", "permanent", "discard"):
        p = sub.add_parser(name, help=f"セッションを {name}")
        p.add_argument("session_id")

    sub.add_parser("sessions", help="セッション一覧")
    p = sub.add_parser("session", help="セッション詳細")
    p.add_argument("session_id")

    args = parser.parse_args(argv)
    cmd = args.cmd

    if cmd == "daemon":
        import daemon

        daemon.main()
        return 0

    if cmd in ("sync", "index"):
        _print(_call("POST", f"/{cmd}"))
    elif cmd == "status":
        _print(_call("GET", "/status"))
    elif cmd == "search":
        res = _call("POST", "/search", {"query": args.query, "n": args.n})
        for i, r in enumerate(res.get("results", []), 1):
            meta = r.get("metadata", {})
            rel = 1 - r.get("distance", 1.0)
            print(f"{i}. {meta.get('note_id', r.get('id'))}  ({rel:.0%})  {meta.get('file_path', '')}")
    elif cmd == "fetch-url":
        _print(_call("POST", "/fetch-url", {"url": args.url}))
    elif cmd == "fetch-youtube":
        _print(_call("POST", "/fetch-youtube", {"url": args.url}))
    elif cmd == "note":
        content = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
        _print(_call("POST", "/note", {
            "note_type": args.note_type, "content": content, "tags": args.tag,
        }))
    elif cmd in ("memo", "research", "planning", "chat"):
        _print(_call("POST", "/session/start", {"command": cmd, "text": args.text}))
    elif cmd == "link":
        _print(_call("POST", "/session/start-link", {"url": args.url}))
    elif cmd == "continue":
        _print(_call("POST", "/session/continue", {
            "session_id": args.session_id, "message": args.message,
        }))
    elif cmd in ("save", "permanent", "discard"):
        _print(_call("POST", f"/session/{cmd}", {"session_id": args.session_id}))
    elif cmd == "sessions":
        _print(_call("GET", "/session/list"))
    elif cmd == "session":
        _print(_call("GET", f"/session/get?id={args.session_id}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
