# 🦥 SlothSort — the local AI file tidier that lets you do less

> **Hacktoberfest Open-Source AI Challenge · Week 3: Slow and Steady (October 19–25, 2026)**

**Drop your notes into an inbox. SlothSort reads their *meaning* with an open-weight embedding model, suggests the right folder, moves only what you approve, and remembers how to undo it.** For opt-in unattended operation, use watch mode with confidence gates so it automatically files only clear cases and leaves ambiguous ones alone.

No paid API. No account. No cloud upload of file contents. The local embedding model is the product's central decision-maker.

## What it looks like

1. Click **Create synthetic demo files** to generate 11 harmless documents with meaningless filenames such as `note_005.txt`.
2. Click **Scan inbox with local AI**. Meaningful contents like “follow-up consultation” get scored against user-editable category descriptions.
3. Review the suggestion table. Clear candidates are preselected; unsure candidates stay unchecked.
4. Click **Move selected files**. All moves are journaled without overwriting existing files.
5. Open **Undo / audit trail** and reverse the last batch.

> [Add your own screenshot here after running the app; no screenshot is included until the real UI has been verified.]

## Stack

| Layer | Technology | Why |
| --- | --- | --- |
| Semantic decisions | [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Apache-2.0 open-weight sentence embeddings; runs on-device |
| Model runner | [`sentence-transformers`](https://www.sbert.net/) | Open-source inference and interchangeable encoding API |
| UI | [Streamlit](https://streamlit.io/) | Local review app; runs on `localhost` |
| File readers | Python stdlib, `pypdf`, `python-docx` | Local text extraction, no online OCR |
| Audit/undo | JSONL file + SHA-256 | Reversible, traceable file operations |
| CI | GitHub Actions + pytest | 32 lightweight tests, no model download in CI |

### Why AI is *essential* here

The program deliberately has no hard-coded “invoice ⇒ Finance” production rules. File text and the category descriptions are embedded locally into vectors. Cosine similarity ranks the possible folders; a configurable threshold and gap between first and second place decide which predictions can be auto-filed. Replace the embedding model or rewrite category definitions to change the classification behavior without depending on a proprietary API.

A tiny *keyword baseline exists only in the evaluation script* so the write-up can compare model-based sorting against an intentionally simple alternative. Don't describe the baseline as production logic.

## Windows setup (PowerShell)

Requirements: Python 3.11, internet once to download Python packages and model weights.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/download_model.py
python -m streamlit run app.py
```

Streamlit should open `http://localhost:8501`. Click **Create synthetic demo files** before scanning.

### Demonstrate offline processing

After the model was cached successfully, stop Streamlit (`Ctrl+C`) and restart it with **strict offline mode** switched on in the sidebar, then disconnect from the internet and scan. The setting requests local cached model files only. For a command-line check, use:

```powershell
python -m slothsort.cli demo
python -m slothsort.cli scan --offline
```

If you get a missing-model error, first reconnect and run `python scripts/download_model.py` again. **Model installation requires internet; local inference does not.** There are no AI API usage fees, although electricity and hardware are not free.

## Headless laziness: optional watched inbox

Only after verifying the app with synthetic files:

```powershell
# Preview suggestions, without moving anything
python -m slothsort.cli scan --offline

# Explicitly move only high-scoring, well-separated predictions
python -m slothsort.cli organize --approve-high --offline

# Keep watching the demo inbox until you press Ctrl+C
python -m slothsort.cli watch --auto --offline --interval 6 --min-age 6

# Undo the last successful set of moves
python -m slothsort.cli undo
```

Pass `--inbox "C:\path\to\inbox" --out "C:\path\to\organized"` to point to your own folders. Source/output must be separate, non-nested folders. Watch mode waits at least two scans and `--min-age` seconds of unchanged metadata before considering new files. The watcher has no network requirement if the model is cached and `--offline` is specified.

**Watch runs only while its terminal is open.** For continuous operation, you can later attach it to a system scheduler. Do not test unattended automation on irreplaceable files; make a backup first.

## How safety works

- **Preview first.** The UI does not move anything until the person approves selected rows. CLI watch-mode auto-moving requires an explicit `--auto` flag.
- **Conservative gated sorting.** The model's score is cosine similarity, *not a probability*. Documents with small top-two gaps remain for review; thresholds are tunable.
- **Reversible.** Each move records its exact source, destination, timestamp, batch and SHA-256. Undo checks contents and refuses to overwrite an existing inbox file.
- **No overwrite.** A filename collision produces `name__2.txt` and so on.
- **Narrow input handling.** Flat inbox only, no symlink documents, no hidden files, no executable files and 8 MB max per file. Allowed: `.txt`, `.md`, `.csv`, `.json`, `.pdf`, `.docx`.
- **No cloud processing of document contents.** The app loads a public model from Hugging Face on first use, then embeds locally. Neither the app nor its model wrapper explicitly transmits private documents.
- **Not antivirus or data-loss insurance.** Back up files, keep the watcher under supervision when trying it with real documents, and don't treat embedding scores as guaranteed correctness. Image-only PDFs are not OCR'd.

## Run tests and evaluation

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/evaluate.py
python scripts/evaluate.py --offline
```

The unit tests use fake vector fixtures and don't need to download an AI model. `scripts/evaluate.py` really loads the open-weight model and reports AI gated decisions alongside an explicitly disclosed, naive keyword baseline on 11 **synthetic** text files (10 labeled categories + 1 expected-to-review ambiguous note). **Run the script locally and add its actual numbers to your blog post; the score is not a production benchmark.**

## Folder layout

```text
slothsort-week3/
├── app.py                      # Streamlit review + undo UI
├── slothsort/
│   ├── cli.py                  # scan / organize / watch / undo
│   ├── engine.py               # on-device embeddings + cosine scoring
│   ├── scanner.py              # safe document text extraction
│   ├── operations.py           # durable move journal and verified undo
│   ├── demo.py                 # synthetic notes and expected categories
│   └── config.py               # user-editable folder descriptions
├── scripts/
│   ├── download_model.py       # warm cached model once
│   └── evaluate.py             # real embedding vs simple keyword baseline
├── tests/                      # small deterministic tests
├── .github/workflows/tests.yml # CI uses python -m pytest
├── DEV_SUBMISSION.md           # fill in actual GitHub/demo/evaluation links
└── DEMO_AND_PUBLISH.md         # video walkthrough and submission checklist
```

## Why open innovation matters

A local open-weight embedding model allows each private file's *content* to be processed on the user's own machine, including offline after installation. No API keys or recurring token fees; categories can be personalized and the model swapped or fine-tuned. A closed hosted API might provide stronger general language reasoning, but it would introduce recurring cost and a third-party document-processing dependency. This product prioritizes modest local hardware and a transparent, user-controlled workflow instead.

## License and attributions

Project code: MIT (see `LICENSE`). Model `sentence-transformers/all-MiniLM-L6-v2`: Apache-2.0, provided by the Sentence Transformers community. Streamlit, PyPDF and python-docx are independent open-source dependencies with their own licenses. Never commit private folders, `demo_workspace`, downloaded model weights or credentials to your public repo. Use `.gitignore` provided.

**Submission deadline:** October 25, 2026, **11:59 PM PDT**. Official challenge: https://dev.to/challenges/hacktoberfest-week3-2026-10-19
