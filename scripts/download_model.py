"""One-time model cache warm-up. Subsequent runs may be fully offline."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from slothsort.engine import MODEL_ID, load_encoder

if __name__ == "__main__":
    model = load_encoder(offline=False)
    model.encode(["This is an offline-ready local file classification test."])
    print(f"Cached and tested {MODEL_ID}. You can now choose strict offline mode.")
