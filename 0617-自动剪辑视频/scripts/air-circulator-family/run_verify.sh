#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_FILE="${ROOT_DIR}/outputs/air-circulator-family-ad.mp4"
FRAME_DIR="${ROOT_DIR}/outputs/air-circulator-family-ad-frames"
LOG_FILE="${ROOT_DIR}/logs/air_circulator_family_verify.log"

mkdir -p "${ROOT_DIR}/logs" "${FRAME_DIR}"

{
  echo "[air-circulator-family-verify] $(date '+%Y-%m-%d %H:%M:%S')"
  if [ ! -f "${OUTPUT_FILE}" ]; then
    echo "missing render: ${OUTPUT_FILE}" >&2
    exit 1
  fi

  ffprobe -v error \
    -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels \
    -show_entries format=duration,size,bit_rate -of json "${OUTPUT_FILE}"

  ffmpeg -hide_banner -loglevel info -i "${OUTPUT_FILE}" -map 0:a:0 \
    -af volumedetect -f null - 2>&1 | sed -n '/mean_volume/p;/max_volume/p'

  times=(1.5 4.5 8.0 13.5)
  index=1
  for timestamp in "${times[@]}"; do
    ffmpeg -y -hide_banner -loglevel error -ss "${timestamp}" -i "${OUTPUT_FILE}" \
      -frames:v 1 "${FRAME_DIR}/frame-$(printf '%02d' "${index}").png"
    index=$((index + 1))
  done

  ffmpeg -y -hide_banner -loglevel error -framerate 1 -start_number 1 \
    -i "${FRAME_DIR}/frame-%02d.png" \
    -vf "scale=540:960,tile=2x2:padding=20:margin=20:color=0xF7F3EA" \
    -frames:v 1 "${FRAME_DIR}/contact-sheet.png"

  echo "contact sheet: ${FRAME_DIR}/contact-sheet.png"
} 2>&1 | tee "${LOG_FILE}"
