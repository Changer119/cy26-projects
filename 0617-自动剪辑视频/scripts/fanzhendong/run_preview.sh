#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="$ROOT_DIR/remotion-fzd"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/fanzhendong-preview.log"

mkdir -p "$LOG_DIR"
exec > >(tee "$LOG_FILE") 2>&1

cd "$PROJECT_DIR"
npm run preview
