from __future__ import annotations
import base64
import http.cookiejar
import os
import re
import aiohttp
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import trafilatura

# ボット対策で 403 を返すサイト（NewsPicks 等）対策として、実ブラウザに近い
# ヘッダーを一通り送る。
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

_COOKIE_JAR: http.cookiejar.MozillaCookieJar | None = None
_COOKIE_JAR_LOADED: bool = False

_NEXT_PAGE_TEXTS = [
    "次のページ", "次へ", "次ページ", "続きを読む",
    "Next page", "Next Page", "NEXT", "next »", "»",
]


@dataclass
class ScrapeResult:
    url: str
    title: str
    text: str
    is_paywall: bool = False
    page_count: int = 1
    images: list[str] = field(default_factory=list)  # 本文が画像で構成される記事の図解URL


def _get_cookie_jar() -> http.cookiejar.MozillaCookieJar | None:
    """COOKIES_FILE から Cookie ジャーを読み込む（ドメイン情報を保持したまま）。"""
    global _COOKIE_JAR, _COOKIE_JAR_LOADED
    if _COOKIE_JAR_LOADED:
        return _COOKIE_JAR
    _COOKIE_JAR_LOADED = True

    cookie_file = os.getenv("COOKIES_FILE", "")
    if not cookie_file or not os.path.exists(cookie_file):
        return None

    try:
        jar = http.cookiejar.MozillaCookieJar(cookie_file)
        jar.load(ignore_discard=True, ignore_expires=True)
        _COOKIE_JAR = jar
        print(f"[INFO] Loaded {sum(1 for _ in jar)} cookies from {cookie_file}")
        return jar
    except Exception as e:
        print(f"[WARN] Cookie load failed: {e}")
        return None


def _cookies_for_url(url: str) -> dict:
    """URL のドメインに一致する Cookie のみを {name: value} で返す。

    ブラウザ全体の Cookie エクスポート（多数サイト分）が渡されても、対象サイトの
    ドメインに一致する Cookie だけを送信する。他サイトのログイン情報を漏らさず、
    Cookie 名の衝突も防ぐ。
    """
    jar = _get_cookie_jar()
    if jar is None:
        return {}
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return {}
    out: dict = {}
    for c in jar:
        domain = (c.domain or "").lstrip(".").lower()
        if domain and (host == domain or host.endswith("." + domain)):
            out[c.name] = c.value
    return out


def _find_next_page_url(html: str, current_url: str) -> str | None:
    """Detect a 'next page' link via rel=next or common text patterns."""
    try:
        from lxml import html as lxml_html
        tree = lxml_html.fromstring(html.encode("utf-8"))

        # rel="next" on <a> or <link>
        for elem in tree.xpath(
            '//*[contains(concat(" ", normalize-space(@rel), " "), " next ")][@href]'
        ):
            href = elem.get("href", "").strip()
            if href and not href.startswith("#"):
                return urljoin(current_url, href)

        # Text-based patterns
        for a in tree.xpath("//a[@href]"):
            text = (a.text_content() or "").strip()
            href = a.get("href", "").strip()
            if href and not href.startswith("#") and any(p in text for p in _NEXT_PAGE_TEXTS):
                return urljoin(current_url, href)
    except Exception:
        pass
    return None


async def fetch_article(url: str) -> ScrapeResult:
    pages_html: list[str] = []
    current_url = url
    visited: set[str] = set()

    for _ in range(5):  # max 5 pages
        if current_url in visited:
            break
        visited.add(current_url)

        html = await _download_html(current_url, cookies=_cookies_for_url(current_url))
        if html is None:
            break
        pages_html.append(html)

        next_url = _find_next_page_url(html, current_url)
        if next_url is None or next_url in visited:
            break
        current_url = next_url

    if not pages_html:
        return ScrapeResult(url=url, title=url, text="", is_paywall=True)

    title = _extract_title(pages_html[0])
    texts: list[str] = []

    for i, html in enumerate(pages_html):
        text = trafilatura.extract(html, include_comments=False, include_tables=True)
        if text and len(text) >= 200:
            texts.append(text)
        elif i == 0:
            fallback_text, fallback_title = _newspaper_fallback(url, html)
            if not title:
                title = fallback_title
            if fallback_text and len(fallback_text) >= 200:
                texts.append(fallback_text)

    combined = "\n\n---\n\n".join(texts)

    # NewsPicks の「図解」記事は本文が文字でなく画像（図解パネル）で構成される。
    # その場合は本文の図解画像URLを集め、視覚モデルで読み取れるようにする。
    images: list[str] = []
    host = (urlparse(url).hostname or "").lower()
    if "newspicks.com" in host:
        m = re.search(r"/news/(\d+)", url)
        if m:
            images = _newspicks_figure_images(pages_html[0], m.group(1))

    # 本文テキストも図解画像も無ければペイウォール扱い。
    if (not combined or len(combined) < 200) and not images:
        return ScrapeResult(url=url, title=title or url, text="", is_paywall=True)

    return ScrapeResult(
        url=url,
        title=title or url,
        text=combined,
        is_paywall=False,
        page_count=len(pages_html),
        images=images,
    )


def _newspicks_figure_images(html: str, article_id: str) -> list[str]:
    """NewsPicks 記事HTMLから本文の図解画像URLを読み順で抽出する。

    図解記事は本文が文字でなく図解パネル（画像）で構成される。各パネルは
    webp（高解像度・軽量）と png の2形式で埋め込まれるため webp を優先する。
    画像URLは HTML属性内（&amp;）と JSON文字列内（\\u0026）の両方の形で現れる
    ため、両エスケープを正規化してから抽出する。
    """
    norm = html.replace("\\u0026", "&").replace("&amp;", "&")
    pat = re.compile(
        r"https://contents\.newspicks\.com/images/unified/newspicks-news/"
        + re.escape(article_id) + r"/(\d+)[^\s\"'<>\\]*"
    )
    panels: dict[str, list[str]] = {}
    for m in pat.finditer(norm):
        panels.setdefault(m.group(1), []).append(m.group(0))

    out: list[str] = []
    for panel_id in sorted(panels):  # パネルIDは固定長の数値なので文字列ソート＝読み順
        urls = panels[panel_id]
        webp = [u for u in urls if "WEBP" in u.upper()]
        out.append(webp[0] if webp else urls[0])
    return out


async def download_images_as_blocks(urls: list[str], limit: int = 20) -> list[dict]:
    """画像URL群をダウンロードし Anthropic API の image コンテンツブロック列にする。

    NewsPicks 図解記事のように本文が画像で構成されるページを、視覚モデルへ
    渡すための変換。会員制画像にも対応するためドメイン一致 Cookie を付与する。
    """
    allowed = ("image/jpeg", "image/png", "image/gif", "image/webp")
    blocks: list[dict] = []
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for url in urls[:limit]:
            try:
                async with session.get(
                    url,
                    cookies=_cookies_for_url(url),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        continue
                    ctype = (
                        resp.headers.get("Content-Type", "")
                        .split(";")[0].strip().lower()
                    )
                    if ctype not in allowed:
                        continue
                    data = await resp.read()
            except Exception:
                continue
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": ctype,
                    "data": base64.b64encode(data).decode("ascii"),
                },
            })
    return blocks


async def _download_html(url: str, cookies: dict | None = None) -> str | None:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(
                url,
                cookies=cookies or {},
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=True,
            ) as resp:
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
