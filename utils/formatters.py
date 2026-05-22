from __future__ import annotations

from datetime import datetime
import re


def make_zk_id(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime("ZK-%Y%m%d-%H%M%S")


def make_timestamp_filename(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y%m%d-%H%M%S.md")


def make_zk_filename(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime("ZK-%Y%m%d-%H%M%S.md")


def sanitize_tags(raw_tags: list[str]) -> list[str]:
    return [re.sub(r"\s+", "-", t.strip().lower()) for t in raw_tags if t.strip()]


def truncate_for_discord(text: str, max_chars: int = 1900) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…(truncated)"


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block from the start of text."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].strip()
    return text


def split_for_discord(text: str, max_chars: int = 1900) -> list[str]:
    """Split text into chunks that fit within Discord's character limit."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    while len(text) > max_chars:
        split_at = text.rfind("\n", 0, max_chars)
        if split_at <= 0:
            split_at = max_chars
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def discord_preview(markdown: str, max_chars: int = 1800) -> str:
    """YAMLフロントマターを除去してDiscord向けに整形・切り詰める。"""
    return truncate_for_discord(strip_frontmatter(markdown), max_chars=max_chars)


def inject_tags(content: str, tags: list[str]) -> str:
    """Insert tags into YAML frontmatter, or prepend a minimal frontmatter block."""
    if content.startswith("---"):
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("tags:"):
                lines[i] = f"tags: [{', '.join(tags)}]"
                return "\n".join(lines)
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                lines.insert(i, f"tags: [{', '.join(tags)}]")
                return "\n".join(lines)
    return f"---\ntags: [{', '.join(tags)}]\n---\n\n{content}"


def set_frontmatter_field(content: str, key: str, value: str) -> str:
    """YAML フロントマターの ``key`` 行を ``value`` に置換する（無ければ追加）。

    フロントマターが無い内容はそのまま返す。
    """
    if not content.startswith("---"):
        return content
    lines = content.split("\n")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            # フロントマター内に key が無かった → 閉じ --- の直前に挿入
            lines.insert(i, f"{key}: {value}")
            return "\n".join(lines)
        if re.match(rf"^{re.escape(key)}:\s*", lines[i]):
            lines[i] = f"{key}: {value}"
            return "\n".join(lines)
    return content


def add_to_frontmatter_list(content: str, key: str, value: str) -> str:
    """YAML フロントマターのインラインリスト ``key`` に ``value`` を追加する。

    既存項目に同値があれば何もしない。フロントマター内に ``key`` が無ければ追加する。
    フロントマターが無い内容はそのまま返す。
    """
    if not content.startswith("---"):
        return content
    lines = content.split("\n")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            lines.insert(i, f"{key}: [{value}]")
            return "\n".join(lines)
        m = re.match(rf"^{re.escape(key)}:\s*\[(.*)\]\s*$", lines[i])
        if m:
            items = [x.strip() for x in m.group(1).split(",") if x.strip()]
            if value in items:
                return content
            items.append(value)
            lines[i] = f"{key}: [{', '.join(items)}]"
            return "\n".join(lines)
    return content


def format_search_results(results: list[dict]) -> str:
    if not results:
        return "No matching notes found."
    lines = []
    for i, r in enumerate(results, 1):
        score = r.get("distance", 0)
        meta = r.get("metadata", {})
        tags = meta.get("tags", "")
        tag_list = tags.split(",") if tags else []
        lines.append(
            f"**{i}. {meta.get('note_id', 'Unknown')}** "
            f"(score: {1 - score:.2f})\n"
            f"  Tags: {', '.join(tag_list)}\n"
            f"  Path: `{meta.get('file_path', '')}`"
        )
    return "\n\n".join(lines)
