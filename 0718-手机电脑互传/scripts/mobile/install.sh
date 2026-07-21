#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

{
  APK="${PROJECT_ROOT}/dist/Phone2Computer-v2-debug.apk"
  if [[ ! -f "${APK}" ]]; then
    "${SCRIPT_DIR}/build.sh"
  fi
  adb install -r "${APK}"
} 2>&1 | tee "${LOG_DIR}/mobile-install.log"
