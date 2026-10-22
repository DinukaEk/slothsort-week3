"""Safely inspect a flat inbox. Never execute or recursively follow content."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

SUPPORTED = {".txt", ".md", ".csv", ".json", ".pdf", ".docx"}
MAX_BYTES = 8 * 1024 * 1024
MAX_CHARACTERS = 3500


@dataclass(frozen=True)
class FileItem:
    path: Path
    text: str
    digest: str
    size: int


def hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(65536), b""):
            sha.update(part)
    return sha.hexdigest()


def _content(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".csv", ".json"}:
        return path.read_bytes()[:65536].decode("utf-8", errors="replace")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Install requirements.txt to read PDFs") from exc
        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:3])
    if ext == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("Install requirements.txt to read DOCX") from exc
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs[:120])
    return ""


def read_item(path: Path) -> FileItem:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Not a regular, non-symlink file")
    if path.name.startswith(".") or path.suffix.lower() not in SUPPORTED:
        raise ValueError("Unsupported or hidden file")
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ValueError("File exceeds 8 MB limit")
    content = _content(path)
    # Filename is context, content is the primary signal. Prevent giant prompts.
    text = f"Document name: {path.stem.replace('_', ' ')}. Document content: {content[:MAX_CHARACTERS]}"
    return FileItem(path=path, text=text, digest=hash_file(path), size=size)


def scan(inbox: Path) -> tuple[list[FileItem], list[tuple[str, str]]]:
    if inbox.is_symlink() or not inbox.is_dir():
        raise ValueError("Inbox must be an existing non-symlink directory")
    results: list[FileItem] = []
    skips: list[tuple[str, str]] = []
    for path in sorted(inbox.iterdir(), key=lambda p: p.name.casefold()):
        if path.is_symlink() or not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in SUPPORTED:
            skips.append((path.name, "Unsupported extension"))
            continue
        try:
            results.append(read_item(path))
        except (ValueError, RuntimeError, OSError, KeyError) as exc:
            skips.append((path.name, str(exc)))
        except Exception as exc:
            # Malformed PDFs/DOCXs should be skipped without stopping the whole batch.
            skips.append((path.name, f"Unreadable document ({type(exc).__name__})"))
    return results, skips
