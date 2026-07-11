#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs outputs
LOG_FILE="logs/ideal_glasses_verify.log"
VIDEO_FILE="${1:-outputs/理想AI眼镜-入盒演示-5s.mp4}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ideal glasses verify"
  ffprobe -v error \
    -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,duration \
    -show_entries format=duration,size \
    -of json "$VIDEO_FILE"
  for second in 0.5 2.5 4.6; do
    frame_name="${second/./_}"
    ffmpeg -y -ss "$second" -i "$VIDEO_FILE" -frames:v 1 -update 1 \
      "outputs/理想AI眼镜-frame-${frame_name}.jpg"
  done
} 2>&1 | tee "$LOG_FILE"
