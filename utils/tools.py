"""
tools.py — The three actions the agent can take after vision extraction.

Day 3: Google Sheets backend via gspread.
Each tool writes to a dedicated sheet tab inside one Google Spreadsheet.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TAB_EXTRACTIONS = "Extractions"
TAB_REVIEW      = "Review Queue"

EXTRACTION_HEADERS = [
    "Timestamp", "Image", "Vendor", "Date", "Total",
    "Subtotal", "Tax", "Currency", "Type", "Confidence", "Line Items"
]
REVIEW_HEADERS = [
    "Timestamp", "Image", "Confidence", "Reason", "Vendor", "Total", "Status"
]


def _get_sheet_client():
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise EnvironmentError("GOOGLE_SERVICE_ACCOUNT_JSON not set in .env")
    creds_dict = json.loads(raw)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_tab(spreadsheet, tab_name: str, headers: list) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="RAW")
        print(f"  Created new tab: {tab_name}")
    return ws


def save_to_sheet(data: dict) -> dict:
    """Append a high-confidence extraction to the Extractions tab."""
    try:
        client      = _get_sheet_client()
        sheet_id    = os.getenv("GOOGLE_SHEET_ID")
        spreadsheet = client.open_by_key(sheet_id)
        ws          = _get_or_create_tab(spreadsheet, TAB_EXTRACTIONS, EXTRACTION_HEADERS)
        row = [
            datetime.now().isoformat(),
            str(Path(data.get("_image_path", "")).name),
            data.get("vendor")        or "",
            data.get("date")          or "",
            data.get("total")         or "",
            data.get("subtotal")      or "",
            data.get("tax")           or "",
            data.get("currency")      or "",
            data.get("document_type") or "",
            data.get("confidence")    or "",
            json.dumps(data.get("line_items", [])),
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"  Saved to Google Sheets -> {TAB_EXTRACTIONS}")
        return {"status": "saved", "tab": TAB_EXTRACTIONS}
    except Exception as e:
        print(f"  Sheets write failed ({e}), falling back to CSV")
        return _csv_fallback(data, "outputs/extractions_fallback.csv")


def generate_report(data: dict) -> dict:
    """Write a human-readable markdown summary of the extracted receipt."""
    image_name  = Path(data.get("_image_path", "unknown")).stem
    output_path = Path(f"outputs/{image_name}_report.md")
    output_path.parent.mkdir(exist_ok=True)
    lines = [
        f"# Receipt Report — {data.get('vendor', 'Unknown Vendor')}",
        "", "| Field | Value |", "|-------|-------|",
        f"| Date | {data.get('date', 'N/A')} |",
        f"| Document Type | {data.get('document_type', 'N/A')} |",
        f"| Subtotal | {data.get('currency', '')} {data.get('subtotal', 'N/A')} |",
        f"| Tax | {data.get('currency', '')} {data.get('tax', 'N/A')} |",
        f"| **Total** | **{data.get('currency', '')} {data.get('total', 'N/A')}** |",
        f"| Confidence | {data.get('confidence', 'N/A')} |", "",
    ]
    line_items = data.get("line_items", [])
    if line_items:
        lines += ["## Line Items", "",
                  "| Description | Qty | Unit Price | Total |",
                  "|-------------|-----|------------|-------|"]
        for item in line_items:
            lines.append(f"| {item.get('description','')} | {item.get('quantity','')} | {item.get('unit_price','')} | {item.get('total','')} |")
    lines += ["", f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"]
    output_path.write_text("\n".join(lines))
    print(f"  Report saved -> {output_path}")
    return {"status": "report_generated", "path": str(output_path)}


def flag_for_review(data: dict) -> dict:
    """Log a low-confidence extraction to the Review Queue tab."""
    try:
        client      = _get_sheet_client()
        sheet_id    = os.getenv("GOOGLE_SHEET_ID")
        spreadsheet = client.open_by_key(sheet_id)
        ws          = _get_or_create_tab(spreadsheet, TAB_REVIEW, REVIEW_HEADERS)
        row = [
            datetime.now().isoformat(),
            str(Path(data.get("_image_path", "")).name),
            data.get("confidence")            or "",
            data.get("low_confidence_reason") or "No reason provided",
            data.get("vendor")                or "",
            data.get("total")                 or "",
            "needs_review",
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"  Flagged for review -> Google Sheets: {TAB_REVIEW}")
        print(f"  Reason: {data.get('low_confidence_reason', 'No reason provided')}")
        return {"status": "flagged", "tab": TAB_REVIEW}
    except Exception as e:
        print(f"  Sheets write failed ({e}), falling back to CSV")
        return _csv_fallback(data, "outputs/review_fallback.csv")


def _csv_fallback(data: dict, path: str) -> dict:
    import csv
    output_path = Path(path)
    output_path.parent.mkdir(exist_ok=True)
    file_exists = output_path.exists()
    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    return {"status": "csv_fallback", "path": path}