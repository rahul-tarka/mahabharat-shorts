#!/bin/bash
# ============================================================
#  Step 05 — Assemble final 60s YouTube Short via FFmpeg
#  Usage:  bash scripts/05_assemble_video.sh <episode_number>
#  Example: bash scripts/05_assemble_video.sh 2
# ============================================================

set -euo pipefail

EP_NUM="${1:-}"
if [ -z "$EP_NUM" ]; then
  echo "Usage: bash scripts/05_assemble_video.sh <episode_number>"
  exit 1
fi

EP_PAD=$(printf "%03d" "$EP_NUM")
EP_DIR="output/ep-${EP_PAD}"
IMG_DIR="${EP_DIR}/images"
AUDIO_DIR="${EP_DIR}/audio"
VIDEO_DIR="${EP_DIR}/video"
FONT_PATH="ffmpeg/fonts/NotoSansDevanagari-Bold.ttf"
SCRIPT_JSON="${EP_DIR}/script.json"

echo ""
echo "🎬 Assembling video for Episode ${EP_NUM}..."
echo "   Input dir: ${EP_DIR}"

# ── Validate inputs ────────────────────────────────────────────
if [ ! -f "${AUDIO_DIR}/voiceover.mp3" ]; then
  echo "❌ Missing: ${AUDIO_DIR}/voiceover.mp3"
  echo "   Run Step 03 first: python3 scripts/03_generate_voice.py --episode ${EP_NUM}"
  exit 1
fi

if [ ! -f "${AUDIO_DIR}/bgm.mp3" ]; then
  echo "❌ Missing: ${AUDIO_DIR}/bgm.mp3"
  echo "   Run Step 04 first: python3 scripts/04_generate_music.py --episode ${EP_NUM}"
  exit 1
fi

SCENE_COUNT=$(ls "${IMG_DIR}"/scene_*.jpg 2>/dev/null | wc -l | tr -d ' ')
if [ "$SCENE_COUNT" -eq 0 ]; then
  echo "❌ No scene images found in ${IMG_DIR}"
  echo "   Run Step 02 first: python3 scripts/02_generate_images.py --episode ${EP_NUM}"
  exit 1
fi

echo "   Found ${SCENE_COUNT} scene images"

mkdir -p "${VIDEO_DIR}/clips" "${VIDEO_DIR}/tmp"

# Absolute path to clips dir — used in concat list so ffmpeg can always find them
CLIPS_ABS="$(pwd)/${VIDEO_DIR}/clips"

# ── Step A: Create animated clip from each image (Ken Burns effect) ──
echo ""
echo "📽️  Step A: Animating ${SCENE_COUNT} scenes (Ken Burns + zoom)..."

CLIP_DURATION=10  # seconds per scene
TOTAL_DURATION=$((SCENE_COUNT * CLIP_DURATION))

for i in $(seq 1 "$SCENE_COUNT"); do
  IMG_FILE="${IMG_DIR}/scene_$(printf '%02d' $i).jpg"
  OUT_CLIP="${VIDEO_DIR}/clips/clip_$(printf '%02d' $i).mp4"

  if [ ! -f "$IMG_FILE" ]; then
    echo "   ⚠️  Missing scene $i — skipping"
    continue
  fi

  echo "   Scene $i → ${OUT_CLIP}..."

  # Ken Burns: slow zoom-in with slight pan
  # zoompan: zoom from 1.0 to 1.06 over 300 frames, pan center
  ffmpeg -y -loop 1 -i "${IMG_FILE}" \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,\
zoompan=z='min(zoom+0.0002,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=300:s=1080x1920:fps=30,\
format=yuv420p" \
    -t "${CLIP_DURATION}" \
    -c:v libx264 -preset fast -crf 20 \
    -an \
    "${OUT_CLIP}" \
    -loglevel error
done

echo "   ✅ All clips created"

# ── Step B: Concatenate clips ──────────────────────────────────
echo ""
echo "📽️  Step B: Concatenating clips..."

CONCAT_LIST="${VIDEO_DIR}/tmp/concat.txt"
> "$CONCAT_LIST"
for i in $(seq 1 "$SCENE_COUNT"); do
  CLIP="${VIDEO_DIR}/clips/clip_$(printf '%02d' $i).mp4"
  if [ -f "$CLIP" ]; then
    echo "file '${CLIPS_ABS}/clip_$(printf '%02d' $i).mp4'" >> "$CONCAT_LIST"
  fi
done

VIDEO_ONLY="${VIDEO_DIR}/tmp/video_only.mp4"
ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" \
  -c copy "${VIDEO_ONLY}" \
  -loglevel error

echo "   ✅ Clips concatenated → ${TOTAL_DURATION}s video"

# ── Step C: Mix voiceover + BGM ───────────────────────────────
echo ""
echo "🔊 Step C: Mixing audio..."
MIXED_AUDIO="${VIDEO_DIR}/tmp/mixed_audio.mp3"

# voiceover at 0dB, BGM at -12dB (background)
ffmpeg -y \
  -i "${AUDIO_DIR}/voiceover.mp3" \
  -i "${AUDIO_DIR}/bgm.mp3" \
  -filter_complex "\
[0:a]volume=1.0[voice];\
[1:a]volume=0.25,afade=t=in:st=0:d=2,afade=t=out:st=$((TOTAL_DURATION-3)):d=3[bgm];\
[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]" \
  -map "[out]" \
  -t "${TOTAL_DURATION}" \
  -c:a libmp3lame -b:a 192k \
  "${MIXED_AUDIO}" \
  -loglevel error

