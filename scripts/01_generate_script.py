#!/usr/bin/env python3
"""
Step 01 — Generate episode script using Claude API
Usage:
  python3 scripts/01_generate_script.py --episode 2
  python3 scripts/01_generate_script.py --episode 2 --verbose
  python3 scripts/01_generate_script.py --test
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# ── Load environment ────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv("config/.env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# ── Anthropic client ────────────────────────────────────────────
try:
    import anthropic
except ImportError:
    print("❌ anthropic not installed. Run: pip install anthropic")
    sys.exit(1)


def load_episode_plan(episode_num: int) -> dict:
    """Load episode details from episode_plan.json"""
    plan_path = Path("config/episode_plan.json")
    if not plan_path.exists():
        raise FileNotFoundError("config/episode_plan.json not found")

    with open(plan_path) as f:
        plan = json.load(f)

    for ep in plan["episodes"]:
        if ep["episode"] == episode_num:
            return ep

    raise ValueError(f"Episode {episode_num} not found in episode_plan.json")


def load_system_prompt() -> str:
    """Load the Claude system prompt template"""
    prompt_path = Path("prompts/script_system_prompt.txt")
    if not prompt_path.exists():
        raise FileNotFoundError("prompts/script_system_prompt.txt not found")
    return prompt_path.read_text()


def build_user_message(ep: dict) -> str:
    """Build the user message for Claude from episode plan"""
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
    """Call Claude API and return parsed script JSON"""

    ep = load_episode_plan(episode_num)
    system_prompt = load_system_prompt()
    user_message = build_user_message(ep)

    if verbose:
        print(f"📖 Loaded episode plan for Episode {episode_num}")
        print(f"   Character: {ep['character_focus']}")
        print(f"   Arc: {ep['arc']}")
        print("🤖 Calling Claude API...")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",  # Always use Sonnet 4
        max_tokens=2000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    raw_response = message.content[0].text

    if verbose:
        print("✅ Claude responded")
        print(f"   Input tokens:  {message.usage.input_tokens}")
        print(f"   Output tokens: {message.usage.output_tokens}")

    # Parse JSON response
    try:
        script_data = json.loads(raw_response)
    except json.JSONDecodeError:
        # Claude sometimes adds markdown fences — strip them
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        script_data = json.loads(cleaned.strip())

    return script_data


def save_script(script_data: dict, episode_num: int) -> Path:
    """Save script JSON to output directory"""
    ep_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}"
    ep_dir.mkdir(parents=True, exist_ok=True)

    output_path = ep_dir / "script.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    return output_path


def print_script_preview(script_data: dict):
    """Pretty-print script preview to terminal"""
    print("\n" + "═" * 60)
    print(f"🎬 {script_data['title_hindi']}")
    print(f"   {script_data['title_english']}")
    print("═" * 60)
    print("\n📜 SCRIPT PREVIEW:")
    print(script_data['script_hindi'][:300] + "...")
    print("\n⚡ CLIFFHANGER:")
    print(f"   {script_data['cliffhanger_hindi']}")
    print(f"   ({script_data['cliffhanger_english']})")
    print("\n🖼️  IMAGE PROMPTS: 5 generated")
    print("🎙️  SUBTITLES:", len(script_data.get('subtitles', [])), "lines")
    print("═" * 60)


def main():
    parser = argparse.ArgumentParser(description="Generate Mahabharat episode script")
    parser.add_argument("--episode", type=int, help="Episode number")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test", action="store_true", help="Test API connection")
    args = parser.parse_args()

    # ── Test mode ─────────────────────────────────────────────
    if args.test:
        print("🔌 Testing Claude API connection...")
        if not ANTHROPIC_API_KEY:
            print("❌ ANTHROPIC_API_KEY not set in config/.env")
            sys.exit(1)
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say: OK"}]
        )
        print("✅ Claude API connected. Episode 1 script generated.")
        return

    # ── Generate mode ──────────────────────────────────────────
    if not args.episode:
        parser.print_help()
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not set. Check config/.env")
        sys.exit(1)

    print(f"\n🚀 Generating script for Episode {args.episode}...")

    try:
        script_data = generate_script(args.episode, verbose=args.verbose)
        output_path = save_script(script_data, args.episode)
        print_script_preview(script_data)
        print(f"\n✅ Script saved to: {output_path}")
        print(f"   Next step: python3 scripts/02_generate_images.py --episode {args.episode}")

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
