"""Multi-format policy loader used by the RAG ingestion stage."""

from __future__ import annotations

import re
from pathlib import Path


def _markdown_sections(text: str, fallback_title: str) -> list[tuple[str, str]]:
    sections = []
    current = fallback_title
    buffer = []
    for line in text.splitlines():
        if line.startswith("#"):
            if buffer:
                sections.append((current, "\n".join(buffer).strip()))
                buffer = []
            current = re.sub(r"^#+\s*", "", line).strip()
        else:
            buffer.append(line)
    if buffer:
        sections.append((current, "\n".join(buffer).strip()))
    return [(s, b) for s, b in sections if b]


def load_sections(path: Path) -> list[tuple[str, str]]:
    """Load Markdown, TXT, HTML or PDF into section/body pairs."""
    suffix = path.suffix.lower()
    title = path.stem.replace("_", " ").title()
    if suffix in {".md", ".txt"}:
        return _markdown_sections(path.read_text(encoding="utf-8"), title)
    if suffix == ".html":
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        text = soup.get_text("\n")
        return _markdown_sections(text, title)
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        sections = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                sections.append((f"PDF page {page_number}", text.strip()))
        return sections
    raise ValueError(f"Unsupported policy format: {path.suffix}")
