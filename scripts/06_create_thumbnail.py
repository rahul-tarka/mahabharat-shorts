#!/usr/bin/env python3
"""
Step 06 — Create YouTube thumbnail (1280x720)
Uses scene_02 as hero image + title overlay + series branding.
Usage:
  python3 scripts/06_create_thumbnail.py --episode 2
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("config/.env")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("❌ Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


# ── Thumbnail config ────────────────────────────────────────────
THUMB_W, THUMB_H = 1280, 720
FONT_PATH = "ffmpeg/fonts/NotoSansDevanagari-Bold.ttf"
FALLBACK_FONT = None  # PIL default if custom font not found


def load_script(episode_num: int) -> dict:
    script_path = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "script.json"
    with open(script_path, encoding="utf-8") as f:
        return json.load(f)


def get_font(size: int) -> ImageFont.FreeTypeFont:
    if Path(FONT_PATH).exists():
        return ImageFont.truetype(FONT_PATH, size)
    # Fallback to default PIL font (no Hindi support but won't crash)
    return ImageFont.load_default()


def create_thumbnail(episode_num: int, verbose: bool = False) -> Path:
    script = load_script(episode_num)
    ep_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}"
    img_dir = ep_dir / "images"

    print(f"\n🖼️  Creating thumbnail for Episode {episode_num}...")

    # ── 1. Load hero image (scene 02, fallback to 01) ──────────
    hero_path = img_dir / "scene_02.jpg"
    if not hero_path.exists():
        hero_path = img_dir / "scene_01.jpg"
    if not hero_path.exists():
        raise FileNotFoundError(f"No scene images found in {img_dir}")

    hero = Image.open(hero_path).convert("RGB")

    # Resize and crop to 16:9 (1280x720)
    # Hero images are 9:16 (1080x1920) — we crop center portion
    hero_w, hero_h = hero.size
    target_ratio = THUMB_W / THUMB_H
    hero_ratio = hero_w / hero_h

    if hero_ratio < target_ratio:
        # Image is taller — crop height
        new_h = int(hero_w / target_ratio)
        top = (hero_h - new_h) // 3  # take upper third (usually face)
        hero = hero.crop((0, top, hero_w, top + new_h))
    else:
        # Image is wider — crop width
        new_w = int(hero_h * target_ratio)
        left = (hero_w - new_w) // 2
        hero = hero.crop((left, 0, left + new_w, hero_h))

    hero = hero.resize((THUMB_W, THUMB_H), Image.LANCZOS)

    if verbose:
        print(f"   Hero image: {hero_path.name} → {THUMB_W}x{THUMB_H}")

    # ── 2. Dark vignette overlay ────────────────────────────────
    canvas = hero.copy()
    draw = ImageDraw.Draw(canvas)

    # Bottom gradient: black overlay for text readability
    for y in range(THUMB_H):
        alpha = int(200 * (y / THUMB_H) ** 1.5)  # exponential fade
        draw.rectangle([(0, y), (THUMB_W, y + 1)],
                       fill=(0, 0, 0, min(alpha, 200)))

    # Left side overlay for text
    overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for x in range(THUMB_W // 2):
        alpha = int(140 * (1 - x / (THUMB_W // 2)))
        ov_draw.rectangle([(x, 0), (x + 1, THUMB_H)],
                           fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # ── 3. Text overlays ────────────────────────────────────────
    title_hindi = script.get("title_hindi", "")
    title_english = script.get("title_english", "")
    ep_num_text = f"EP {episode_num:02d}"

    # Episode number (top left)
    ep_font = get_font(36)
    draw.text((40, 35), ep_num_text, font=ep_font,
              fill=(255, 215, 0), stroke_width=2, stroke_fill=(0, 0, 0))

    # Series name (top right)
    series_font = get_font(22)
    series_text = "महाभारत"
    bbox = draw.textbbox((0, 0), series_text, font=series_font)
    sw = bbox[2] - bbox[0]
    draw.text((THUMB_W - sw - 40, 40), series_text, font=series_font,
              fill=(255, 215, 0, 200), stroke_width=1, stroke_fill=(0, 0, 0))

    # Main Hindi title (bottom area)
    title_font = get_font(56)
    # Wrap long titles
    if len(title_hindi) > 20:
        mid = len(title_hindi) // 2
        space_pos = title_hindi.rfind(" ", 0, mid + 5)
        if space_pos > 0:
            line1 = title_hindi[:space_pos]
            line2 = title_hindi[space_pos + 1:]
        else:
            line1 = title_hindi[:mid]
            line2 = title_hindi[mid:]
    else:
        line1 = title_hindi
        line2 = ""

    draw.text((40, THUMB_H - 200), line1, font=title_font,
              fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    if line2:
        draw.text((40, THUMB_H - 130), line2, font=title_font,
                  fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))

    # English subtitle
    eng_font = get_font(28)
    draw.text((40, THUMB_H - 65), title_english, font=eng_font,
              fill=(200, 200, 200), stroke_width=2, stroke_fill=(0, 0, 0))

    # Gold border accent (top + bottom)
    draw.rectangle([(0, 0), (THUMB_W, 6)], fill=(255, 215, 0))
    draw.rectangle([(0, THUMB_H - 6), (THUMB_W, THUMB_H)], fill=(255, 215, 0))

    # ── 4. Save thumbnail ───────────────────────────────────────
    thumb_path = ep_dir / "thumbnail.jpg"
    canvas.save(thumb_path, "JPEG", quality=95, optimize=True)

    size_kb = thumb_path.stat().st_size // 1024
    print(f"✅ Thumbnail saved: {thumb_path} ({size_kb}KB)")
    print(f"   Title: {title_hindi}")
    print(f"   Next step: python3 scripts/07_upload_youtube.py --episode {episode_num}")

    return thumb_path


def main():
    parser = argparse.ArgumentParser(description="Create YouTube thumbnail")
    parser.add_argument("--episode", type=int, required=True)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    create_thumbnail(args.episode, verbose=args.verbose)


if __name__ == "__main__":
    main()
