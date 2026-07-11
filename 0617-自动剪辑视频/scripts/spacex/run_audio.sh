#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/spacex-promo"
LOG_FILE="${ROOT_DIR}/logs/spacex_audio.log"

mkdir -p "${ROOT_DIR}/logs" "${PROJECT_DIR}/assets"

{
  echo "[spacex-audio] $(date '+%Y-%m-%d %H:%M:%S')"
  ffmpeg -y \
    -f lavfi -i "sine=frequency=44:duration=30:sample_rate=48000" \
    -f lavfi -i "sine=frequency=88:duration=30:sample_rate=48000" \
    -f lavfi -i "sine=frequency=176:duration=30:sample_rate=48000" \
    -filter_complex "[0:a]volume=0.22[a0];[1:a]volume=0.08,atrim=0:30[a1];[2:a]volume=0.035,atrim=0:30[a2];[a0][a1][a2]amix=inputs=3:duration=longest,afade=t=in:st=0:d=0.8,afade=t=out:st=28.8:d=1.2" \
    -c:a pcm_s16le "${PROJECT_DIR}/assets/pulse.wav"
} 2>&1 | tee "${LOG_FILE}"
