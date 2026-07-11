#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
LOG_FILE="logs/prepare.log"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] prepare"
  uv run auto-video-edit prepare
} 2>&1 | tee "$LOG_FILE"
