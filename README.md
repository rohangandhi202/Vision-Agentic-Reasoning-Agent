# Vision + Agentic Reasoning Agent

A multimodal AI agent that processes receipt and invoice images — extracting structured data, reasoning about extraction confidence, and autonomously routing to the right action.

Built to demonstrate production-grade agentic patterns: vision-to-reasoning handoff, confidence-based routing, multi-tool orchestration, and structured extraction from unstructured visual data.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Claude](https://img.shields.io/badge/Claude-claude--opus--4--5-purple) ![Streamlit](https://img.shields.io/badge/UI-Streamlit-red) ![Sheets](https://img.shields.io/badge/Storage-Google%20Sheets-green)

---

## Demo

Upload a receipt → agent extracts structured data → routes automatically based on confidence:

| High confidence ✅ | Low confidence ⚠️ |
|---|---|
| Saves to Google Sheets | Flags in Review Queue |
| Generates markdown report | Logs reason for failure |
| Shows extracted line items | Preserves partial data |

---

## Architecture

```
Image Input
     │
     ▼
┌─────────────────────────────────┐
│         Vision Layer            │
│  Claude API (claude-opus-4-5)   │
│  • Structured JSON extraction   │
│  • Self-reported confidence     │
│  • Ambiguity detection          │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│        Reasoning Layer          │
│     Python Orchestrator         │
│  • Reads confidence score       │
│  • Routes to correct tool       │
└──────┬───────────────┬──────────┘
       │               │
  conf ≥ 0.8      conf < 0.8
       │               │
       ▼               ▼
┌────────────┐   ┌─────────────┐
│ Save to    │   │ Flag for    │
│ Sheets +   │   │ Review      │
│ Report     │   │ Queue       │
└────────────┘   └─────────────┘
```

---

## Key Agentic Patterns Demonstrated

**Vision-to-reasoning handoff** — Claude processes raw image pixels and returns structured JSON that downstream logic can act on. No templates, no fixed layouts — works on any receipt format.

**Confidence-based routing** — the agent asks Claude to self-report a confidence score (0.0–1.0) alongside the extraction. Scores below 0.8 trigger human review instead of automated persistence. This mirrors real-world MLOps patterns where model uncertainty gates automated decisions.

**Multi-tool orchestration** — the agent selects and executes different tools depending on the routing decision: Google Sheets append, markdown report generation, or review queue logging.

**Graceful degradation** — if the Sheets API is unreachable, tools automatically fall back to local CSV so data is never lost.

---

## Project Structure

```
vision-agent/
├── app.py               # Streamlit UI — file uploader, confidence display, results
├── agent.py             # CLI pipeline — vision → route → tools
├── main.py              # Day 1 test script — raw vision extraction only
├── utils/
│   ├── vision.py        # Image encoding + Claude vision extraction
│   └── tools.py         # save_to_sheet, generate_report, flag_for_review
├── images/
│   └── test/            # Drop test receipt images here
├── outputs/             # Generated reports saved here
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/vision-agent.git
cd vision-agent
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account", ...}
GOOGLE_SHEET_ID=your_spreadsheet_id_here
```

### 3. Set up Google Sheets

- Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com) (use "No organization")
- Enable the **Google Sheets API** and **Google Drive API**
- Create a service account → download the JSON key
- Create a Google Sheet and share it with the service account's `client_email` as Editor
- Paste the full JSON contents into `GOOGLE_SERVICE_ACCOUNT_JSON` in your `.env`

The agent auto-creates two tabs on first run: **Extractions** (high confidence) and **Review Queue** (low confidence).

---

## Stack

| Component | Technology |
|-----------|-----------|
| Vision + reasoning | Claude API (`claude-opus-4-5`) |
| UI | Streamlit |
| Storage | Google Sheets via gspread |
| Image processing | Pillow |
| Auth | Google service account (OAuth2) |
| Runtime | Python 3.12 |