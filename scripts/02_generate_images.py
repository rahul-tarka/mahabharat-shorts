#!/usr/bin/env python3
"""
Step 02 — Generate 5 cinematic scene images using Ideogram API
Usage:
  python3 scripts/02_generate_images.py --episode 2
  python3 scripts/02_generate_images.py --episode 2 --verbose
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv("config/.env")

IDEOGRAM_API_KEY = os.getenv("IDEOGRAM_API_KEY")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# ── Style suffix appended to every prompt ──────────────────────
STYLE_SUFFIX = (
    "cinematic hyperrealistic, 9:16 vertical portrait, "
    "dramatic lighting, ancient Indian mythology, "
    "photorealistic, ultra detailed, masterpiece quality, "
    "Zack Snyder color grade, volumetric light"
)

# ── Character seed prompts for visual consistency ───────────────
# These are appended to ensure the same character looks consistent
CHARACTER_SEEDS = {
    "Yudhishthira": "noble Indian warrior king, golden crown, bronze armor, kind eyes, slight beard",
    "Krishna": "dark blue-black skin, peacock feather crown, calm divine expression, yellow dhoti",
    "Arjuna": "tall athletic Indian warrior, silver armor, focused intense eyes, Gandiva bow",
    "Karna": "sun-kissed skin, golden kavach chest armor, proud bearing, steady gaze",
    "Draupadi": "fierce beautiful Indian queen, dark unbound hair, crimson and gold saree",
    "Bhishma": "ancient white-haired warrior, white beard, imposing stature, silver armor",
    "Duryodhana": "powerful muscular Indian prince, dark armor, confident dangerous expression",
    "Drona": "wise elderly guru, white dhoti, calm eyes, wooden staff",
}


def load_script(episode_num: int) -> dict:
    ep_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}"
    script_path = ep_dir / "script.json"
    if not script_path.exists():
        raise FileNotFoundError(
            f"Script not found at {script_path}. "
            f"Run Step 01 first: python3 scripts/01_generate_script.py --episode {episode_num}"
        )
    with open(script_path, encoding="utf-8") as f:
        return json.load(f)


def build_full_prompt(base_prompt: str, characters: list[str]) -> str:
    """Append style suffix and character seeds to base prompt"""
    seed_additions = []
    for char in characters:
        if char in CHARACTER_SEEDS:
            seed_additions.append(CHARACTER_SEEDS[char])

    full_prompt = base_prompt
    if seed_additions:
        full_prompt += ", " + ", ".join(seed_additions)
    full_prompt += ", " + STYLE_SUFFIX
    return full_prompt


def generate_image(prompt: str, scene_num: int, verbose: bool = False) -> bytes:
    """Call Ideogram API and return image bytes"""
    headers = {
        "Api-Key": IDEOGRAM_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "image_request": {
            "prompt": prompt,
            "aspect_ratio": "ASPECT_9_16",   # 9:16 for Shorts
            "model": "V_2",
            "magic_prompt_option": "OFF",     # Use our prompt as-is
            "style_type": "REALISTIC",
        }
    }

    if verbose:
        print(f"   📡 Calling Ideogram API for Scene {scene_num}...")

    response = requests.post(
        "https://api.ideogram.ai/generate",
        headers=headers,
        json=payload,
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Ideogram API error {response.status_code}: {response.text}"
        )

    data = response.json()
    image_url = data["data"][0]["url"]

    # Download image from URL
    img_response = requests.get(image_url, timeout=60)
    img_response.raise_for_status()
    return img_response.content


def generate_all_images(episode_num: int, verbose: bool = False):
    script = load_script(episode_num)
    ep_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "images"
    ep_dir.mkdir(parents=True, exist_ok=True)

    image_prompts = script.get("image_prompts", [])
    characters = script.get("character_focus", "").split(",") if isinstance(
        script.get("character_focus"), str
    ) else []

    # Extract characters from episode plan if available
    ep_characters = [c.strip() for c in characters]

    print(f"\n🖼️  Generating {len(image_prompts)} scene images for Episode {episode_num}...")

    results = []
    for i, item in enumerate(image_prompts, 1):
        scene_num = item.get("scene", i)
        base_prompt = item.get("prompt", "")

        full_prompt = build_full_prompt(base_prompt, ep_characters)

        if verbose:
            print(f"\n   Scene {scene_num} prompt preview:")
            print(f"   {full_prompt[:120]}...")

        try:
            print(f"   ⏳ Scene {scene_num}/{len(image_prompts)} generating...", end="", flush=True)
            image_bytes = generate_image(full_prompt, scene_num, verbose=verbose)

            output_path = ep_dir / f"scene_{scene_num:02d}.jpg"
            output_path.write_bytes(image_bytes)
            print(f" ✅ saved ({len(image_bytes)//1024}KB)")
            results.append(str(output_path))

            # Respect rate limits — Ideogram allows ~5 req/min on free tier
            if i < len(image_prompts):
                time.sleep(13)  # ~4.5 req/min to stay safe

        except Exception as e:
            print(f" ❌ Failed: {e}")
            results.append(None)

    # Save image manifest
    manifest = {
        "episode": episode_num,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "images": [
            {"scene": i + 1, "path": p} for i, p in enumerate(results)
        ]
    }
    manifest_path = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "image_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    success = sum(1 for r in results if r is not None)
    print(f"\n✅ {success}/{len(image_prompts)} images generated")
    print(f"   Saved to: output/ep-{episode_num:03d}/images/")
    print(f"   Next step: python3 scripts/03_generate_voice.py --episode {episode_num}")


def main():
    parser = argparse.ArgumentParser(description="Generate scene images")
    parser.add_argument("--episode", type=int, required=True)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if not IDEOGRAM_API_KEY:
        print("❌ IDEOGRAM_API_KEY not set. Check config/.env")
        sys.exit(1)

    generate_all_images(args.episode, verbose=args.verbose)


if __name__ == "__main__":
    main()
