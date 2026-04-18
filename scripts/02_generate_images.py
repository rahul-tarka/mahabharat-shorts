#!/usr/bin/env python3
"""
Step 02 — Generate 5 cinematic scene images using Pollinations.ai (free, no API key)
Usage:
  python3 scripts/02_generate_images.py --episode 2
  python3 scripts/02_generate_images.py --episode 2 --verbose
"""

import argparse
import json
import os
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv("config/.env")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# ── Style suffix appended to every prompt ──────────────────────
STYLE_SUFFIX = (
    "cinematic hyperrealistic, 9:16 vertical portrait, "
    "dramatic lighting, ancient Indian mythology, "
    "photorealistic, ultra detailed, masterpiece quality, "
    "Zack Snyder color grade, volumetric light"
)

# ── Character seed prompts for visual consistency ───────────────
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

# Pollinations.ai endpoint
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


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
    seed_additions = [CHARACTER_SEEDS[c] for c in characters if c in CHARACTER_SEEDS]
    full_prompt = base_prompt
    if seed_additions:
        full_prompt += ", " + ", ".join(seed_additions)
    full_prompt += ", " + STYLE_SUFFIX
    return full_prompt


def generate_image(prompt: str, scene_num: int, episode_num: int, verbose: bool = False) -> bytes:
    """Call Pollinations.ai and return image bytes. No API key required."""
    encoded_prompt = urllib.parse.quote(prompt)
    # Use episode+scene as seed for reproducibility; nologo removes watermark
    url = (
        POLLINATIONS_URL.format(prompt=encoded_prompt)
        + f"?width=1080&height=1920&model=flux&nologo=true&seed={episode_num * 100 + scene_num}"
    )

    if verbose:
        print(f"   URL: {url[:100]}...")

    response = requests.get(url, timeout=180)
    response.raise_for_status()
    return response.content


def generate_all_images(episode_num: int, verbose: bool = False):
    script = load_script(episode_num)
    ep_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "images"
    ep_dir.mkdir(parents=True, exist_ok=True)

    image_prompts = script.get("image_prompts", [])
    character_focus = script.get("character_focus", "")
    ep_characters = [c.strip() for c in character_focus.split(",") if c.strip()]

    print(f"\n🖼️  Generating {len(image_prompts)} scene images for Episode {episode_num}...")
    print("   Provider: Pollinations.ai (free, no API key)")

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
            image_bytes = generate_image(full_prompt, scene_num, episode_num, verbose=verbose)

            output_path = ep_dir / f"scene_{scene_num:02d}.jpg"
            output_path.write_bytes(image_bytes)
            print(f" ✅ saved ({len(image_bytes)//1024}KB)")
            results.append(str(output_path))

            # Pollinations recommends ~5s between requests on free tier
            if i < len(image_prompts):
                time.sleep(6)

        except Exception as e:
            print(f" ❌ Failed: {e}")
            results.append(None)

    # Save image manifest
    manifest = {
        "episode": episode_num,
        "generated_at": datetime.now().isoformat(),
        "provider": "pollinations.ai",
        "images": [{"scene": i + 1, "path": p} for i, p in enumerate(results)],
    }
    manifest_path = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "image_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    success = sum(1 for r in results if r is not None)
    print(f"\n✅ {success}/{len(image_prompts)} images generated")
    print(f"   Saved to: output/ep-{episode_num:03d}/images/")
    print(f"   Next step: python3 scripts/03_generate_voice.py --episode {episode_num}")


def main():
    parser = argparse.ArgumentParser(description="Generate scene images via Pollinations.ai (free)")
    parser.add_argument("--episode", type=int, required=True)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    generate_all_images(args.episode, verbose=args.verbose)


if __name__ == "__main__":
    main()
