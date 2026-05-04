from __future__ import annotations
import asyncio
import discord
from discord import app_commands

from services.knowledge_store import KnowledgeStore
from utils.formatters import truncate_for_discord


def register_search_command(
    tree: app_commands.CommandTree,
    guild: discord.Object,
    knowledge: KnowledgeStore,
) -> None:
    @tree.command(
        name="search",
        description="蓄積知識をセマンティック検索",
        guild=guild,
    )
    @app_commands.describe(query="検索クエリ")
    async def search_command(interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()

        results = await asyncio.to_thread(knowledge.search, query, 5)

        if not results:
            await interaction.followup.send(
                "🔍 該当するノートが見つかりませんでした。\n"
                "まず `/memo` や `/link` でノートを保存してください。"
            )
            return

        lines = [f"🔍 **「{query}」の検索結果** ({len(results)}件)\n"]
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            note_id = meta.get("note_id", r.get("id", "?"))
            command = meta.get("command", "?")
            tags = meta.get("tags", "")
            file_path = meta.get("file_path", "")
            distance = r.get("distance", 1.0)
            relevance = f"{(1 - distance) * 100:.0f}%"

            doc_preview = r.get("document", "")[:200].replace("\n", " ")

            lines.append(
                f"**{i}. `{note_id}`** ({command}) — 関連度: {relevance}\n"
                f"📁 `{file_path}`\n"
                f"🏷️ {tags}\n"
                f"> {doc_preview}...\n"
            )

        await interaction.followup.send(truncate_for_discord("\n".join(lines)))