echo "   ✅ Audio mixed (voice + BGM)"

# ── Step D: Merge video + audio ───────────────────────────────
echo ""
echo "🔗 Step D: Merging video + audio..."
VIDEO_WITH_AUDIO="${VIDEO_DIR}/tmp/video_audio.mp4"

ffmpeg -y \
  -i "${VIDEO_ONLY}" \
  -i "${MIXED_AUDIO}" \
  -c:v copy -c:a aac -b:a 192k \
  -shortest \
  "${VIDEO_WITH_AUDIO}" \
  -loglevel error

echo "   ✅ Video + audio merged"

# ── Step E: Burn subtitles ────────────────────────────────────
# Extract subtitles from script.json into SRT format first
echo ""
echo "📝 Step E: Adding Hindi subtitles..."

python3 - <<PYEOF
import json, sys
from pathlib import Path

script_path = Path("${SCRIPT_JSON}")
if not script_path.exists():
    sys.exit(0)

with open(script_path, encoding='utf-8') as f:
    data = json.load(f)

subs = data.get('subtitles', [])
if not subs:
    print("   ⚠️  No subtitles in script.json — skipping subtitle burn")
    sys.exit(0)

srt_path = Path("${VIDEO_DIR}/tmp/subtitles.srt")
with open(srt_path, 'w', encoding='utf-8') as f:
    for i, sub in enumerate(subs, 1):
        start = sub.get('start', '00:00')
        end = sub.get('end', '00:05')
        # Convert MM:SS to HH:MM:SS,mmm format for SRT
        def to_srt_time(t):
            parts = t.split(':')
            if len(parts) == 2:
                return f"00:00:{parts[0]},{parts[1]}0" if len(parts[1]) == 1 else f"00:{parts[0]}:{parts[1]},000"
            return f"{t},000"
        
        hindi = sub.get('hindi', '')
        english = sub.get('english', '')
        f.write(f"{i}\n")
        f.write(f"{to_srt_time(start)} --> {to_srt_time(end)}\n")
        f.write(f"{hindi}\n")
        f.write(f"<i>{english}</i>\n\n")

print(f"   ✅ SRT file created with {len(subs)} subtitles")
PYEOF

SRT_FILE="${VIDEO_DIR}/tmp/subtitles.srt"
FINAL_VIDEO="${VIDEO_DIR}/final.mp4"

if [ -f "$SRT_FILE" ] && [ -f "$FONT_PATH" ]; then
  ffmpeg -y \
    -i "${VIDEO_WITH_AUDIO}" \
    -vf "subtitles=${SRT_FILE}:force_style='FontName=NotoSansDevanagari-Bold,\
FontSize=20,PrimaryColour=&Hffffff,OutlineColour=&H000000,\
Outline=2,Shadow=1,Bold=1,Alignment=2,MarginV=60':\
fontsdir=ffmpeg/fonts" \
    -c:a copy \
    "${FINAL_VIDEO}" \
    -loglevel error
  echo "   ✅ Subtitles burned"
elif [ -f "$SRT_FILE" ]; then
  echo "   ⚠️  Font not found — burning subtitles without custom font"
  ffmpeg -y \
    -i "${VIDEO_WITH_AUDIO}" \
    -vf "subtitles=${SRT_FILE}" \
    -c:a copy \
    "${FINAL_VIDEO}" \
    -loglevel error
else
  echo "   ⚠️  No subtitles — copying video as-is"
  cp "${VIDEO_WITH_AUDIO}" "${FINAL_VIDEO}"
fi

# ── Step F: Add series watermark (text overlay) ───────────────
echo ""
echo "🏷️  Step F: Adding series watermark..."

WATERMARKED="${VIDEO_DIR}/final_watermarked.mp4"
SERIES_TEXT="महाभारत · युग का संघर्ष"
EP_TEXT="EP ${EP_NUM}"

ffmpeg -y \
  -i "${FINAL_VIDEO}" \
  -vf "drawtext=text='${SERIES_TEXT}':fontfile=${FONT_PATH}:\
fontsize=22:fontcolor=white@0.7:\
x=(w-text_w)/2:y=40:shadowcolor=black@0.5:shadowx=1:shadowy=1,\
drawtext=text='${EP_TEXT}':fontfile=${FONT_PATH}:\
fontsize=18:fontcolor=gold@0.8:\
x=w-text_w-20:y=40:shadowcolor=black@0.8:shadowx=1:shadowy=1" \
  -c:a copy \
  "${WATERMARKED}" \
  -loglevel error 2>/dev/null || {
    echo "   ⚠️  Watermark skipped (font issue) — using un-watermarked video"
    cp "${FINAL_VIDEO}" "${WATERMARKED}"
  }

echo "   ✅ Watermark added"

# ── Done ───────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "✅ Video assembly complete!"
echo "   Output: ${WATERMARKED}"
SIZE=$(du -sh "${WATERMARKED}" | cut -f1)
echo "   Size: ${SIZE}"
echo "   Duration: ${TOTAL_DURATION}s"
echo ""
echo "   Next steps:"
echo "   python3 scripts/06_create_thumbnail.py --episode ${EP_NUM}"
echo "   python3 scripts/07_upload_youtube.py --episode ${EP_NUM}"
echo "════════════════════════════════════════"
