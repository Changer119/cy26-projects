#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
LOG_FILE="logs/plan.log"
INPUT_VIDEO="${1:-}"
MAX_DURATION="${MAX_DURATION:-60}"
SILENCE_THRESHOLD="${SILENCE_THRESHOLD:-0.8}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] plan"
  args=(plan --max-duration "$MAX_DURATION" --silence-threshold "$SILENCE_THRESHOLD")
  if [[ -n "$INPUT_VIDEO" ]]; then
    args+=(--input "$INPUT_VIDEO")
  fi
  uv run auto-video-edit "${args[@]}"
} 2>&1 | tee "$LOG_FILE"
