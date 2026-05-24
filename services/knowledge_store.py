from __future__ import annotations
import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime
import config

COLLECTION_NAME = "notes"
EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"


class KnowledgeStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        self._embedder = SentenceTransformer(EMBEDDING_MODEL)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_note(
        self,
        note_id: str,
        content: str,
        command: str,
        file_path: str,
        tags: list[str],
        created_at: datetime | None = None,
    ) -> None:
        if created_at is None:
            created_at = datetime.now()
        embedding = self._embedder.encode(content).tolist()
        self._collection.upsert(
            ids=[note_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "note_id": note_id,
                "command": command,
                "file_path": file_path,
                "tags": ",".join(tags),
                "created_at": created_at.isoformat(),
            }],
        )

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        count = self._collection.count()
        if count == 0:
            return []

        embedding = self._embedder.encode(query).tolist()
        kwargs: dict = {
            "query_embeddings": [embedding],
            "n_results": min(n_results, count),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        out = []
        for i in range(len(results["ids"][0])):
            out.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        return out

    def count(self) -> int:
        return self._collection.count()

    def delete_note(self, note_id: str) -> None:
        """指定 ID のノートを索引から削除する（存在しない場合は無視）。"""
        try:
            self._collection.delete(ids=[note_id])
        except Exception:  # noqa: BLE001 - 削除失敗は致命傷ではない
            pass
