#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/common.sh"
{
  if launchctl print "gui/${UID}/com.local.ai-trading" >/dev/null 2>&1; then
    launchctl kickstart -k "gui/${UID}/com.local.ai-trading"
  else
    "${PROJECT_ROOT}/scripts/stop.sh"
    "${PROJECT_ROOT}/scripts/start.sh"
  fi
  for _attempt in {1..40}; do
    if curl --fail --silent 'http://127.0.0.1:8765/api/health' >/dev/null; then
      echo "AI Trading 重启后健康检查通过"
      curl --fail --silent 'http://127.0.0.1:8765/api/data-health'
      echo
      exit 0
    fi
    sleep 0.25
  done
  echo "AI Trading 重启后未通过健康检查" >&2
  exit 1
} 2>&1 | tee "${PROJECT_ROOT}/logs/restart.log"
