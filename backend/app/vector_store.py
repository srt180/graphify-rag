from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from app.config import Settings


@dataclass(frozen=True)
class ChunkPayload:
    doc_id: str
    filename: str
    chunk_id: str
    chunk_index: int
    text: str
    page: int | None
    section_label: str | None


class VectorStore:
    def __init__(self, settings: Settings) -> None:
        self.collection = settings.qdrant_collection
        self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)

    def healthcheck(self) -> str:
        try:
            self.client.get_collections()
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return f"error: {exc}"

    def ensure_collection(self, vector_size: int) -> None:
        try:
            info = self.client.get_collection(self.collection)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
            return

        vectors = info.config.params.vectors
        existing_size = getattr(vectors, "size", None)
        if existing_size and existing_size != vector_size:
            raise RuntimeError(
                f"Qdrant collection '{self.collection}' has vector size {existing_size}, "
                f"but embeddings returned size {vector_size}."
            )

    def upsert_chunks(self, vectors: list[list[float]], payloads: list[ChunkPayload]) -> None:
        if not vectors:
            return
        self.ensure_collection(len(vectors[0]))
        points = [
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, payload.chunk_id)),
                vector=vector,
                payload={
                    "doc_id": payload.doc_id,
                    "filename": payload.filename,
                    "chunk_id": payload.chunk_id,
                    "chunk_index": payload.chunk_index,
                    "text": payload.text,
                    "page": payload.page,
                    "section_label": payload.section_label,
                },
            )
            for vector, payload in zip(vectors, payloads, strict=True)
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def query(self, vector: list[float], top_k: int) -> list[dict]:
        try:
            result = self.client.query_points(
                collection_name=self.collection,
                query=vector,
                limit=top_k,
                with_payload=True,
            )
        except Exception:
            return []

        points = getattr(result, "points", result)
        hits: list[dict] = []
        for point in points:
            payload = dict(point.payload or {})
            payload["score"] = getattr(point, "score", None)
            hits.append(payload)
        return hits

    def delete_document(self, doc_id: str) -> None:
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id",
                                match=models.MatchValue(value=doc_id),
                            )
                        ]
                    )
                ),
                wait=True,
            )
        except Exception:
            return

