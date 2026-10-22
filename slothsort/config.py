"""User-editable topic definitions; changing them changes local model behavior."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CATEGORIES = {
    "Finance": "Bookkeeping, purchase invoices, receipts, expense reimbursements, bank transfers, payments, budgets, taxes and accounting paperwork.",
    "Work": "Software projects, feature requests, bug reports, sprint planning, team meeting notes, clients, contracts and project delivery.",
    "Health": "Health care, clinical visits, doctor appointments, dental check-ups, medicine, treatment instructions and medical records.",
    "Learning": "Study material, tutorials, class lectures, examinations, training courses, research notes and educational summaries.",
    "Personal": "Household errands, family plans, grocery shopping, travel packing, hobbies, celebrations and everyday personal life.",
}

@dataclass(frozen=True)
class Settings:
    inbox: Path
    organized: Path
    min_similarity: float = 0.32
    min_margin: float = 0.055

    def validate(self) -> None:
        src, dst = self.inbox.expanduser().resolve(), self.organized.expanduser().resolve()
        if not (0 <= self.min_similarity <= 1) or not (0 <= self.min_margin <= 1):
            raise ValueError("Thresholds must be between 0 and 1")
        if not src.is_dir():
            raise ValueError(f"Inbox does not exist: {src}")
        if self.inbox.is_symlink() or self.organized.is_symlink():
            raise ValueError("Symlink inbox/output folders are not allowed")
        if src == dst or src in dst.parents or dst in src.parents:
            raise ValueError("Inbox and output must be separate, non-nested folders")
        if dst.exists() and not dst.is_dir():
            raise ValueError("Output path is not a folder")
