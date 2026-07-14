#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SLIDES_FILE="$ROOT_DIR/slides/ai-team-transformation.html"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/frontend-slides.log"

mkdir -p "$LOG_DIR"

{
  printf '[%s] 打开完整演示\n' "$(date '+%Y-%m-%d %H:%M:%S')"
  if [[ ! -f "$SLIDES_FILE" ]]; then
    printf '缺少演示文件：%s\n' "$SLIDES_FILE" >&2
    exit 1
  fi
  open "$SLIDES_FILE"
  printf '已打开：%s\n' "$SLIDES_FILE"
} 2>&1 | tee -a "$LOG_FILE"
