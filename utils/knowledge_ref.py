from __future__ import annotations


def build_knowledge_context(results: list[dict], max_chars: int = 3000) -> str:
    """Format ChromaDB search results as a Markdown context block for Claude."""
    if not results:
        return ""

    parts = ["## 関連ノート（蓄積知識）\n\n"]
    total = len(parts[0])
    for r in results:
        meta = r.get("metadata", {})
        note_id = meta.get("note_id", r.get("id", "?"))
        tags = meta.get("tags", "")
        doc_snippet = r.get("document", "")[:600]
        distance = r.get("distance", 1.0)
        relevance = f"{(1 - distance) * 100:.0f}%" if distance <= 1.0 else "?"

        entry = (
            f"### {note_id} (関連度: {relevance})\n"
            f"**タグ:** {tags}\n\n"
            f"{doc_snippet}\n\n"
        )
        if total + len(entry) > max_chars:
            break
        parts.append(entry)
        total += len(entry)

    return "".join(parts)


def build_web_context(results: list[dict], max_chars: int = 2000) -> str:
    """Format Tavily web search results as a Markdown context block for Claude."""
    if not results:
        return ""

    parts = ["## Web検索結果\n\n"]
    total = len(parts[0])
    for r in results:
        title = r.get("title", "No title")
        url = r.get("url", "")
        content = r.get("content", "")[:400]
        entry = f"### {title}\n**URL:** {url}\n\n{content}\n\n"
        if total + len(entry) > max_chars:
            break
        parts.append(entry)
        total += len(entry)

    return "".join(parts)
