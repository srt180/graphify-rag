from __future__ import annotations

from dataclasses import dataclass

from app.document_loaders import ParsedSection


@dataclass(frozen=True)
class TextChunk:
    text: str
    page: int | None
    section_label: str | None


def chunk_sections(sections: list[ParsedSection], chunk_size: int, overlap: int) -> list[TextChunk]:
    if overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")

    chunks: list[TextChunk] = []
    for section in sections:
        for text in _split_text(section.text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(TextChunk(text=text, page=section.page, section_label=section.label))
    return chunks


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        target_end = min(start + chunk_size, len(text))
        end = target_end
        if target_end < len(text):
            newline = text.rfind("\n\n", start, target_end)
            space = text.rfind(" ", start, target_end)
            candidate = max(newline, space)
            if candidate > start + chunk_size // 2:
                end = candidate

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks

