"""
vision.py — Core vision extraction module.

Sends an image to Claude and returns structured JSON with
extracted fields + a self-reported confidence score.
"""

import anthropic
import base64
import json
import re
from pathlib import Path
from PIL import Image


# ── Constants ───────────────────────────────────────────────────────────────

# Claude will try to return these fields for every image.
# Add or remove fields here as you expand the project.
EXTRACTION_SCHEMA = {
    "vendor":       "Business or person name shown on the document",
    "date":         "Transaction or invoice date (YYYY-MM-DD if possible)",
    "total":        "Final total amount as a float (e.g. 42.99)",
    "subtotal":     "Pre-tax subtotal as a float, or null if not shown",
    "tax":          "Tax amount as a float, or null if not shown",
    "currency":     "3-letter currency code (e.g. USD, EUR)",
    "line_items":   "List of {description, quantity, unit_price, total} dicts",
    "document_type":"One of: receipt, invoice, bill, unknown",
    "confidence":   "Float 0.0–1.0. Your confidence in the extraction accuracy.",
    "low_confidence_reason": "If confidence < 0.8, explain what was unclear. Else null.",
}

SYSTEM_PROMPT = """You are a document extraction specialist.
When given an image of a receipt, invoice, or bill, you extract structured data with high precision.

Rules:
- Always respond with valid JSON only. No markdown fences, no explanation.
- Use null for any field you cannot determine — never guess.
- Set confidence to reflect how clearly readable and complete the document is:
    1.0 = perfectly clear, all fields present
    0.8–0.99 = minor issues (small text, partial cutoff)
    0.5–0.79 = significant issues (blurry, missing key fields)
    below 0.5 = document is unreadable or not a financial document
- If confidence < 0.8, populate low_confidence_reason with a brief explanation."""

EXTRACTION_PROMPT = f"""Extract all available information from this document image.

Return a JSON object with exactly these fields:
{json.dumps(EXTRACTION_SCHEMA, indent=2)}

Respond with JSON only."""


# ── Image helpers ────────────────────────────────────────────────────────────

def load_and_encode_image(image_path: str) -> tuple[str, str]:
    """
    Load an image from disk, validate it, and return (base64_string, media_type).
    Resizes large images to keep API costs down.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Map file extension → MIME type accepted by Claude
    mime_map = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".gif":  "image/gif",
        ".webp": "image/webp",
    }
    media_type = mime_map.get(path.suffix.lower())
    if not media_type:
        raise ValueError(f"Unsupported image type: {path.suffix}. Use JPG, PNG, GIF, or WEBP.")

    # Resize if the image is very large (saves API tokens)
    with Image.open(path) as img:
        max_dim = 1568  # Claude's recommended max dimension
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            # Save resized version to a temp path
            temp_path = path.parent / f"_resized_{path.name}"
            img.save(temp_path)
            path = temp_path
            print(f"  ↳ Resized to fit {max_dim}px max dimension")

    with open(path, "rb") as f:
        encoded = base64.standard_b64encode(f.read()).decode("utf-8")

    return encoded, media_type


# ── Main extraction function ─────────────────────────────────────────────────

def extract_from_image(image_path: str, client: anthropic.Anthropic) -> dict:
    """
    Send an image to Claude and return structured extraction results.

    Returns a dict with all EXTRACTION_SCHEMA fields plus:
      - _image_path: original file path
      - _raw_response: Claude's raw text (useful for debugging)
      - _error: populated only if something went wrong
    """
    result = {
        "_image_path": image_path,
        "_raw_response": None,
        "_error": None,
    }

    try:
        print(f"\n📄 Processing: {image_path}")
        image_data, media_type = load_and_encode_image(image_path)

        # Build the API request
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
        )

        raw_text = message.content[0].text
        result["_raw_response"] = raw_text

        # Parse JSON — strip markdown fences if Claude added them despite instructions
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
        extracted = json.loads(clean)
        result.update(extracted)

        confidence = extracted.get("confidence", 0)
        conf_label = "✅ HIGH" if confidence >= 0.8 else "⚠️  LOW"
        print(f"  Confidence: {conf_label} ({confidence})")
        if extracted.get("low_confidence_reason"):
            print(f"  Reason: {extracted['low_confidence_reason']}")

    except json.JSONDecodeError as e:
        result["_error"] = f"JSON parse error: {e}. Raw: {result['_raw_response']}"
        print(f"  ❌ Failed to parse JSON: {e}")
    except Exception as e:
        result["_error"] = str(e)
        print(f"  ❌ Error: {e}")

    return result