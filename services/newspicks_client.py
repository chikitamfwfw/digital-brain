"""NewsPicks 動画の取り込み（音声からの文字起こし）。

NewsPicks 動画はテキスト字幕トラックを持たない（字幕は映像に焼き込み）ため、
HLS ストリームから音声を取得し faster-whisper で文字起こしする。

重要: 動画ページ HTML に載っている m3u8 は「-public」版（ペイウォール用の
プレビュー。冒頭プレビュー以降は無音セグメント paywall_audio*.ts に差し替え
られている）。会員の完全版は、各画質バリアントの URL から「-public」を外した
ものを使う（ログイン Cookie で 200 が返り、実セグメントが取得できる）。
記事ページ（/news/...）は scraper.py が扱う。
"""
from __future__ import annotations

import asyncio
import os
import re
import tempfile
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import trafilatura

from services.scraper import _cookies_for_url, _download_html

# 動画ページ HTML 内の HLS マスタープレイリスト URL
_M3U8_RE = re.compile(r"https://vod\.newspicks\.com/[^\s\"'<>\\]+\.m3u8")
# マスター m3u8 内のバリアント定義（属性行 + 次行の URL）
_VARIANT_RE = re.compile(r"#EXT-X-STREAM-INF:([^\r\n]+)\r?\n([^\r\n#]+)")


@dataclass
class NewsPicksVideo:
    url: str
    title: str
    description: str
    transcript: str
    method: str  # "whisper" | "unavailable"


def is_newspicks_video_url(url: str) -> bool:
    """NewsPicks の動画ページ URL かどうかを判定する。"""
    host = (urlparse(url).hostname or "").lower()
    if "newspicks.com" not in host:
        return False
    return "/movie-series/" in url or "/movie/" in url or "movieId=" in url


async def get_newspicks_video(url: str) -> NewsPicksVideo:
    """NewsPicks 動画ページからタイトル・説明・文字起こしを取得する。"""
    html = await _download_html(url, cookies=_cookies_for_url(url))
    if not html:
        return NewsPicksVideo(url, url, "", "", "unavailable")

    meta = trafilatura.extract_metadata(html)
    title = (meta.title if meta and meta.title else "") or url
    description = trafilatura.extract(html, include_comments=False) or ""

    master_match = _M3U8_RE.search(html)
    if not master_match:
        return NewsPicksVideo(url, title, description, "", "unavailable")

    stream_url = await _resolve_member_stream(master_match.group(0))
    transcript = ""
    if stream_url:
        transcript = await asyncio.to_thread(_transcribe_hls, stream_url)
    return NewsPicksVideo(
        url=url,
        title=title,
        description=description,
        transcript=transcript,
        method="whisper" if transcript else "unavailable",
    )


async def _resolve_member_stream(master_url: str) -> str:
    """マスター m3u8 から、会員完全版バリアント（実音声つき）の URL を求める。

    HTML 記載の「-public」マスターはペイウォール版。各バリアント URL から
    「-public」を外すと、ログイン Cookie で完全版（実セグメント）が取得できる。
    音声は AAC-LC（mp4a.40.2）の最小バリアントを選ぶ。最低画質バリアントだけは
    HE-AAC で音声が壊れることがあるため避ける。
    """
    master = await _download_html(master_url, cookies=_cookies_for_url(master_url))
    if not master:
        return master_url

    variants: list[tuple[int, str, str]] = []  # (bandwidth, codecs, url)
    for attrs, vurl in _VARIANT_RE.findall(master):
        bw_match = re.search(r"BANDWIDTH=(\d+)", attrs)
        codecs_match = re.search(r'CODECS="([^"]+)"', attrs)
        variants.append((
            int(bw_match.group(1)) if bw_match else 0,
            codecs_match.group(1) if codecs_match else "",
            urljoin(master_url, vurl.strip()),
        ))
    if not variants:
        return master_url

    aac_lc = [v for v in variants if "mp4a.40.2" in v[1]]
    _, _, variant_url = min(aac_lc or variants, key=lambda v: v[0])

    # 「-public」を外して会員完全版にする。会員版が取れなければ public のまま。
    member_url = variant_url.replace("-public.m3u8", ".m3u8")
    if member_url != variant_url:
        body = await _download_html(member_url, cookies=_cookies_for_url(member_url))
        if body and "paywall" not in body and "#EXTINF" in body:
            return member_url
    return variant_url


def _transcribe_hls(m3u8_url: str) -> str:
    """HLS ストリームから音声を取得し faster-whisper で文字起こしする。

    youtube_client._transcribe_with_whisper と同じ仕組み（yt-dlp で音声取得 →
    faster-whisper）。長尺動画では CPU 処理に時間がかかる。
    """
    try:
        import yt_dlp
        from faster_whisper import WhisperModel
    except Exception as e:  # noqa: BLE001
        print(f"[newspicks] 依存パッケージのロード失敗: {e}")
        return ""

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts: dict = {
            "format": "best",
            "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }],
        }
        cookie_file = os.getenv("COOKIES_FILE", "")
        if cookie_file and os.path.exists(cookie_file):
            ydl_opts["cookiefile"] = cookie_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([m3u8_url])
        except Exception as e:  # noqa: BLE001
            print(f"[newspicks] 音声ダウンロード失敗: {e}")
            return ""

        mp3s = [f for f in os.listdir(tmpdir) if f.endswith(".mp3")]
        if not mp3s:
            print(f"[newspicks] 音声ファイルが見つかりません: {os.listdir(tmpdir)}")
            return ""
        audio_path = os.path.join(tmpdir, mp3s[0])

        try:
            model = WhisperModel("small", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(
                audio_path, beam_size=5, language="ja", vad_filter=True
            )
            return " ".join(seg.text for seg in segments).strip()
        except Exception as e:  # noqa: BLE001
            print(f"[newspicks] 文字起こし失敗: {e}")
            return ""
