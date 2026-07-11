#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
LOG_FILE="logs/tests.log"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] run tests"
  uv run --extra dev pytest "$@"
} 2>&1 | tee "$LOG_FILE"
