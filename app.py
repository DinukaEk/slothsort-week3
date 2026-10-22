"""Browser-based, local-only review UI for SlothSort."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from slothsort.config import CATEGORIES, Settings
from slothsort.demo import create_demo
from slothsort.engine import MODEL_ID, load_encoder, suggest
from slothsort.operations import history, move_items, undo_last_batch
from slothsort.scanner import scan

st.set_page_config(page_title="SlothSort · Local AI file organizer", page_icon="🦥", layout="wide")
st.markdown("""<style>
.block-container {padding-top:2rem; max-width:1200px;}
.hero {background:linear-gradient(110deg,#132d26,#25533d);border-radius:18px;padding:30px 32px;color:#f5f9f3;margin-bottom:18px}
.hero h1 {margin:0;font-size:2.5rem;color:#f5f9f3}
.hero p {font-size:1.07rem;color:#d5eadc;margin:8px 0 0}
.muted {color:#64726b;font-size:.9rem}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🦥 SlothSort</h1><p>Take it slow. Let your laptop sort the clutter — privately, locally, and with an undo button.</p></div>', unsafe_allow_html=True)
if st.session_state.pop("flash_moved", None) is not None:
    st.success("Selected files organized successfully. Use the Undo / audit trail tab to reverse the last batch.")
if st.session_state.pop("flash_undone", None) is not None:
    st.success("The last eligible batch was restored to the inbox.")

@st.cache_resource(show_spinner="Loading the local open-weight embedding model…")
def encoder_cached(offline: bool):
    return load_encoder(offline)

root = Path.cwd() / "demo_workspace"
with st.sidebar:
    st.header("Your quiet little workspace")
    if st.button("✨ Create synthetic demo files", use_container_width=True):
        inbox, dest, n = create_demo(root)
        st.success(f"Created {n} files (existing files preserved).")
        st.session_state.pop("suggestions", None)
    inbox_text = st.text_input("Inbox folder", str(root / "inbox"))
    dest_text = st.text_input("Output folder", str(root / "organized"))
    offline = st.toggle("Strict offline mode", value=False, help="Requires the model to have been downloaded already; no Hub requests")
    score = st.slider("Minimum similarity", 0.0, 0.80, 0.32, 0.01)
    gap = st.slider("Minimum winning margin", 0.0, 0.30, 0.055, 0.005, help="Difference between top two category similarities; not a probability")
    st.caption("All file content stays on this machine. Categories are editable in slothsort/config.py.")

settings = Settings(Path(inbox_text).expanduser(), Path(dest_text).expanduser(), score, gap)
try:
    settings.validate()
except ValueError as exc:
    st.info(f"Create the demo inbox above, or select valid folders. {exc}")
    st.stop()

left, mid, right = st.columns([1, 1, 1])
with left:
    st.metric("Category folders", len(CATEGORIES))
with mid:
    st.metric("Model API fees", "$0 per request")
with right:
    st.metric("Decision policy", "Review first")
st.caption(f"Open-weight model: `{MODEL_ID}` · Supported: TXT, MD, CSV, JSON, PDF, DOCX (text-based) · Direct files only; no recursive scanning")

review, audit = st.tabs(["🗂️ Review and organize", "↩️ Undo / audit trail"])
with review:
    st.write("AI suggests topics by meaning, not just matching keywords. Similarity scores are **not calibrated confidence percentages**. Nothing moves until you approve it here.")
    if st.button("🔎 Scan inbox with local AI", type="primary"):
        with st.spinner("Reading allowed document types and calculating local embeddings…"):
            try:
                files, skips = scan(settings.inbox)
                if files:
                    predicted = suggest(files, CATEGORIES, encoder_cached(offline), score, gap)
                else:
                    predicted = []
                st.session_state["suggestions"] = predicted
                st.session_state["scan_skips"] = skips
                st.session_state["scan_counter"] = st.session_state.get("scan_counter", 0) + 1
            except Exception as exc:
                st.error(f"Could not scan files: {exc}")
    predictions = st.session_state.get("suggestions", [])
    skips = st.session_state.get("scan_skips", [])
    if skips:
        with st.expander(f"Skipped files ({len(skips)})"):
            for filename, reason in skips:
                st.write(f"`{filename}` — {reason}")
    if predictions:
        ready = sum(s.eligible for s in predictions)
        ca, cb, cc = st.columns(3)
        ca.metric("Files scanned", len(predictions))
        cb.metric("Safe-to-suggest", ready)
        cc.metric("Needs attention", len(predictions)-ready)
        rows = [{
            "Approve": s.eligible,
            "Document": s.item.path.name,
            "Target category": s.category,
            "Similarity": round(s.similarity, 3),
            "Top-two gap": round(s.margin, 3),
            "Decision": "Suggested" if s.eligible else "Review needed",
        } for s in predictions]
        edited = st.data_editor(
            pd.DataFrame(rows), hide_index=True, use_container_width=True,
            key=f"review_{st.session_state.get('scan_counter',0)}",
            column_config={
                "Approve": st.column_config.CheckboxColumn(help="You control what moves"),
                "Target category": st.column_config.SelectboxColumn(options=list(CATEGORIES), required=True),
                "Similarity": st.column_config.NumberColumn(format="%.3f"),
                "Top-two gap": st.column_config.NumberColumn(format="%.3f"),
            }, disabled=["Document", "Similarity", "Top-two gap", "Decision"],
        )
        st.caption("A low-margin result stays unchecked by default. You may explicitly approve or change its target category. Review unusual predictions before proceeding.")
        approved = [(s, str(edited.iloc[ix]["Target category"])) for ix, s in enumerate(predictions) if bool(edited.iloc[ix]["Approve"])]
        st.write(f"**{len(approved)}** moves selected. Existing destination files will never be overwritten.")
        if st.button("✅ Move selected files", disabled=not approved):
            try:
                events = move_items(settings, approved, set(CATEGORIES))
                st.session_state["flash_moved"] = len(events)
                st.session_state.pop("suggestions", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Stopped: {exc}. Re-scan before retrying.")
    else:
        st.info("Create the demo inbox in the sidebar, then click **Scan inbox with local AI**.")

with audit:
    events = history(settings.organized)
    moved = [e for e in events if e.get("op") == "move"]
    undone = {e.get("ref") for e in events if e.get("op") == "undo"}
    active = [e for e in moved if e.get("id") not in undone]
    col1, col2 = st.columns(2)
    col1.metric("Total logged moves", len(moved))
    col2.metric("Still organized", len(active))
    st.caption("Undo verifies the file hash first and refuses to overwrite a file in the inbox.")
    if st.button("↩️ Undo last batch", disabled=not active):
        try:
            restored, errors = undo_last_batch(settings)
            if errors:
                for err in errors:
                    st.warning(err)
            elif restored:
                st.session_state["flash_undone"] = len(restored)
                st.session_state.pop("suggestions", None)
                st.rerun()
            else:
                st.info("No moves were eligible for undo.")
        except Exception as exc:
            st.error(str(exc))
    if moved:
        display = [{"File": Path(e["target"]).name, "Category": e["category"], "State": "Undone" if e["id"] in undone else "Moved", "Timestamp (UTC)": e["time"]} for e in reversed(moved)]
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.write("No file movements yet.")
