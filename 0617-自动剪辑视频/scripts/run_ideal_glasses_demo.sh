#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs outputs
LOG_FILE="logs/ideal_glasses_demo.log"
INPUT_DIR="${1:-inputs/理想AI眼镜}"
OUTPUT_FILE="${2:-outputs/理想AI眼镜-入盒演示-5s.mp4}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ideal glasses demo"
  uv run python -m auto_video_editing.glasses_box_demo \
    --input-dir "$INPUT_DIR" \
    --output "$OUTPUT_FILE"
} 2>&1 | tee "$LOG_FILE"
