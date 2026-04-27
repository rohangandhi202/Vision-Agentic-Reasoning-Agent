"""
app.py — Streamlit UI for the Vision + Agentic Reasoning Agent.

Run with: streamlit run app.py
"""

import os
import json
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
import anthropic

from utils.vision import extract_from_image
from utils.tools import save_to_sheet, generate_report, flag_for_review

load_dotenv()

CONFIDENCE_THRESHOLD = 0.8

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Vision Receipt Agent",
    page_icon="🧾",
    layout="centered",
)

st.title("🧾 Vision Receipt Agent")
st.caption("Upload a receipt or invoice — the agent extracts structured data and routes it automatically.")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("How it works")
    st.markdown("""
1. **Vision layer** — Claude reads the image and extracts structured data
2. **Confidence score** — Claude self-reports how readable the document is
3. **Routing decision** — Agent decides what to do:
   - ✅ High confidence → saves to Google Sheets + generates report
   - ⚠️ Low confidence → flags for human review
""")
    st.divider()
    st.markdown(f"**Confidence threshold:** `{CONFIDENCE_THRESHOLD}`")
    st.markdown("**Model:** `claude-opus-4-5`")
    st.markdown("**Storage:** Google Sheets")

# ── File uploader ─────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "Upload a receipt image",
    type=["jpg", "jpeg", "png", "webp"],
    help="Take a photo of any receipt, invoice, or bill"
)

if uploaded_file is None:
    st.info("Upload an image above to get started.")
    st.stop()

# ── Show uploaded image ───────────────────────────────────────────────────────

col1, col2 = st.columns([1, 1])
with col1:
    st.image(uploaded_file, caption="Uploaded image", use_container_width=True)

# ── Run the pipeline ──────────────────────────────────────────────────────────

with col2:
    st.markdown("### Agent status")
    run_button = st.button("▶ Run Agent", type="primary", use_container_width=True)

if run_button:
    # Save upload to a temp file so vision.py can read it from disk
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # ── Step 1: Vision extraction ─────────────────────────────────────────
        with st.spinner("🔍 Analyzing image..."):
            extraction = extract_from_image(tmp_path, client)
            extraction["_image_path"] = uploaded_file.name  # use original name for reports

        if extraction.get("_error"):
            st.error(f"Vision extraction failed: {extraction['_error']}")
            st.stop()

        confidence  = extraction.get("confidence", 0)
        high_conf   = confidence >= CONFIDENCE_THRESHOLD

        # ── Step 2: Show confidence ───────────────────────────────────────────
        conf_pct = int(confidence * 100)
        st.metric("Confidence score", f"{conf_pct}%")
        st.progress(confidence)

        # ── Step 3: Routing decision badge ────────────────────────────────────
        if high_conf:
            st.success("✅ High confidence — saving to Sheets and generating report")
        else:
            st.warning(f"⚠️ Low confidence — flagging for review\n\n_{extraction.get('low_confidence_reason', '')}_")

        # ── Step 4: Execute tools ─────────────────────────────────────────────
        with st.spinner("⚙️ Running agent actions..."):
            if high_conf:
                save_result   = save_to_sheet(extraction)
                report_result = generate_report(extraction)
                actions_taken = ["Saved to Google Sheets", "Generated markdown report"]
            else:
                flag_result  = flag_for_review(extraction)
                actions_taken = ["Flagged in Review Queue sheet"]

        st.markdown("**Actions taken:**")
        for action in actions_taken:
            st.markdown(f"- {action}")

    finally:
        os.unlink(tmp_path)  # clean up temp file

    # ── Step 5: Show extracted data ───────────────────────────────────────────
    st.divider()
    st.markdown("### Extracted data")

    # Key fields as metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Vendor",   extraction.get("vendor")   or "—")
    m2.metric("Total",    f"{extraction.get('currency', '')} {extraction.get('total', '—')}")
    m3.metric("Date",     extraction.get("date")      or "—")

    m4, m5 = st.columns(2)
    m4.metric("Document type", extraction.get("document_type") or "—")
    m5.metric("Tax",           f"{extraction.get('currency', '')} {extraction.get('tax', '—')}")

    # Line items table
    line_items = extraction.get("line_items", [])
    if line_items:
        st.markdown("**Line items**")
        st.dataframe(line_items, use_container_width=True)

    # Full JSON expander for the curious / debugging
    with st.expander("Full extraction JSON"):
        display = {k: v for k, v in extraction.items() if not k.startswith("_")}
        st.json(display)

    # Download report button if it was generated
    if high_conf:
        report_path = Path(f"outputs/{Path(uploaded_file.name).stem}_report.md")
        if report_path.exists():
            st.download_button(
                label="⬇️ Download report",
                data=report_path.read_text(),
                file_name=report_path.name,
                mime="text/markdown",
            )