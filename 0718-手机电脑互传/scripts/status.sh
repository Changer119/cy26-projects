#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if launchctl print "gui/$(id -u)/${SERVICE_LABEL}" >/dev/null 2>&1; then
  PID="$(launchctl print "gui/$(id -u)/${SERVICE_LABEL}" | awk '/pid =/ { print $3; exit }')"
  echo "Phone2Computer 正在运行，PID=${PID}"
  ACTIVE_PORT="${APP_PORT}"
  if [[ -f "${PORT_FILE}" ]]; then
    ACTIVE_PORT="$(cat "${PORT_FILE}")"
  fi
  curl --silent "http://127.0.0.1:${ACTIVE_PORT}/health"
  echo
  exit 0
fi

echo "Phone2Computer 未运行。"
exit 1
