"""
main.py — Day 1 entry point.

Run a single image or a folder of images through the vision extractor
and print the results. No agent logic yet — just testing the vision layer.

Usage:
    python main.py --image images/test/receipt.jpg
    python main.py --folder images/test/
    python main.py --image images/test/receipt.jpg --save
"""

import argparse
import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from utils.vision import extract_from_image

load_dotenv()

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. "
            "Copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(api_key=api_key)


def process_single(image_path: str, client: anthropic.Anthropic, save: bool = False) -> dict:
    result = extract_from_image(image_path, client)

    print("\n── Extracted Data ──────────────────────────────────")
    # Print cleanly, skip internal debug fields
    display = {k: v for k, v in result.items() if not k.startswith("_")}
    print(json.dumps(display, indent=2))

    if result.get("_error"):
        print(f"\n⚠️  Error occurred: {result['_error']}")

    if save:
        out_path = Path("outputs") / (Path(image_path).stem + "_extracted.json")
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Saved to {out_path}")

    return result


def process_folder(folder_path: str, client: anthropic.Anthropic, save: bool = False) -> list[dict]:
    folder = Path(folder_path)
    images = [f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not images:
        print(f"No supported images found in {folder_path}")
        return []

    print(f"\n🗂️  Found {len(images)} image(s) in {folder_path}")
    results = []
    for img in sorted(images):
        result = process_single(str(img), client, save=save)
        results.append(result)

    # Summary
    high_conf = sum(1 for r in results if (r.get("confidence") or 0) >= 0.8)
    low_conf = len(results) - high_conf
    print(f"\n── Summary ──────────────────────────────────────────")
    print(f"  Total processed : {len(results)}")
    print(f"  High confidence : {high_conf}")
    print(f"  Needs review    : {low_conf}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Vision extraction agent — Day 1")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image",  help="Path to a single image file")
    group.add_argument("--folder", help="Path to a folder of images")
    parser.add_argument("--save", action="store_true", help="Save results to outputs/")
    args = parser.parse_args()

    client = get_client()

    if args.image:
        process_single(args.image, client, save=args.save)
    else:
        process_folder(args.folder, client, save=args.save)


if __name__ == "__main__":
    main()