#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/common.sh"
ensure_environment
"${PROJECT_ROOT}/scripts/web/build.sh"

LABEL="com.local.ai-trading"
DOMAIN="gui/${UID}"
TEMPLATE="${PROJECT_ROOT}/deploy/launchd/${LABEL}.plist.template"
TARGET_DIR="${HOME}/Library/LaunchAgents"
TARGET="${TARGET_DIR}/${LABEL}.plist"

mkdir -p "${TARGET_DIR}"
sed "s|__PROJECT_ROOT__|${PROJECT_ROOT}|g" "${TEMPLATE}" >"${TARGET}"
plutil -lint "${TARGET}"
launchctl bootout "${DOMAIN}" "${TARGET}" >/dev/null 2>&1 || true
launchctl bootstrap "${DOMAIN}" "${TARGET}"
launchctl kickstart -k "${DOMAIN}/${LABEL}"
echo "已安装并启动本机常驻服务：${LABEL}"
