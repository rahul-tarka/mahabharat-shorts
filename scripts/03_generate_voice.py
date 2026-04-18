#!/usr/bin/env python3
"""
Step 03 — Generate Hindi voiceover using Microsoft Edge TTS (free, no API key)
Usage:
  python3 scripts/03_generate_voice.py --episode 2
  python3 scripts/03_generate_voice.py --episode 2 --verbose
  python3 scripts/03_generate_voice.py --list-voices
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("config/.env")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

try:
    import edge_tts
except ImportError:
    print("❌ Run: pip install edge-tts")
    sys.exit(1)

# ── Hindi voice — deep male narrator ───────────────────────────
# Available Hindi voices:
#   hi-IN-MadhurNeural     — male, deep and dramatic (best for narration)
#   hi-IN-SwaraNeural      — female
EDGE_TTS_VOICE = "hi-IN-MadhurNeural"

# Speaking rate and pitch adjustments (SSML-compatible)
RATE  = "+5%"   # slightly faster than default
PITCH = "-8Hz"  # slightly lower pitch for gravitas


def load_script(episode_num: int) -> dict:
    script_path = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "script.json"
    if not script_path.exists():
        raise FileNotFoundError(
            f"Script not found. Run Step 01 first: "
            f"python3 scripts/01_generate_script.py --episode {episode_num}"
        )
    with open(script_path, encoding="utf-8") as f:
        return json.load(f)


def prepare_tts_text(script_data: dict) -> str:
    """
    Clean up Hindi script for TTS.
    Remove stage directions in [] and (), keep only spoken lines.
    """
    raw = script_data.get("script_hindi", "")

    # Remove stage directions
    text = re.sub(r"\[.*?\]", "", raw)   # Remove [brackets]
    text = re.sub(r"\(.*?\)", "", text)  # Remove (parentheses)

    # Clean up whitespace
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

    return text


async def _generate_async(text: str, output_path: str, verbose: bool = False):
    """Run edge-tts generation asynchronously."""
    communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE, rate=RATE, pitch=PITCH)

    if verbose:
        print(f"   Voice: {EDGE_TTS_VOICE}")
        print(f"   Rate: {RATE}  Pitch: {PITCH}")
        print(f"   Text preview: {text[:200]}")

    await communicate.save(output_path)


async def _list_hindi_voices():
    voices = await edge_tts.list_voices()
    hindi = [v for v in voices if v["Locale"].startswith("hi-")]
    print("\n🎤 Available Hindi voices (edge-tts):")
    for v in hindi:
        print(f"   {v['ShortName']:35s}  Gender: {v['Gender']}")


def generate_voiceover(episode_num: int, verbose: bool = False) -> Path:
    script_data = load_script(episode_num)
    tts_text = prepare_tts_text(script_data)

    char_count = len(tts_text)
    print(f"\n🎙️  Generating Hindi voiceover for Episode {episode_num}...")
    print(f"   Provider : Microsoft Edge TTS (free, no API key)")
    print(f"   Voice    : {EDGE_TTS_VOICE}")
    print(f"   Characters: {char_count}")

    audio_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    output_path = audio_dir / "voiceover.mp3"

    asyncio.run(_generate_async(tts_text, str(output_path), verbose=verbose))

    size_kb = output_path.stat().st_size // 1024
    print(f"✅ Voiceover saved: {output_path} ({size_kb}KB)")
    print(f"   Next step: python3 scripts/04_generate_music.py --episode {episode_num}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate Hindi voiceover via Edge TTS (free)")
    parser.add_argument("--episode", type=int)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available Hindi voices")
    args = parser.parse_args()

    if args.list_voices:
        asyncio.run(_list_hindi_voices())
        return

    if not args.episode:
        parser.print_help()
        sys.exit(1)

    generate_voiceover(args.episode, verbose=args.verbose)


if __name__ == "__main__":
    main()
