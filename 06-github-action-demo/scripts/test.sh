#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/test.log"

mkdir -p "$LOG_DIR"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] start tests"
  bash "$ROOT_DIR/scripts/test-readme-update.sh"
  bash "$ROOT_DIR/scripts/test-workflow-config.sh"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] tests passed"
} 2>&1 | tee "$LOG_FILE"
