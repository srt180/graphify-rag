from __future__ import annotations

from collections.abc import Iterable

from openai import OpenAI

from app.config import Settings
from app.schemas import SourceOut


class BailianClient:
    def __init__(self, settings: Settings) -> None:
        api_key = settings.model_api_key
        if not api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured.")
        self.settings = settings
        self.client = OpenAI(api_key=api_key, base_url=settings.dashscope_base_url)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in _batched(texts, self.settings.embedding_batch_size):
            response = self.client.embeddings.create(
                model=self.settings.embedding_model,
                input=batch,
                dimensions=self.settings.embedding_dimensions,
                encoding_format="float",
            )
            for item in sorted(response.data, key=lambda data: data.index):
                vectors.append(list(item.embedding))
        return vectors

    def answer(self, question: str, sources: list[SourceOut]) -> str:
        context = _format_context(sources)
        response = self.client.chat.completions.create(
            model=self.settings.chat_model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You answer questions for a document knowledge base. "
                        "Use only the provided context. Cite sources with [1], [2], etc. "
                        "If the answer is not in the context, say that the knowledge base "
                        "does not contain enough information. Answer in the user's language."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question:\n{question}\n\nContext:\n{context}",
                },
            ],
        )
        return response.choices[0].message.content or ""


def _batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def _format_context(sources: list[SourceOut]) -> str:
    parts: list[str] = []
    for source in sources:
        page = f", page {source.page}" if source.page else ""
        parts.append(
            f"[{source.citation_id}] {source.filename}{page}\n"
            f"{source.text}"
        )
    return "\n\n".join(parts)

