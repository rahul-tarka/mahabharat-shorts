#!/usr/bin/env python3
"""
Step 04 — Get background music (BGM) for the episode.

Two modes:
  --mode pixabay  Download free royalty-free track from Pixabay (default)
  --mode suno     Generate via Suno API (requires Suno API key)

Usage:
  python3 scripts/04_generate_music.py --episode 2
  python3 scripts/04_generate_music.py --episode 2 --mode suno
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

SUNO_API_KEY = os.getenv("SUNO_API_KEY", "")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# ── Royalty-free tracks (Internet Archive — reliable direct links) ─
# All CC0 / Public Domain — safe for YouTube monetization
PIXABAY_TRACKS = [
    {
        "name": "Epic Cinematic Battle",
        "url": "https://ia800202.us.archive.org/3/items/Kevin_MacLeod_-_Dramatic/Kevin_MacLeod_-_Volatile_Reaction.mp3",
        "mood": "battle"
    },
    {
        "name": "Ancient India Ambient",
        "url": "https://ia800202.us.archive.org/3/items/Kevin_MacLeod_-_Dramatic/Kevin_MacLeod_-_Cipher.mp3",
        "mood": "emotional"
    },
    {
        "name": "Dramatic Orchestral",
        "url": "https://ia800202.us.archive.org/3/items/Kevin_MacLeod_-_Dramatic/Kevin_MacLeod_-_Dark_Times.mp3",
        "mood": "dramatic"
    },
]

DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
}

# ── Suno music prompt ───────────────────────────────────────────
SUNO_PROMPT = (
    "epic orchestral ancient Indian war music, "
    "sitar melody, tabla drums, dramatic strings, "
    "no lyrics, cinematic soundtrack, 60 seconds, "
    "emotional and powerful, Mahabharat theme"
)


def get_episode_mood(episode_num: int) -> str:
    """Determine BGM mood based on episode content"""
    script_path = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "script.json"
    if script_path.exists():
        with open(script_path, encoding="utf-8") as f:
            script = json.load(f)
        emotional_core = script.get("emotional_core", "").lower()
        if any(w in emotional_core for w in ["battle", "war", "fight", "kill"]):
            return "battle"
        if any(w in emotional_core for w in ["grief", "sad", "sorrow", "loss"]):
            return "emotional"
    return "dramatic"


def generate_ffmpeg_fallback(output_path: Path, duration: int = 65) -> Path:
    """Generate ambient brown-noise BGM using ffmpeg (always available on runner)"""
    import subprocess
    print("   ⚠️  Download failed — generating ambient audio via ffmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anoisesrc=d={duration}:c=brown:a=0.3",
        "-ar", "44100", "-ac", "2",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"   ✅ Ambient BGM generated ({duration}s)")
    return output_path


def download_pixabay_track(episode_num: int, verbose: bool = False) -> Path:
    """Download a pre-selected royalty-free track, fallback to ffmpeg generation"""
    mood = get_episode_mood(episode_num)

    track = next(
        (t for t in PIXABAY_TRACKS if t["mood"] == mood),
        PIXABAY_TRACKS[-1]
    )

    print(f"\n🎵 Downloading BGM: '{track['name']}' (mood: {mood})")

    audio_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / "bgm.mp3"

    # Try each track URL, fallback to ffmpeg if all fail
    for t in PIXABAY_TRACKS:
        try:
            response = requests.get(t["url"], headers=DOWNLOAD_HEADERS, timeout=60)
            response.raise_for_status()
            output_path.write_bytes(response.content)
            size_kb = len(response.content) // 1024
            print(f"✅ BGM saved: {output_path} ({size_kb}KB)")
            return output_path
        except Exception as e:
            print(f"   ⚠️  {t['name']} failed: {e}")
            continue

    # All URLs failed — generate with ffmpeg
    return generate_ffmpeg_fallback(output_path)


def generate_suno_track(episode_num: int, verbose: bool = False) -> Path:
    """Generate music via Suno API"""
    if not SUNO_API_KEY:
        print("⚠️  SUNO_API_KEY not set — falling back to Pixabay")
        return download_pixabay_track(episode_num, verbose)

    print(f"\n🎵 Generating BGM via Suno AI...")
    print(f"   Prompt: {SUNO_PROMPT[:80]}...")

    # Suno API — submit generation job
    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": SUNO_PROMPT,
        "make_instrumental": True,
        "model": "chirp-v3-5",
    }

    response = requests.post(
        "https://studio-api.suno.ai/api/generate/v2/",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if response.status_code != 200:
        print(f"⚠️  Suno API error {response.status_code} — falling back to Pixabay")
        return download_pixabay_track(episode_num, verbose)

    task_id = response.json().get("id")
    print(f"   Task ID: {task_id}")
    print("   ⏳ Waiting for generation (up to 2 min)...", end="", flush=True)

    # Poll for completion
    for _ in range(24):  # 24 x 5s = 2 min max
        time.sleep(5)
        print(".", end="", flush=True)

        poll = requests.get(
            f"https://studio-api.suno.ai/api/feed/?ids={task_id}",
            headers=headers,
            timeout=30,
        )
        items = poll.json()
        if items and items[0].get("status") == "complete":
            audio_url = items[0]["audio_url"]
            print(" ✅")
            break
    else:
        print(" ⏰ Timeout — falling back to Pixabay")
        return download_pixabay_track(episode_num, verbose)

    # Download generated audio
    audio_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    audio_response = requests.get(audio_url, timeout=60)
    output_path = audio_dir / "bgm.mp3"
    output_path.write_bytes(audio_response.content)

    print(f"✅ BGM saved: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Get background music")
    parser.add_argument("--episode", type=int, required=True)
    parser.add_argument("--mode", choices=["pixabay", "suno"], default="pixabay",
                        help="pixabay = free download, suno = AI generate")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.mode == "suno":
        generate_suno_track(args.episode, args.verbose)
    else:
        download_pixabay_track(args.episode, args.verbose)

    print(f"\n   Next step: bash scripts/05_assemble_video.sh {args.episode}")


if __name__ == "__main__":
    main()
