"""
agent.py — The full LangChain reasoning agent (Day 2).

Orchestrates the full pipeline:
  1. Vision extraction (utils/vision.py)
  2. Confidence-based routing decision
  3. Tool execution (utils/tools.py)

Usage:
    python agent.py --image images/test/receipt.jpg
    python agent.py --folder images/test/
"""

import argparse
import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from utils.vision import extract_from_image
from utils.tools import save_to_sheet, generate_report, flag_for_review

load_dotenv()

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

CONFIDENCE_THRESHOLD = 0.8


# ── Routing logic ─────────────────────────────────────────────────────────────

def route(extraction: dict) -> str:
    """Decide which action to take based on confidence score."""
    confidence = extraction.get("confidence", 0)
    if confidence >= CONFIDENCE_THRESHOLD:
        return "high_confidence"
    return "low_confidence"


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(image_path: str, vision_client: anthropic.Anthropic):
    """Full pipeline for one image: vision → route → tools."""
    print(f"\n{'='*55}")
    print(f"🖼️  Image: {image_path}")
    print(f"{'='*55}")

    # Step 1: Vision extraction
    extraction = extract_from_image(image_path, vision_client)

    if extraction.get("_error"):
        print(f"❌ Vision extraction failed: {extraction['_error']}")
        return

    confidence = extraction.get("confidence", 0)

    # Step 2: Route based on confidence
    decision = route(extraction)
    print(f"\n🤖 Agent decision: confidence={confidence} → {decision}")

    if decision == "high_confidence":
        print("  → Saving data and generating report...")
        save_to_sheet(extraction)
        generate_report(extraction)
    else:
        print("  → Flagging for human review...")
        flag_for_review(extraction)

    print("\n✅ Done.")


# ── LangChain agent setup (optional, for future use) ─────────────────────────
# Kept here so Day 3 can optionally plug in a real agent loop.
# For now, the routing logic above handles everything we need.

def build_agent():
    """
    Placeholder for a full LangChain AgentExecutor.
    Uncomment and use once LangChain version issues are resolved.
    """
    raise NotImplementedError("Use run_pipeline() for now.")


def main():
    parser = argparse.ArgumentParser(description="Vision + Agentic Reasoning Agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image",  help="Path to a single image")
    group.add_argument("--folder", help="Path to a folder of images")
    args = parser.parse_args()

    vision_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    if args.image:
        run_pipeline(args.image, vision_client)
    else:
        folder = Path(args.folder)
        images = [f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        if not images:
            print(f"No images found in {args.folder}")
            return
        print(f"\n🗂️  Processing {len(images)} image(s)...")
        for img in sorted(images):
            run_pipeline(str(img), vision_client)


if __name__ == "__main__":
    main()