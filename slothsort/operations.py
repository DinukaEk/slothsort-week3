"""Journaled file movement, no overwrites, and verify-before-undo."""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import Settings
from .engine import Suggestion
from .scanner import hash_file

JOURNAL_NAME = ".slothsort_journal.jsonl"


def _within(file: Path, folder: Path) -> bool:
    """Both paths resolve to canonical locations; forbid escaping via symlinks."""
    return file.resolve().parent == folder.resolve()


def _journal(dest: Path, event: dict) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with (dest / JOURNAL_NAME).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def history(dest: Path) -> list[dict]:
    file = dest / JOURNAL_NAME
    if not file.exists():
        return []
    events = []
    for line in file.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _new_target(folder: Path, name: str) -> Path:
    stem, suffix = Path(name).stem, Path(name).suffix
    candidate = folder / name
    n = 2
    while candidate.exists() or candidate.is_symlink():
        candidate = folder / f"{stem}__{n}{suffix}"
        n += 1
    return candidate


def move_items(settings: Settings, selections: Iterable[tuple[Suggestion, str]], allowed: set[str]) -> list[dict]:
    """Require explicit selected files and target categories, then journal each move."""
    settings.validate()
    original_inbox, dest = settings.inbox.resolve(), settings.organized.resolve()
    batch = str(uuid.uuid4())
    results = []
    for suggestion, category in selections:
        src = suggestion.item.path
        if category not in allowed:
            raise ValueError(f"Unknown target category: {category}")
        if src.is_symlink() or not src.is_file() or not _within(src, original_inbox):
            raise ValueError(f"Unsafe or missing source: {src}")
        if hash_file(src) != suggestion.item.digest:
            raise ValueError(f"File changed after preview. Re-scan: {src.name}")
        folder = dest / category
        if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
            raise ValueError(f"Invalid destination folder: {folder}")
        folder.mkdir(parents=True, exist_ok=True)
        target = _new_target(folder, src.name)
        # Prevent symlink races / redirects as far as practical for a local desktop tool.
        if not _within(target, folder) or src.is_symlink():
            raise ValueError("Unsafe destination")
        shutil.move(str(src), str(target))
        event = {
            "op": "move", "id": str(uuid.uuid4()), "batch": batch,
            "time": datetime.now(timezone.utc).isoformat(), "source": str(src),
            "target": str(target), "sha256": suggestion.item.digest, "category": category,
        }
        _journal(dest, event)
        results.append(event)
    return results


def undo_last_batch(settings: Settings) -> tuple[list[dict], list[str]]:
    settings.validate()
    events = history(settings.organized)
    undone = {e.get("ref") for e in events if e.get("op") == "undo"}
    moves = [e for e in events if e.get("op") == "move" and e.get("id") not in undone]
    if not moves:
        return [], []
    last_batch = moves[-1]["batch"]
    restore, errors = [], []
    for event in reversed([m for m in moves if m["batch"] == last_batch]):
        src, dst = Path(event["target"]), Path(event["source"])
        if (
            src.is_symlink() or not src.is_file()
            or src.parent.parent.resolve() != settings.organized.resolve()
            or dst.parent.resolve() != settings.inbox.resolve()
            or dst.exists() or dst.is_symlink()
        ):
            errors.append(f"Can't safely undo {src.name}: source changed, path escaped, or original name is taken")
            continue
        if hash_file(src) != event["sha256"]:
            errors.append(f"Can't undo {src.name}: file content changed since sorting")
            continue
        shutil.move(str(src), str(dst))
        _journal(settings.organized, {
            "op": "undo", "ref": event["id"],
            "time": datetime.now(timezone.utc).isoformat(),
        })
        restore.append(event)
    return restore, errors
