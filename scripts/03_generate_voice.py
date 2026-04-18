#!/usr/bin/env python3
"""
Step 03 — Generate Hindi voiceover using ElevenLabs API
Usage:
  python3 scripts/03_generate_voice.py --episode 2
  python3 scripts/03_generate_voice.py --episode 2 --verbose
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv("config/.env")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# ── Voice settings for epic narration ──────────────────────────
VOICE_SETTINGS = {
    "stability": 0.65,        # 0-1: lower = more expressive
    "similarity_boost": 0.80, # 0-1: higher = closer to original voice
    "style": 0.45,            # 0-1: style exaggeration
    "use_speaker_boost": True
}

# ── Model — use Multilingual v2 for best Hindi quality ─────────
ELEVENLABS_MODEL = "eleven_multilingual_v2"


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
    Remove stage directions in [], keep only spoken lines.
    """
    raw = script_data.get("script_hindi", "")

    # Remove stage directions like [SCENE: ...] or (द्रौपदी की आवाज़)
    import re
    text = re.sub(r"\[.*?\]", "", raw)        # Remove [brackets]
    text = re.sub(r"\(.*?\)", "", text)        # Remove (parentheses) — stage directions

    # Clean up whitespace
    text = "\n".join(
        line.strip() for line in text.splitlines() if line.strip()
    )

    # Add pauses via SSML-like markers ElevenLabs understands
    # <break time="0.5s"/> works in ElevenLabs
    text = text.replace("...", '<break time="0.8s"/>')
    text = text.replace("—", '<break time="0.4s"/>')

    return text


def generate_voiceover(episode_num: int, verbose: bool = False) -> Path:
    script_data = load_script(episode_num)
    tts_text = prepare_tts_text(script_data)

    if verbose:
        print(f"\n📝 TTS text preview:")
        print(tts_text[:300])
        print(f"\n   Characters: {len(tts_text)}")

    print(f"\n🎙️  Generating Hindi voiceover for Episode {episode_num}...")
    print(f"   Voice ID: {ELEVENLABS_VOICE_ID}")
    print(f"   Model: {ELEVENLABS_MODEL}")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": tts_text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": VOICE_SETTINGS,
        "output_format": "mp3_44100_128",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs API error {response.status_code}: {response.text[:200]}"
        )

    # Save audio
    audio_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    output_path = audio_dir / "voiceover.mp3"
    output_path.write_bytes(response.content)

    size_kb = len(response.content) // 1024
    print(f"✅ Voiceover saved: {output_path} ({size_kb}KB)")
    print(f"   Next step: python3 scripts/04_generate_music.py --episode {episode_num}")

    return output_path


def list_available_voices():
    """Helper: list all voices in your ElevenLabs account"""
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
    voices = response.json().get("voices", [])
    print("\n🎤 Available voices in your account:")
    for v in voices:
        print(f"   {v['name']:30s}  ID: {v['voice_id']}")


def main():
    parser = argparse.ArgumentParser(description="Generate Hindi voiceover")
    parser.add_argument("--episode", type=int)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available ElevenLabs voices")
    args = parser.parse_args()

    if not ELEVENLABS_API_KEY:
        print("❌ ELEVENLABS_API_KEY not set. Check config/.env")
        sys.exit(1)

    if args.list_voices:
        list_available_voices()
        return

    if not args.episode:
        parser.print_help()
        sys.exit(1)

    if not ELEVENLABS_VOICE_ID:
        print("❌ ELEVENLABS_VOICE_ID not set.")
        print("   Run with --list-voices to find your voice ID")
        sys.exit(1)

    generate_voiceover(args.episode, verbose=args.verbose)


if __name__ == "__main__":
    main()
