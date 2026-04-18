#!/usr/bin/env python3
"""
Step 07 — Upload episode to YouTube (Shorts)
Usage:
  python3 scripts/07_upload_youtube.py --auth           # One-time OAuth setup
  python3 scripts/07_upload_youtube.py --episode 2
  python3 scripts/07_upload_youtube.py --episode 2 --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("config/.env")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "config/client_secret.json")
TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "config/token.json")
PUBLISH_TIME_UTC = os.getenv("PUBLISH_TIME_UTC", "02:30")  # 08:00 IST = 02:30 UTC

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("❌ Google API libraries not installed.")
    print("   Run: pip install google-api-python-client google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ── YouTube Shorts tags ─────────────────────────────────────────
SERIES_TAGS = [
    "Mahabharat", "Mahabharata", "महाभारत", "Shorts", "YTShorts",
    "HindiShorts", "MahabharatShorts", "Krishna", "Arjun", "Kurukshetra",
    "IndianMythology", "EpicIndia", "HindiContent", "ViralShorts",
    "Bhishma", "Draupadi", "Karna", "Dharma", "महाभारत_शॉर्ट्स"
]


def get_youtube_service():
    """Authenticate and return YouTube API service"""
    creds = None
    token_path = Path(TOKEN_FILE)

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing access token...")
            creds.refresh(Request())
        else:
            if not Path(CLIENT_SECRETS).exists():
                print(f"❌ client_secret.json not found at {CLIENT_SECRETS}")
                print("\n📋 How to get it:")
                print("   1. Go to https://console.cloud.google.com")
                print("   2. Create project → APIs & Services → Enable YouTube Data API v3")
                print("   3. Credentials → Create OAuth 2.0 Client ID → Desktop App")
                print("   4. Download JSON → save as config/client_secret.json")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future use
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())
        print(f"✅ Token saved to {TOKEN_FILE}")

    return build("youtube", "v3", credentials=creds)


def get_publish_datetime() -> str:
    """Get next day's publish time as ISO 8601 string"""
    now_utc = datetime.now(timezone.utc)
    hour, minute = map(int, PUBLISH_TIME_UTC.split(":"))

    # Schedule for tomorrow at publish time
    publish_dt = (now_utc + timedelta(days=1)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return publish_dt.isoformat()


def build_video_metadata(episode_num: int, script: dict) -> dict:
    """Build YouTube video metadata from script"""
    title_hindi = script.get("title_hindi", f"महाभारत शॉर्ट्स EP {episode_num}")
    title_english = script.get("title_english", "")
    script_hindi = script.get("script_hindi", "")

    # Build description
    description = f"""{title_hindi}
{title_english}

{script_hindi[:500]}...

महाभारत की इस अद्भुत कहानी को देखते रहिए। हर रोज़ एक नया एपिसोड।
Watch this epic saga unfold daily — subscribe so you don't miss the next episode!

━━━━━━━━━━━━━━━━━━━━━━━
📱 Series: महाभारत Cinematic Shorts — युग का संघर्ष
🎬 Episode: {episode_num}
━━━━━━━━━━━━━━━━━━━━━━━

#Mahabharat #Shorts #Hindi #महाभारत #Krishna #Arjun #Kurukshetra #IndianMythology
"""

    return {
        "snippet": {
            "title": f"{title_hindi} | महाभारत Shorts EP {episode_num:02d}",
            "description": description,
            "tags": SERIES_TAGS,
            "categoryId": "22",  # People & Blogs
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": "private",       # Upload as private
            "publishAt": get_publish_datetime(),  # Schedule public publish
            "selfDeclaredMadeForKids": False,
        }
    }


def upload_episode(episode_num: int, dry_run: bool = False, verbose: bool = False) -> str:
    ep_dir = Path(OUTPUT_DIR) / f"ep-{episode_num:03d}"
    script_path = ep_dir / "script.json"
    video_path = ep_dir / "video" / "final_watermarked.mp4"
    thumb_path = ep_dir / "thumbnail.jpg"

    # Fallback video filename
    if not video_path.exists():
        video_path = ep_dir / "video" / "final.mp4"

    # Validate files exist
    missing = []
    if not script_path.exists(): missing.append(str(script_path))
    if not video_path.exists():  missing.append(f"{ep_dir}/video/final_watermarked.mp4")
    if not thumb_path.exists():  missing.append(str(thumb_path))

    if missing:
        print(f"❌ Missing files: {', '.join(missing)}")
        print("   Complete all previous steps before uploading.")
        sys.exit(1)

    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    metadata = build_video_metadata(episode_num, script)
    video_size = video_path.stat().st_size // (1024 * 1024)

    print(f"\n📤 Uploading Episode {episode_num} to YouTube...")
    print(f"   Video: {video_path.name} ({video_size}MB)")
    print(f"   Title: {metadata['snippet']['title']}")
    print(f"   Scheduled: {metadata['status']['publishAt']}")

    if dry_run:
        print("\n⚠️  DRY RUN — not actually uploading. Remove --dry-run to upload.")
        return "dry-run-video-id"

    youtube = get_youtube_service()

    # Upload video
    print("   ⏳ Uploading video...", end="", flush=True)
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=5 * 1024 * 1024,  # 5MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=metadata,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"\r   ⏳ Uploading: {pct}%", end="", flush=True)

    video_id = response["id"]
    print(f"\r   ✅ Upload complete! Video ID: {video_id}")
    print(f"   URL: https://www.youtube.com/shorts/{video_id}")

    # Set thumbnail
    if thumb_path.exists():
        print("   🖼️  Setting thumbnail...")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumb_path), mimetype="image/jpeg"),
        ).execute()
        print("   ✅ Thumbnail set")

    # Save upload log
    log_path = ep_dir / "upload_log.json"
    log_data = {
        "episode": episode_num,
        "video_id": video_id,
        "url": f"https://www.youtube.com/shorts/{video_id}",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "scheduled_publish": metadata["status"]["publishAt"],
        "title": metadata["snippet"]["title"],
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)

    print(f"\n✅ Episode {episode_num} upload complete!")
    print(f"   Video ID: {video_id}")
    print(f"   Will go public at: {metadata['status']['publishAt']}")
    print(f"   Upload log: {log_path}")

    return video_id


def main():
    parser = argparse.ArgumentParser(description="Upload episode to YouTube")
    parser.add_argument("--episode", type=int)
    parser.add_argument("--auth", action="store_true", help="Run OAuth setup flow")
    parser.add_argument("--dry-run", action="store_true", help="Test without uploading")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.auth:
        print("🔐 Running YouTube OAuth setup...")
        get_youtube_service()
        print("✅ Authentication complete! Token saved.")
        return

    if not args.episode:
        parser.print_help()
        sys.exit(1)

    upload_episode(args.episode, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
