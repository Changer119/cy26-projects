#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
LOG_FILE="logs/edit.log"
PLAN_PATH="${1:-outputs/plan.json}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] edit"
  uv run auto-video-edit edit --plan "$PLAN_PATH"
  mkdir -p output
  if [[ -f outputs/final.mp4 ]]; then
    cp outputs/final.mp4 output/final.mp4
    echo "synced output/final.mp4"
  fi
} 2>&1 | tee "$LOG_FILE"
