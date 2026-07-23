"""Handbook corpus loading and evidence retrieval."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from helpdesk.config import DATA_DIR, FALLBACK_HANDBOOK


def _read_pdf_text(path: Path) -> str:
    try:
        import fitz  # pymupdf

        doc = fitz.open(path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    except Exception:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
        except Exception:
            return ""


def load_handbook_corpus() -> list[dict[str, Any]]:
    """Load knowledge chunks from data/*.pdf and data/*.txt."""
    sources: list[tuple[Path, str]] = []

    if DATA_DIR.is_dir():
        for path in sorted(DATA_DIR.glob("*")):
            if path.suffix.lower() == ".pdf":
                text = _read_pdf_text(path)
                if text:
                    sources.append((path, text))
            elif path.suffix.lower() in {".txt", ".md"}:
                sources.append((path, path.read_text(encoding="utf-8")))

    if not sources:
        sources = [(Path("fallback"), FALLBACK_HANDBOOK)]

    chunks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path, text in sources:
        source_type = "pdf" if path.suffix.lower() == ".pdf" else "txt"
        title = path.name if path.name != "fallback" else "Handbook"
        parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(parts) <= 1:
            parts = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 20]
        for part in parts:
            key = part.lower()
            if key in seen:
                continue
            seen.add(key)
            chunks.append(
                {
                    "id": f"{path.stem}-{len(chunks)}",
                    "title": title,
                    "excerpt": part,
                    "sourceType": source_type,
                    "sourcePath": str(path),
                }
            )

    return chunks or [
        {
            "id": "fallback-0",
            "title": "Handbook",
            "excerpt": FALLBACK_HANDBOOK,
            "sourceType": "txt",
            "sourcePath": "fallback",
        }
    ]


HANDBOOK_CHUNKS = load_handbook_corpus()


def tokenize(text: str) -> set[str]:
    return {
        t
        for t in re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
        if len(t) > 2
    }


def overlap_score(query: str, candidate: str) -> float:
    q = tokenize(query)
    return len(q & tokenize(candidate)) / len(q) if q else 0.0


def retrieve_similar(
    ticket: dict[str, Any], history: list[dict[str, Any]], limit: int = 3
) -> list[dict[str, Any]]:
    query = f"{ticket['title']} {ticket['description']}"
    hits = [
        {
            "title": item["title"],
            "category": item["category"],
            "score": overlap_score(
                query, f"{item['title']} {item['description']} {item['category']}"
            ),
            "sourceType": "db",
        }
        for item in history
        if item["id"] != ticket["id"]
    ]
    return sorted(
        (h for h in hits if h["score"] > 0), key=lambda h: h["score"], reverse=True
    )[:limit]


def retrieve_handbook(ticket: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    query = f"{ticket['title']} {ticket['description']}"
    hits = [
        {
            "id": chunk["id"],
            "title": chunk["title"],
            "excerpt": chunk["excerpt"],
            "score": overlap_score(query, chunk["excerpt"]),
            "sourceType": chunk["sourceType"],
            "sourcePath": chunk.get("sourcePath"),
        }
        for chunk in HANDBOOK_CHUNKS
    ]
    return sorted(
        (h for h in hits if h["score"] > 0), key=lambda h: h["score"], reverse=True
    )[:limit]


def normalize_category(raw: Any) -> str:
    text = str(raw or "OTHER").upper()
    for label in ("FACILITIES", "HR", "IT", "OTHER"):
        if label in text:
            return label
    return "OTHER"


def normalize_priority(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).upper()
    for label in ("URGENT", "HIGH", "MEDIUM", "LOW"):
        if label in text:
            return label
    return "MEDIUM"
