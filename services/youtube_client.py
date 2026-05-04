from __future__ import annotations
import asyncio
import re
import tempfile
import os
from dataclasses import dataclass


@dataclass
class TranscriptResult:
    video_id: str
    title: str
    transcript: str
    language: str
    method: str  # "api" | "whisper" | "unavailable"


_VIDEO_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})"
)


def _extract_video_id(url: str) -> str | None:
    m = _VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


async def get_transcript(url: str) -> TranscriptResult:
    video_id = _extract_video_id(url)
    if not video_id:
        return TranscriptResult(
            video_id="", title=url, transcript="", language="", method="unavailable"
        )

    loop = asyncio.get_event_loop()

    # Fast path: youtube-transcript-api (no audio download)
    result = await loop.run_in_executor(None, _try_transcript_api, video_id, url)
    if result:
        return result

    # Slow path: yt-dlp + faster-whisper
    result = await loop.run_in_executor(None, _transcribe_with_whisper, video_id, url)
    if result:
        return result

    return TranscriptResult(
        video_id=video_id,
        title=url,
        transcript="",
        language="",
        method="unavailable",
    )


def _try_transcript_api(video_id: str, url: str) -> TranscriptResult | None:
    """Fetch transcript using youtube-transcript-api v1.x (instant, no download)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Priority: ja/en first, then any available language
        transcript = None
        try:
            transcript = transcript_list.find_transcript(["ja", "en"])
        except NoTranscriptFound:
            for t in transcript_list:
                transcript = t
                break

        if transcript is None:
            return None

        fetched = transcript.fetch()
        text = " ".join(s.text for s in fetched)
        if not text.strip():
            return None

        title = _fetch_video_title(video_id, url)
        return TranscriptResult(
            video_id=video_id,
            title=title,
            transcript=text,
            language=transcript.language_code,
            method="api",
        )
    except TranscriptsDisabled:
        print(f"[INFO] Transcripts disabled for {video_id}")
        return None
    except Exception as e:
        print(f"[INFO] Transcript API failed for {video_id}: {e}")
        return None


def _fetch_video_title(video_id: str, url: str) -> str:
    """Get video title via yt-dlp metadata (no audio download)."""
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", f"YouTube: {video_id}")
    except Exception:
        return f"YouTube: {video_id}"


def _transcribe_with_whisper(video_id: str, url: str) -> TranscriptResult | None:
    try:
        import yt_dlp
        from faster_whisper import WhisperModel

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "96",
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", f"YouTube: {video_id}")

            mp3_files = [f for f in os.listdir(tmpdir) if f.endswith(".mp3")]
            if not mp3_files:
                print(f"[WARN] No mp3 found in tmpdir. Files: {os.listdir(tmpdir)}")
                return None
            audio_path = os.path.join(tmpdir, mp3_files[0])

            model = WhisperModel("small", device="cpu", compute_type="int8")
            segments, info_whisper = model.transcribe(audio_path, beam_size=5)
            text = " ".join(seg.text for seg in segments)

            return TranscriptResult(
                video_id=video_id,
                title=title,
                transcript=text,
                language=info_whisper.language,
                method="whisper",
            )
    except Exception as e:
        print(f"[WARN] Whisper transcription failed: {e}")
        return None
