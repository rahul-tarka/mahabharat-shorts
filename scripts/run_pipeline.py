#!/usr/bin/env python3
"""
run_pipeline.py — Master runner for the Mahabharat Shorts pipeline.
Runs all 7 steps in sequence for a given episode.

Usage:
  python3 scripts/run_pipeline.py --episode 2
  python3 scripts/run_pipeline.py --next          # Auto-pick next pending episode
  python3 scripts/run_pipeline.py --episode 2 --skip-upload
  python3 scripts/run_pipeline.py --episode 2 --from-step 3
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("config/.env")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
LOG_DIR = "logs"


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "ℹ️ ", "OK": "✅", "ERR": "❌", "WARN": "⚠️ "}.get(level, "")
    line = f"[{ts}] {prefix} {msg}"
    print(line)
    # Also write to log file
    Path(LOG_DIR).mkdir(exist_ok=True)
    with open(f"{LOG_DIR}/pipeline.log", "a") as f:
        f.write(line + "\n")


def get_next_pending_episode() -> int:
    plan_path = Path("config/episode_plan.json")
    with open(plan_path) as f:
        plan = json.load(f)
    for ep in plan["episodes"]:
        if ep.get("status") == "pending":
            return ep["episode"]
    raise ValueError("No pending episodes found in episode_plan.json")


def mark_episode_done(episode_num: int):
    plan_path = Path("config/episode_plan.json")
    with open(plan_path) as f:
        plan = json.load(f)
    for ep in plan["episodes"]:
        if ep["episode"] == episode_num:
            ep["status"] = "done"
    with open(plan_path, "w") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def run_step(cmd: list[str], step_name: str) -> bool:
    log(f"Starting: {step_name}")
    start = time.time()

    result = subprocess.run(
        cmd,
        capture_output=False,  # Let output stream to terminal
        text=True,
    )

    elapsed = int(time.time() - start)
    if result.returncode == 0:
        log(f"Completed: {step_name} ({elapsed}s)", "OK")
        return True
    else:
        log(f"FAILED: {step_name} (exit code {result.returncode})", "ERR")
        return False


def run_pipeline(episode_num: int, skip_upload: bool = False, from_step: int = 1):
    start_time = time.time()

    print("\n" + "═" * 60)
    print(f"🚀 MAHABHARAT SHORTS PIPELINE — Episode {episode_num}")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if from_step > 1:
        print(f"   Resuming from Step {from_step}")
    print("═" * 60 + "\n")

    steps = [
        # (step_number, name, command)
        (1, "Script generation",   ["python3", "scripts/01_generate_script.py", "--episode", str(episode_num)]),
        (2, "Image generation",    ["python3", "scripts/02_generate_images.py", "--episode", str(episode_num)]),
        (3, "Voice generation",    ["python3", "scripts/03_generate_voice.py",  "--episode", str(episode_num)]),
        (4, "Music download",      ["python3", "scripts/04_generate_music.py",  "--episode", str(episode_num)]),
        (5, "Video assembly",      ["bash",    "scripts/05_assemble_video.sh",  str(episode_num)]),
        (6, "Thumbnail creation",  ["python3", "scripts/06_create_thumbnail.py","--episode", str(episode_num)]),
        (7, "YouTube upload",      ["python3", "scripts/07_upload_youtube.py",  "--episode", str(episode_num)]),
    ]

    failed_steps = []

    for step_num, step_name, cmd in steps:
        # Skip steps before from_step
        if step_num < from_step:
            log(f"Skipping Step {step_num}: {step_name} (--from-step {from_step})", "WARN")
            continue

        # Skip upload if requested
        if step_num == 7 and skip_upload:
            log("Skipping Step 7: YouTube upload (--skip-upload)", "WARN")
            continue

        print(f"\n{'─'*50}")
        print(f"Step {step_num}/7 — {step_name}")
        print(f"{'─'*50}")

        success = run_step(cmd, step_name)
        if not success:
            failed_steps.append((step_num, step_name))
            log(f"Pipeline stopped at Step {step_num}. Fix the error and resume with:", "ERR")
            log(f"  python3 scripts/run_pipeline.py --episode {episode_num} --from-step {step_num}")
            break

    # ── Summary ────────────────────────────────────────────────
    elapsed = int(time.time() - start_time)
    minutes, seconds = divmod(elapsed, 60)

    print("\n" + "═" * 60)
    if not failed_steps:
        print(f"✅ PIPELINE COMPLETE — Episode {episode_num}")
        print(f"   Total time: {minutes}m {seconds}s")
        print(f"   Output: output/ep-{episode_num:03d}/")
        print("═" * 60)

        # Mark episode as done in plan
        mark_episode_done(episode_num)
        log(f"Episode {episode_num} marked as done in episode_plan.json", "OK")
    else:
        print(f"❌ PIPELINE FAILED at Step {failed_steps[0][0]}: {failed_steps[0][1]}")
        print(f"   Time elapsed before failure: {minutes}m {seconds}s")
        print(f"\n   To resume: python3 scripts/run_pipeline.py --episode {episode_num} --from-step {failed_steps[0][0]}")
        print("═" * 60)
        sys.exit(1)  # Non-zero exit so GitHub Actions marks the job as failed


def main():
    parser = argparse.ArgumentParser(description="Run full Mahabharat Shorts pipeline")
    parser.add_argument("--episode", type=int, help="Episode number")
    parser.add_argument("--next", action="store_true",
                        help="Auto-pick next pending episode from episode_plan.json")
    parser.add_argument("--skip-upload", action="store_true",
                        help="Skip YouTube upload (for testing)")
    parser.add_argument("--from-step", type=int, default=1,
                        help="Resume from step N (1-7)")
    args = parser.parse_args()

    if args.next:
        episode_num = get_next_pending_episode()
        print(f"📋 Next pending episode: {episode_num}")
    elif args.episode:
        episode_num = args.episode
    else:
        parser.print_help()
        sys.exit(1)

    run_pipeline(
        episode_num=episode_num,
        skip_upload=args.skip_upload,
        from_step=args.from_step,
    )


if __name__ == "__main__":
    main()
