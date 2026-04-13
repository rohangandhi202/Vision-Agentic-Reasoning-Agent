# Vision + Agentic Reasoning Agent

A multimodal AI agent that processes images of receipts and invoices — extracting structured data, reasoning about confidence, and routing to the right action automatically.

**Built to demonstrate:** vision-to-reasoning handoff, confidence-based routing, multi-tool orchestration, and structured extraction from unstructured visual data.

---

## Architecture

```
Image Input
    │
    ▼
Vision Layer (Claude API)
  ├── Structured extraction (vendor, total, line items, etc.)
  └── Self-reported confidence score
    │
    ▼
Reasoning Layer (LangChain Agent)
  └── Think → Act → Observe loop
    │
    ├── confidence ≥ 0.8 → Save to Sheet + Generate Report
    └── confidence < 0.8 → Flag for Review
```

---

## Project Structure

```
vision-agent/
├── main.py              # CLI entry point (Day 1: test vision layer)
├── agent.py             # Full LangChain agent (Day 2+)
├── utils/
│   ├── vision.py        # Image encoding + Claude vision extraction
│   └── tools.py         # Agent tools (save to sheet, report, flag)
├── images/
│   └── test/            # Drop test receipt images here
├── outputs/             # Extracted JSON results saved here
├── requirements.txt
└── .env.example
```

---

## Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/YOUR_USERNAME/vision-agent.git
cd vision-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
cp .env.example .env
# Edit .env and paste your Anthropic API key
```

---

## Usage

### Day 1 — Test the vision layer

```bash
# Process a single receipt image
python main.py --image images/test/receipt.jpg

# Process a folder of images
python main.py --folder images/test/

# Save extracted JSON to outputs/
python main.py --image images/test/receipt.jpg --save
```

### Day 2+ — Run the full agent (coming soon)

```bash
python agent.py --image images/test/receipt.jpg
```

---

## Example Output

```json
{
  "vendor": "Whole Foods Market",
  "date": "2024-03-15",
  "total": 47.83,
  "subtotal": 44.75,
  "tax": 3.08,
  "currency": "USD",
  "line_items": [
    { "description": "Organic Bananas", "quantity": 1, "unit_price": 1.49, "total": 1.49 },
    { "description": "Greek Yogurt", "quantity": 2, "unit_price": 3.99, "total": 7.98 }
  ],
  "document_type": "receipt",
  "confidence": 0.95,
  "low_confidence_reason": null
}
```

---

## Key Agentic Patterns Demonstrated

- **Vision-to-reasoning handoff** — Claude processes raw image pixels and returns structured data for downstream logic
- **Confidence-based routing** — agent autonomously decides whether to persist data or escalate to human review
- **Multi-tool orchestration** — LangChain agent selects and calls the right tool based on reasoning
- **Structured extraction from unstructured visual data** — no templates or fixed layouts required