"""Transparent toy-data semantic evaluation, NOT a production benchmark."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

from slothsort.config import CATEGORIES
from slothsort.demo import EXPECTED, create_demo
from slothsort.engine import load_encoder, suggest
from slothsort.scanner import scan

# Naive keyword baseline, intentionally simple and fully disclosed.
KEYWORDS = {
    "Finance": ("invoice", "receipt", "tax", "bank"),
    "Work": ("software", "bug", "sprint", "client"),
    "Health": ("doctor", "medicine", "clinic", "dental"),
    "Learning": ("tutorial", "examination", "lecture", "study"),
    "Personal": ("grocery", "family", "holiday", "shopping"),
}


def keyword_baseline(content: str) -> str | None:
    scores = {k: sum(word in content.casefold() for word in words) for k, words in KEYWORDS.items()}
    top = max(scores, key=scores.get)
    return top if scores[top] > 0 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    # Uses isolated synthetic data in temp dir; never touches a real user's inbox.
    import tempfile
    with tempfile.TemporaryDirectory() as scratch:
        inbox, _, _ = create_demo(Path(scratch))
        items, _ = scan(inbox)
        suggestions = suggest(items, CATEGORIES, load_encoder(offline=args.offline))
        by_name = {s.item.path.name: s for s in suggestions}
        ai_ok = baseline_ok = 0
        print("File           | Expected  | AI top-1  | AI auto? | Keyword baseline")
        print("-" * 75)
        for item in items:
            expected = EXPECTED[item.path.name]
            result = by_name[item.path.name]
            guess = result.category if result.eligible else None
            baseline = keyword_baseline(item.text)
            ai_ok += guess == expected
            baseline_ok += baseline == expected
            print(f"{item.path.name:14} | {str(expected):9} | {result.category:9} | {str(result.eligible):8} | {str(baseline)}")
        print(f"AI gated decisions: {ai_ok}/{len(items)}")
        print(f"Keyword baseline:   {baseline_ok}/{len(items)}")
        print("Small synthetic demo only. Scores are not probabilities. Verify results before quoting.")

if __name__ == "__main__":
    main()
