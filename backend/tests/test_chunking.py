from app.chunking import chunk_sections
from app.document_loaders import ParsedSection


def test_chunk_sections_keeps_short_text_together() -> None:
    chunks = chunk_sections([ParsedSection(text="hello world", page=2)], chunk_size=1200, overlap=200)

    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].page == 2


def test_chunk_sections_splits_long_text() -> None:
    text = "alpha " * 500

    chunks = chunk_sections([ParsedSection(text=text)], chunk_size=400, overlap=50)

    assert len(chunks) > 1
    assert all(chunk.text for chunk in chunks)

