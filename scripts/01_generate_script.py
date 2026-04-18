#!/usr/bin/env python3
"""
Step 01 — Generate episode script using Google Gemini API
Usage:
  python3 scripts/01_generate_script.py --episode 1
  python3 scripts/01_generate_script.py --test
"""

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("config/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
MODEL = "gemini-2.0-flash"

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Run: pip install google-genai")
    sys.exit(1)


def load_episode_plan(episode_num: int) -> dict:
    with open("config/episode_plan.json") as f:
        plan = json.load(f)
    for ep in plan["episodes"]:
        if ep["episode"] == episode_num:
            return ep
    raise ValueError(f"Episode {episode_num} not found")


def load_system_prompt() -> str:
    return Path("prompts/script_system_prompt.txt").read_text()


def build_user_message(ep: dict) -> str:
    return f"""Generate Episode {ep['episode']} of the Mahabharat Shorts series.

EPISODE DETAILS:
- Episode Number: {ep['episode']}
- Title Hint: {ep['title_hint']}
- Character Focus: {ep['character_focus']}
- Story Arc: {ep['arc']}
- Emotional Core: {ep['emotional_core']}
- Cliffhanger Setup: {ep['cliffhanger_setup']}

Write the complete episode. Make it cinematic, emotional, and addictive.
The cliffhanger MUST directly set up the next episode.
"""


def generate_script(episode_num: int, verbose: bool = False) -> dict:
    ep = load_episode_plan(episode_num)
    system_prompt = load_system_prompt()
    user_message = build_user_message(ep)

    client = genai.Client(api_key=GEMINI_API_KEY)

    if verbose:
        print(f"📖 Episode {episode_num} | Character: {ep['character_focus']}")
        print(f"🤖 Calling Gemini API ({MODEL})...")

    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.9,
            max_output_tokens=2000,
        ),
        contents=user_message,
    )

    raw = response.text.strip()

    if verbose:
        print("✅ Gemini responded")

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


def save_script(script_data: dict, episode_num: int) -> Path:
    ep_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}"
    ep_dir.mkdir(parents=True, exist_ok=True)
    output_path = ep_dir / "script.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    return output_path


def print_preview(script_data: dict):
    print("\n" + "═" * 55)
    print(f"🎬 {script_data['title_hindi']}")
    print(f"   {script_data['title_english']}")
    print("═" * 55)
    print("\n📜 SCRIPT PREVIEW:")
    print(script_data['script_hindi'][:300] + "...")
    print("\n⚡ CLIFFHANGER:")
    print(f"   {script_data['cliffhanger_hindi']}")
    print("═" * 55)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=int)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not set in config/.env")
        sys.exit(1)

    client = genai.Client(api_key=GEMINI_API_KEY)

    if args.test:
        print(f"🔌 Testing Gemini API ({MODEL})...")
        response = client.models.generate_content(model=MODEL, contents="Say: OK")
        print(f"✅ Gemini connected: {response.text.strip()}")
        return

    if not args.episode:
        parser.print_help()
        sys.exit(1)

    print(f"\n🚀 Generating script for Episode {args.episode}...")
    script_data = generate_script(args.episode, verbose=args.verbose)
    path = save_script(script_data, args.episode)
    print_preview(script_data)
    print(f"\n✅ Saved: {path}")


if __name__ == "__main__":
    main()
