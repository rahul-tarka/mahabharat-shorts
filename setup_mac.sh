#!/bin/bash
# ============================================================
#  Mahabharat Shorts — One-time Mac Setup Script
#  Run this ONCE after cloning the repo:
#    bash setup_mac.sh
# ============================================================

set -e

echo ""
echo "🚀 Mahabharat Shorts — Mac Setup"
echo "═══════════════════════════════════════"

# ── Check Homebrew ────────────────────────────────────────────
echo ""
echo "📦 Step 1: Checking Homebrew..."
if ! command -v brew &>/dev/null; then
  echo "   Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "   ✅ Homebrew already installed"
fi

# ── Install system tools ──────────────────────────────────────
echo ""
echo "📦 Step 2: Installing system dependencies..."
brew install python@3.11 ffmpeg git 2>/dev/null || true

# Verify
echo "   FFmpeg: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3)"
echo "   Python: $(python3 --version)"
echo "   ✅ System tools ready"

# ── Python virtual environment ────────────────────────────────
echo ""
echo "🐍 Step 3: Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "   ✅ Python environment ready"

# ── Download Hindi font ───────────────────────────────────────
echo ""
echo "🔤 Step 4: Downloading Hindi font..."
mkdir -p ffmpeg/fonts
FONT_PATH="ffmpeg/fonts/NotoSansDevanagari-Bold.ttf"
if [ ! -f "$FONT_PATH" ]; then
  echo "   Downloading NotoSansDevanagari-Bold.ttf..."
  curl -sL "https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari-Bold.ttf" \
    -o "$FONT_PATH"
  echo "   ✅ Font downloaded"
else
  echo "   ✅ Font already exists"
fi

# ── Create directories ────────────────────────────────────────
echo ""
echo "📁 Step 5: Creating project directories..."
mkdir -p output logs config
echo "   ✅ Directories created"

# ── Copy .env template ────────────────────────────────────────
echo ""
echo "🔑 Step 6: Environment setup..."
if [ ! -f "config/.env" ]; then
  cp config/.env.example config/.env
  echo "   ✅ config/.env created from template"
  echo ""
  echo "   ⚠️  IMPORTANT: Open config/.env and fill in your API keys:"
  echo "   ┌─────────────────────────────────────────────────────┐"
  echo "   │  nano config/.env                                   │"
  echo "   │                                                     │"
  echo "   │  Keys needed:                                       │"
  echo "   │  - ANTHROPIC_API_KEY (console.anthropic.com)        │"
  echo "   │  - IDEOGRAM_API_KEY  (ideogram.ai)                  │"
  echo "   │  - ELEVENLABS_API_KEY (elevenlabs.io)               │"
  echo "   │  - ELEVENLABS_VOICE_ID (from --list-voices command) │"
  echo "   └─────────────────────────────────────────────────────┘"
else
  echo "   ✅ config/.env already exists"
fi

# ── Make scripts executable ───────────────────────────────────
chmod +x scripts/*.sh
echo ""
echo "═══════════════════════════════════════"
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "   1. Fill in API keys:"
echo "      nano config/.env"
echo ""
echo "   2. Test Claude API:"
echo "      source venv/bin/activate"
echo "      python3 scripts/01_generate_script.py --test"
echo ""
echo "   3. Get ElevenLabs voice ID:"
echo "      python3 scripts/03_generate_voice.py --list-voices"
echo ""
echo "   4. Setup YouTube OAuth (one-time):"
echo "      python3 scripts/07_upload_youtube.py --auth"
echo ""
echo "   5. Run your first episode:"
echo "      python3 scripts/run_pipeline.py --episode 1 --skip-upload"
echo ""
echo "   6. When ready to publish:"
echo "      python3 scripts/run_pipeline.py --episode 1"
echo ""
echo "═══════════════════════════════════════"
