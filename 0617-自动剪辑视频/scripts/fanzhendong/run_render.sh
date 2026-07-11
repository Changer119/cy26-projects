#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="$ROOT_DIR/remotion-fzd"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/fanzhendong-render.log"

mkdir -p "$LOG_DIR" "$ROOT_DIR/outputs/fanzhendong"
exec > >(tee "$LOG_FILE") 2>&1

cd "$PROJECT_DIR"
npm run render
