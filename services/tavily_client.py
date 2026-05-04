from __future__ import annotations
import asyncio
import aiohttp
import config


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web. Tries Tavily first, falls back to DuckDuckGo (no API key needed)."""
    if config.TAVILY_API_KEY:
        results = await _search_tavily(query, max_results)
        if results:
            return results

    return await asyncio.to_thread(_search_ddg, query, max_results)


async def _search_tavily(query: str, max_results: int) -> list[dict]:
    payload = {
        "api_key": config.TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.tavily.com/search",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("results", [])
    except Exception as e:
        print(f"[WARN] Tavily search failed: {e}")
        return []


def _search_ddg(query: str, max_results: int) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            # region="jp-jp" で日本語コンテンツを優先
            for r in ddgs.text(query, max_results=max_results, region="jp-jp"):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "content": r.get("body", ""),
                })
        return results
    except Exception as e:
        print(f"[WARN] DuckDuckGo search failed: {e}")
        return []
