#!/usr/bin/env bash
set -euo pipefail

LABEL="com.local.ai-trading"
DOMAIN="gui/${UID}"
TARGET="${HOME}/Library/LaunchAgents/${LABEL}.plist"

if [[ -f "${TARGET}" ]]; then
  launchctl bootout "${DOMAIN}" "${TARGET}" >/dev/null 2>&1 || true
  rm -f "${TARGET}"
fi
echo "已卸载本机常驻服务：${LABEL}"
