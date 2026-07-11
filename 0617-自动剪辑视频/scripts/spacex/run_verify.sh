#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VIDEO_FILE="${ROOT_DIR}/outputs/spacex-promo-vertical.mp4"
LOG_FILE="${ROOT_DIR}/logs/spacex_verify.log"

mkdir -p "${ROOT_DIR}/logs" "${ROOT_DIR}/outputs"

{
  echo "[spacex-verify] $(date '+%Y-%m-%d %H:%M:%S')"
  ffprobe -v error \
    -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,duration \
    -show_entries format=duration,size \
    -of json "${VIDEO_FILE}"
  for second in 3 12 27; do
    ffmpeg -y -ss "${second}" -i "${VIDEO_FILE}" -frames:v 1 -update 1 \
      "${ROOT_DIR}/outputs/spacex-frame-${second}.jpg"
  done
} 2>&1 | tee "${LOG_FILE}"
