from __future__ import annotations

from pathlib import Path

from docx import Document


def extract_text_from_docx(path: Path) -> str:
    doc = Document(str(path))
    parts: list[str] = []
    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts).strip()
