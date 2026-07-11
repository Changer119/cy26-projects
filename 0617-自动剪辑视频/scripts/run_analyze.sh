#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
LOG_FILE="logs/analyze.log"
INPUT_VIDEO="${1:-}"
WHISPER_MODEL="${WHISPER_MODEL:-small}"
WHISPER_LANGUAGE="${WHISPER_LANGUAGE:-Chinese}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] analyze"
  args=(analyze --model "$WHISPER_MODEL" --language "$WHISPER_LANGUAGE")
  if [[ -n "$INPUT_VIDEO" ]]; then
    args+=(--input "$INPUT_VIDEO")
  fi
  uv run auto-video-edit "${args[@]}"
} 2>&1 | tee "$LOG_FILE"
