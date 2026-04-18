# Mahabharat Shorts — Daily Auto-Publishing Pipeline

> Script → Scene Images → Voice → Music → Video → Thumbnail → YouTube Upload
> Fully automated. Runs daily via GitHub Actions. Zero manual work after setup.

---

## Project Status

| Item | State |
|---|---|
| Episodes defined | 10 of 30 planned |
| Episodes completed | 1 (Episode 1 — Kurukshetra dawn) |
| Episodes pending | 9 (Episodes 2–10) |
| Automation | GitHub Actions — daily at 2:00 AM UTC (7:30 AM IST) |

---

## Project Structure

```
mahabharat-shorts/
├── config/
│   ├── .env.example          ← Copy to .env, fill API keys
│   └── episode_plan.json     ← Episode schedule (arc, character, theme, status)
├── scripts/
│   ├── 01_generate_script.py    ← Gemini API → Script JSON
│   ├── 02_generate_images.py    ← Ideogram API → 5 scene images
│   ├── 03_generate_voice.py     ← ElevenLabs API → voiceover.mp3
│   ├── 04_generate_music.py     ← Suno / Pixabay BGM
│   ├── 05_assemble_video.sh     ← FFmpeg → final 1080x1920 Short
│   ├── 06_create_thumbnail.py   ← PIL → thumbnail 1280x720
│   ├── 07_upload_youtube.py     ← YouTube Data API v3 → upload
│   └── run_pipeline.py          ← Master runner (calls all steps in sequence)
├── prompts/
│   └── script_system_prompt.txt ← Gemini system prompt template
├── ffmpeg/
│   └── fonts/                   ← NotoSansDevanagari-Bold.ttf (downloaded by setup_mac.sh)
├── n8n/
│   └── workflow.json            ← Import into n8n (optional GUI alternative to GitHub Actions)
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml   ← GitHub Actions cron — runs daily, pushes to YouTube
├── output/                      ← Auto-created. Stores episode assets (ep-001/, ep-002/, ...)
├── logs/                        ← Auto-created. Pipeline run logs
├── setup_mac.sh                 ← One-command Mac setup script
└── requirements.txt
```

---

## Phase 1 — Mac Prerequisites (One-time setup)

### Option A — Automated (recommended)

```bash
bash setup_mac.sh
```

This installs Homebrew if missing, installs Python 3.11 + FFmpeg, creates a venv, installs Python deps, downloads the Hindi font, creates `output/` and `logs/`, and copies `.env.example` to `.env`.

### Option B — Manual

```bash
# 1. Install system dependencies
brew install python@3.11 ffmpeg git

# 2. Create venv and install Python deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Download Hindi font for subtitles
mkdir -p ffmpeg/fonts
curl -sL "https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari-Bold.ttf" \
  -o ffmpeg/fonts/NotoSansDevanagari-Bold.ttf

# 4. Create directories and copy env template
mkdir -p output logs
cp config/.env.example config/.env
```

---

## Phase 2 — API Keys Setup

### APIs required

| Service | Purpose | Free Tier | Signup |
|---|---|---|---|
| Google Gemini | Script generation | Free tier available | aistudio.google.com |
| Ideogram | Scene images (5 per episode) | 25 free/day | ideogram.ai |
| ElevenLabs | Hindi voiceover | 10k chars/month | elevenlabs.io |
| YouTube Data API v3 | Upload videos | Free (quota-limited) | console.cloud.google.com |
| Suno (optional) | Background music | 50 songs/day free | suno.com |

### Fill in your keys

```bash
nano config/.env   # or: code config/.env
```

Key variables:
```
GEMINI_API_KEY=...
IDEOGRAM_API_KEY=...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...        # find with: python3 scripts/03_generate_voice.py --list-voices
SUNO_API_KEY=...               # optional
```

---

## Phase 3 — YouTube OAuth Setup (one-time)

```bash
# 1. Go to: https://console.cloud.google.com
# 2. Create project → Enable "YouTube Data API v3"
# 3. Create OAuth 2.0 credentials → Desktop App
# 4. Download client_secret.json → put in config/
# 5. Run the auth flow once:
python3 scripts/07_upload_youtube.py --auth
# Browser opens → sign in → token saved to config/token.json
```

---

## Phase 4 — Run Your First Episode

```bash
source venv/bin/activate

# Full pipeline for a specific episode:
python3 scripts/run_pipeline.py --episode 2

# Auto-pick next pending episode:
python3 scripts/run_pipeline.py --next

# Test without uploading to YouTube:
python3 scripts/run_pipeline.py --episode 2 --skip-upload

# Resume from a specific step after a failure:
python3 scripts/run_pipeline.py --episode 2 --from-step 3
```

### Run individual steps

```bash
python3 scripts/01_generate_script.py --episode 2
python3 scripts/02_generate_images.py --episode 2
python3 scripts/03_generate_voice.py --episode 2
python3 scripts/04_generate_music.py --episode 2
bash   scripts/05_assemble_video.sh 2
python3 scripts/06_create_thumbnail.py --episode 2
python3 scripts/07_upload_youtube.py --episode 2
```

---

## Phase 5 — Daily Auto-Run via GitHub Actions

The pipeline runs automatically every day at **2:00 AM UTC (7:30 AM IST)**.

### Setup

1. Push the repo to GitHub.
2. Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `IDEOGRAM_API_KEY` | Your Ideogram API key |
| `ELEVENLABS_API_KEY` | Your ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | Your ElevenLabs voice ID |
| `SUNO_API_KEY` | Your Suno key (optional) |
| `YOUTUBE_TOKEN_JSON` | Contents of `config/token.json` |
| `YOUTUBE_CLIENT_SECRET_JSON` | Contents of `config/client_secret.json` |

3. Push to `main` — Actions will handle the rest.

### Manual trigger

Go to **Actions → Daily Mahabharat Shorts Pipeline → Run workflow** and optionally specify:
- **Episode number** (leave blank for auto-next)
- **Skip upload** (for dry-run testing)
- **Start from step** (to resume after a failed run)

After each successful run, `config/episode_plan.json` is committed back with the episode marked `done`.

---

## Monitor & Debug

```bash
# View live log
tail -f logs/pipeline.log

# Check episode output folder
ls -la output/ep-002/

# Test Gemini API connection
python3 scripts/01_generate_script.py --test

# List available ElevenLabs voices
python3 scripts/03_generate_voice.py --list-voices
```

Artifacts (output files + logs) are also uploaded to GitHub Actions for 7 days after each run.

---

## Episode Plan

Defined episodes are in [config/episode_plan.json](config/episode_plan.json). Each entry has:

```json
{
  "episode": 2,
  "title_hint": "Yudhishthira bows to Bhishma before battle",
  "character_focus": "Yudhishthira, Bhishma",
  "arc": "Kurukshetra War - Day 1",
  "emotional_core": "reverence vs war",
  "cliffhanger_setup": "Bhishma grants a boon — what does he ask?",
  "status": "pending"
}
```

Status values: `pending` → picked up by `--next` flag | `done` → skipped.
