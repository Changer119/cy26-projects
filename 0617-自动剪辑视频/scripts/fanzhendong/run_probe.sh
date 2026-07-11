#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VIDEO_FILE="$ROOT_DIR/outputs/fanzhendong/fanzhendong-koubo.mp4"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/fanzhendong-probe.log"

mkdir -p "$LOG_DIR"
exec > >(tee "$LOG_FILE") 2>&1

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate \
  -of json \
  "$VIDEO_FILE"
