#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="$ROOT_DIR/remotion-fzd"
PUBLIC_DIR="$PROJECT_DIR/public"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/fanzhendong-assets.log"
IMAGE_URL="https://commons.wikimedia.org/wiki/Special:Redirect/file/Fan_Zhendong_ATTC2017_portrait.jpeg"
VOICE_NAME="${VOICE_NAME:-Tingting}"

mkdir -p "$LOG_DIR" "$PUBLIC_DIR"
exec > >(tee "$LOG_FILE") 2>&1

curl -L "$IMAGE_URL" -o "$PUBLIC_DIR/fan-zhendong.jpeg"

say -v "$VOICE_NAME" -r 205 -o "$PUBLIC_DIR/fan-zhendong-voice.aiff" "$(cat "$PUBLIC_DIR/voiceover.txt")"
ffmpeg -y -i "$PUBLIC_DIR/fan-zhendong-voice.aiff" \
  -filter:a "atempo=1.08,apad=pad_dur=2" \
  -t 10 \
  -codec:a libmp3lame \
  -q:a 3 \
  "$PUBLIC_DIR/fan-zhendong-voice.mp3"
