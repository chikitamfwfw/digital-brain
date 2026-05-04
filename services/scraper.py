from __future__ import annotations
import aiohttp
from dataclasses import dataclass
import trafilatura

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


@dataclass
class ScrapeResult:
    url: str
    title: str
    text: str
    is_paywall: bool = False


async def fetch_article(url: str) -> ScrapeResult:
    html = await _download_html(url)
    if html is None:
        return ScrapeResult(url=url, title=url, text="", is_paywall=True)

    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    title = _extract_title(html)

    if not text or len(text) < 200:
        text, fallback_title = _newspaper_fallback(url, html)
        if not title:
            title = fallback_title

    if not text or len(text) < 200:
        return ScrapeResult(url=url, title=title or url, text="", is_paywall=True)

    return ScrapeResult(url=url, title=title or url, text=text, is_paywall=False)


async def _download_html(url: str) -> str | None:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return None
                return await resp.text()
    except Exception:
        return None


def _extract_title(html: str) -> str:
    meta = trafilatura.extract_metadata(html)
    if meta and meta.title:
        return meta.title
    return ""


def _newspaper_fallback(url: str, html: str) -> tuple[str, str]:
    try:
        from newspaper import Article
        article = Article(url)
        article.set_html(html)
        article.parse()
        return article.text, article.title
    except Exception:
        return "", ""
