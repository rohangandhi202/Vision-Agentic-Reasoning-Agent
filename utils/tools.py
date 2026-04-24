"""
tools.py — The three actions the agent can take after vision extraction.

Each function is a plain Python function today (Day 2).
On Day 3 we'll wrap these as LangChain tools and wire up real backends.
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path


# ── Tool 1: Save to CSV (Google Sheets on Day 3) ─────────────────────────────

def save_to_sheet(data: dict) -> dict:
    """
    Append extracted receipt data to a local CSV file.
    Day 3: swap this for gspread to write to Google Sheets.
    """
    output_path = Path("outputs/extractions.csv")
    output_path.parent.mkdir(exist_ok=True)

    # Flatten line_items to a string so CSV stays one row per receipt
    row = {
        "timestamp":     datetime.now().isoformat(),
        "image_path":    data.get("_image_path", ""),
        "vendor":        data.get("vendor"),
        "date":          data.get("date"),
        "total":         data.get("total"),
        "subtotal":      data.get("subtotal"),
        "tax":           data.get("tax"),
        "currency":      data.get("currency"),
        "document_type": data.get("document_type"),
        "confidence":    data.get("confidence"),
        "line_items":    json.dumps(data.get("line_items", [])),
    }

    file_exists = output_path.exists()
    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"  💾 Saved to {output_path}")
    return {"status": "saved", "path": str(output_path)}


# ── Tool 2: Generate markdown report ─────────────────────────────────────────

def generate_report(data: dict) -> dict:
    """
    Write a human-readable markdown summary of the extracted receipt.
    """
    image_name = Path(data.get("_image_path", "unknown")).stem
    output_path = Path(f"outputs/{image_name}_report.md")
    output_path.parent.mkdir(exist_ok=True)

    lines = [
        f"# Receipt Report — {data.get('vendor', 'Unknown Vendor')}",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Date | {data.get('date', 'N/A')} |",
        f"| Document Type | {data.get('document_type', 'N/A')} |",
        f"| Subtotal | {data.get('currency', '')} {data.get('subtotal', 'N/A')} |",
        f"| Tax | {data.get('currency', '')} {data.get('tax', 'N/A')} |",
        f"| **Total** | **{data.get('currency', '')} {data.get('total', 'N/A')}** |",
        f"| Confidence | {data.get('confidence', 'N/A')} |",
        f"",
    ]

    line_items = data.get("line_items", [])
    if line_items:
        lines += [
            "## Line Items",
            "",
            "| Description | Qty | Unit Price | Total |",
            "|-------------|-----|------------|-------|",
        ]
        for item in line_items:
            lines.append(
                f"| {item.get('description', '')} "
                f"| {item.get('quantity', '')} "
                f"| {item.get('unit_price', '')} "
                f"| {item.get('total', '')} |"
            )

    lines += [
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ]

    output_path.write_text("\n".join(lines))
    print(f"  📝 Report saved to {output_path}")
    return {"status": "report_generated", "path": str(output_path)}


# ── Tool 3: Flag for review ───────────────────────────────────────────────────

def flag_for_review(data: dict) -> dict:
    """
    Log low-confidence extractions to a review queue CSV.
    A human (you) checks this file and manually corrects or re-shoots the image.
    """
    output_path = Path("outputs/review_queue.csv")
    output_path.parent.mkdir(exist_ok=True)

    row = {
        "timestamp":             datetime.now().isoformat(),
        "image_path":            data.get("_image_path", ""),
        "confidence":            data.get("confidence"),
        "low_confidence_reason": data.get("low_confidence_reason"),
        "vendor":                data.get("vendor"),   # partial data — may still be useful
        "total":                 data.get("total"),
        "status":                "needs_review",
    }

    file_exists = output_path.exists()
    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"  ⚠️  Flagged for review → {output_path}")
    print(f"  Reason: {data.get('low_confidence_reason', 'No reason provided')}")
    return {"status": "flagged", "path": str(output_path)}