from pathlib import Path

from app.document_loaders import parse_document


def test_parse_txt(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("First line\n\nSecond line\n", encoding="utf-8")

    sections = parse_document(path)

    assert len(sections) == 1
    assert sections[0].text == "First line\n\nSecond line"


def test_parse_markdown(tmp_path: Path) -> None:
    path = tmp_path / "guide.md"
    path.write_text("# Title\n\nContent", encoding="utf-8")

    sections = parse_document(path)

    assert sections[0].text.startswith("# Title")

