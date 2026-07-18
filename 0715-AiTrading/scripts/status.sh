#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
PID_FILE="${PROJECT_ROOT}/logs/ai-trading.pid"
HEALTH_URL="http://127.0.0.1:8765/api/health"

if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  echo "running PID=$(cat "${PID_FILE}")"
  exit 0
fi
if curl --fail --silent "${HEALTH_URL}" >/dev/null; then
  echo "running service=http://127.0.0.1:8765"
  exit 0
fi
echo "stopped"
exit 1
