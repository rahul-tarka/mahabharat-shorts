#!/usr/bin/env python3
"""
Step 01 — Generate episode script using Groq API (free, fast)
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
MODEL = "llama-3.3-70b-versatile"

try:
    from groq import Groq
except ImportError:
    print("❌ Run: pip install groq")
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

    client = Groq(api_key=GROQ_API_KEY)

    if verbose:
        print(f"📖 Episode {episode_num} | Character: {ep['character_focus']}")
        print(f"🤖 Calling Groq API ({MODEL})...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.9,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()

    if verbose:
        print("✅ Groq responded")

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

    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not set in config/.env")
        sys.exit(1)

    client = Groq(api_key=GROQ_API_KEY)

    if args.test:
        print(f"🔌 Testing Groq API ({MODEL})...")
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say: OK"}],
            max_tokens=5,
        )
        print(f"✅ Groq connected: {r.choices[0].message.content.strip()}")
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
