"""Headless interface for preview, manual apply, scheduled watch, and undo."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import CATEGORIES, Settings
from .demo import create_demo
from .engine import load_encoder, suggest
from .operations import move_items, undo_last_batch
from .scanner import scan


def options(parser):
    parser.add_argument("--inbox", type=Path, default=Path("demo_workspace/inbox"))
    parser.add_argument("--out", type=Path, default=Path("demo_workspace/organized"))
    parser.add_argument("--offline", action="store_true", help="Require cached model; no network inference")
    parser.add_argument("--min-similarity", type=float, default=0.32)
    parser.add_argument("--min-margin", type=float, default=0.055)


def preview(settings: Settings, encoder):
    files, skipped = scan(settings.inbox)
    candidates = suggest(files, CATEGORIES, encoder, settings.min_similarity, settings.min_margin)
    for s in candidates:
        action = "READY" if s.eligible else "REVIEW"
        print(f"{action:6}  {s.item.path.name:24} -> {s.category:9} similarity={s.similarity:.3f} gap={s.margin:.3f}")
    for name, reason in skipped:
        print(f"SKIP    {name}: {reason}")
    return candidates


def run_watch(settings, encoder, interval: int, min_age: int):
    print("Watching only this inbox (Ctrl+C stops). High-confidence moves are automatic.")
    observations = {}
    reviewed_digests = {}  # Don't re-embed unchanged ambiguous files forever.
    while True:
        try:
            files, _ = scan(settings.inbox)
            now = time.time()
            stable = []
            current = set()
            for item in files:
                key = str(item.path)
                current.add(key)
                stat = item.path.stat()
                stamp = (stat.st_size, stat.st_mtime_ns)
                old = observations.get(key)
                cycles = (old[1] + 1) if old and old[0] == stamp else 1
                observations[key] = (stamp, cycles)
                if (cycles >= 2 and now - stat.st_mtime >= min_age
                        and reviewed_digests.get(key) != item.digest):
                    stable.append(item)
            observations = {k: v for k, v in observations.items() if k in current}
            reviewed_digests = {k: v for k, v in reviewed_digests.items() if k in current}
            if stable:
                predictions = suggest(stable, CATEGORIES, encoder, settings.min_similarity, settings.min_margin)
                for s in predictions:
                    reviewed_digests[str(s.item.path)] = s.item.digest
                    if not s.eligible:
                        print(f"REVIEW {s.item.path.name}: ambiguous, kept in inbox")
                        continue
                    try:
                        events = move_items(settings, [(s, s.category)], set(CATEGORIES))
                        for e in events:
                            print(f"AUTO {Path(e['source']).name} -> {e['category']}")
                    except (OSError, ValueError) as exc:
                        print(f"Skipped {s.item.path.name}: {exc}")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped watching.")
            return


def main(argv=None):
    parser = argparse.ArgumentParser(description="SlothSort — semantic local AI file organizer")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Create 11 synthetic example notes")
    for name in ("scan", "organize", "watch", "undo"):
        cmd = sub.add_parser(name)
        options(cmd)
        if name == "organize":
            cmd.add_argument("--approve-high", action="store_true", help="Move only eligible predictions")
        if name == "watch":
            cmd.add_argument("--auto", action="store_true", help="Explicitly opt into automated file moves")
            cmd.add_argument("--interval", type=int, default=6)
            cmd.add_argument("--min-age", type=int, default=6)
    args = parser.parse_args(argv)
    if args.command == "demo":
        inbox, dest, count = create_demo(Path("demo_workspace"))
        print(f"Created {count} demo files in {inbox}. Output folder: {dest}")
        return 0
    settings = Settings(args.inbox, args.out, args.min_similarity, args.min_margin)
    try:
        settings.validate()
        if args.command == "undo":
            events, failures = undo_last_batch(settings)
            print(f"Restored {len(events)} files from the last eligible batch")
            for failure in failures:
                print(f"REVIEW: {failure}")
            return 1 if failures else 0
        if args.command == "organize" and not args.approve_high:
            parser.error("organize requires --approve-high; preview first with scan")
        if args.command == "watch" and not args.auto:
            parser.error("watch requires --auto to authorize automatic file moves")
        encoder = load_encoder(offline=args.offline)
        if args.command == "watch":
            if args.interval < 1 or args.min_age < 0:
                parser.error("interval must be >=1 and min-age >=0")
            run_watch(settings, encoder, args.interval, args.min_age)
        else:
            candidates = preview(settings, encoder)
            if args.command == "organize":
                approved = [(s, s.category) for s in candidates if s.eligible]
                events = move_items(settings, approved, set(CATEGORIES))
                print(f"Moved {len(events)} high-confidence files; {len(candidates) - len(events)} remain for review")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
