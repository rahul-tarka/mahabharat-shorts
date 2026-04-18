# 🎬 Mahabharat Shorts — Daily Auto-Publishing Pipeline

> Script → Character Images → Voice → Video → Thumbnail → YouTube Upload  
> Fully automated. Runs daily. Zero manual work after setup.

---

## 🗂️ Project Structure

```
mahabharat-shorts/
├── config/
│   ├── .env.example          ← Copy to .env, fill API keys
│   └── episode_plan.json     ← Episode schedule (arc, character, theme)
├── scripts/
│   ├── 01_generate_script.py    ← Claude API → Script JSON
│   ├── 02_generate_images.py    ← Ideogram API → 5 scene images
│   ├── 03_generate_voice.py     ← ElevenLabs API → voiceover.mp3
│   ├── 04_generate_music.py     ← Suno / Pixabay BGM
│   ├── 05_assemble_video.sh     ← FFmpeg → final 1080x1920 Short
│   ├── 06_create_thumbnail.py   ← PIL → thumbnail 1280x720
│   ├── 07_upload_youtube.py     ← YouTube Data API v3 → upload
│   └── run_pipeline.py          ← Master runner (calls all steps)
├── prompts/
│   └── script_system_prompt.txt ← Claude system prompt template
├── n8n/
│   └── workflow.json            ← Import into n8n (optional GUI)
├── ffmpeg/
│   └── fonts/                   ← NotoSansDevanagari.ttf goes here
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml   ← GitHub Actions cron (alternative to n8n)
├── output/                      ← Auto-created. Stores episode assets
└── requirements.txt
```

---

## ⚙️ Phase 1 — Mac Prerequisites (One-time setup)

### Step 1.1 — Install Homebrew (if not already)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 1.2 — Install system dependencies
```bash
brew install python@3.11 ffmpeg imagemagick git
brew install node  # for n8n
```

### Step 1.3 — Verify installs
```bash
python3 --version    # Should be 3.11+
ffmpeg -version      # Should show version
convert --version    # ImageMagick
```

### Step 1.4 — Download Hindi font for subtitles
```bash
# In project root
mkdir -p ffmpeg/fonts
curl -L "https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari-Bold.ttf" \
  -o ffmpeg/fonts/NotoSansDevanagari-Bold.ttf
```

---

## 🔑 Phase 2 — API Keys Setup

### APIs you need (all have free tiers to start):

| Service | Purpose | Free Tier | Signup |
|---|---|---|---|
| Anthropic | Script generation | $5 free credit | console.anthropic.com |
| Ideogram | Scene images | 25 free/day | ideogram.ai |
| ElevenLabs | Hindi voiceover | 10k chars/mo | elevenlabs.io |
| YouTube Data API | Upload videos | Free (quota) | console.cloud.google.com |
| Suno (optional) | BGM music | 50 songs/day free | suno.com |

### Step 2.1 — Copy env file
```bash
cp config/.env.example config/.env
```

### Step 2.2 — Fill in your API keys
```bash
nano config/.env   # or: code config/.env
```

---

## 📦 Phase 3 — Python Setup

### Step 3.1 — Create virtual environment
```bash
cd mahabharat-shorts
python3 -m venv venv
source venv/bin/activate
```

### Step 3.2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3.3 — Test Claude connection
```bash
python3 scripts/01_generate_script.py --test
```
Expected output: `✅ Claude API connected. Episode 1 script generated.`

---

## 🔐 Phase 4 — YouTube OAuth Setup (one-time)

```bash
# 1. Go to: https://console.cloud.google.com
# 2. Create project → Enable "YouTube Data API v3"
# 3. Create OAuth 2.0 credentials → Desktop app
# 4. Download client_secret.json → put in config/
# 5. Run auth flow once:
python3 scripts/07_upload_youtube.py --auth
# Browser opens → sign in → paste code → token saved to config/token.json
```

---

## 🚀 Phase 5 — Run Your First Episode

```bash
source venv/bin/activate

# Run full pipeline for episode 1:
python3 scripts/run_pipeline.py --episode 1

# Or run individual steps:
python3 scripts/01_generate_script.py --episode 1
python3 scripts/02_generate_images.py --episode 1
python3 scripts/03_generate_voice.py --episode 1
bash scripts/05_assemble_video.sh 1
python3 scripts/07_upload_youtube.py --episode 1
```

---

## ⏰ Phase 6 — Daily Auto-Run (2 options)

### Option A — Mac cron (simple, local machine must be on)
```bash
crontab -e
# Add this line:
0 2 * * * cd /path/to/mahabharat-shorts && source venv/bin/activate && python3 scripts/run_pipeline.py --next >> logs/pipeline.log 2>&1
```

### Option B — GitHub Actions (recommended, runs in cloud)
Already configured in `.github/workflows/daily_pipeline.yml`
```bash
# Push to GitHub → Actions runs daily at 2 AM IST → uploads to YouTube
git push origin main
# Set secrets in: GitHub repo → Settings → Secrets
```

---

## 📊 Monitor & Debug

```bash
# View today's log
tail -f logs/pipeline.log

# Check output folder
ls -la output/ep-001/

# Test a single step with verbose output
python3 scripts/01_generate_script.py --episode 1 --verbose
```
