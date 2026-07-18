#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if ! launchctl print "gui/$(id -u)/${SERVICE_LABEL}" >/dev/null 2>&1; then
  echo "Phone2Computer 未运行。"
  rm -f "${PID_FILE}" "${PORT_FILE}"
  exit 0
fi

launchctl remove "${SERVICE_LABEL}"
rm -f "${PID_FILE}" "${PORT_FILE}"
echo "Phone2Computer 已停止。"
