"""Semantic classification: the open-weight model is the classification engine."""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Protocol, Sequence

from .scanner import FileItem

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

class Encoder(Protocol):
    def encode(self, sentences: list[str], **kwargs): ...


def load_encoder(offline: bool = False) -> Encoder:
    if offline:
        import os
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("AI dependencies missing. Run: python -m pip install -r requirements.txt") from exc
    try:
        return SentenceTransformer(MODEL_ID, local_files_only=offline)
    except Exception as exc:
        raise RuntimeError(
            "Could not load the model. First run 'python scripts/download_model.py' "
            "with internet, then use offline mode."
        ) from exc


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    av, bv = list(a), list(b)
    if len(av) != len(bv):
        raise ValueError("Embeddings have different dimensions")
    dot = sum(float(x) * float(y) for x, y in zip(av, bv))
    norm_a = sqrt(sum(float(x) ** 2 for x in av))
    norm_b = sqrt(sum(float(y) ** 2 for y in bv))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


@dataclass(frozen=True)
class Suggestion:
    item: FileItem
    category: str
    similarity: float
    margin: float
    eligible: bool
    runner_up: str


def suggest(
    items: list[FileItem],
    category_descriptions: Mapping[str, str],
    encoder: Encoder,
    min_similarity: float = 0.32,
    min_margin: float = 0.055,
) -> list[Suggestion]:
    if not items:
        return []
    if len(category_descriptions) < 2:
        raise ValueError("Provide at least two categories")
    if not 0 <= min_similarity <= 1 or not 0 <= min_margin <= 1:
        raise ValueError("Thresholds must be between 0 and 1")
    labels = list(category_descriptions)
    prompts = [f"This document belongs to: {name}. {category_descriptions[name]}" for name in labels]
    vectors = encoder.encode(prompts + [i.text for i in items])
    references, documents = vectors[:len(labels)], vectors[len(labels):]
    out: list[Suggestion] = []
    for item, vector in zip(items, documents):
        rank = sorted(zip(labels, (cosine(vector, ref) for ref in references)), key=lambda t: t[1], reverse=True)
        first, second = rank[0], rank[1]
        margin = first[1] - second[1]
        out.append(Suggestion(
            item=item, category=first[0], similarity=first[1], margin=margin,
            eligible=first[1] >= min_similarity and margin >= min_margin,
            runner_up=second[0],
        ))
    return out
