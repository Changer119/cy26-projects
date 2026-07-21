#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common.sh"

"${SCRIPT_DIR}/start.sh"
APK="${PROJECT_ROOT}/dist/Phone2Computer-v2-debug.apk"
adb install -r "${APK}" >/dev/null
adb logcat -c
adb shell am force-stop com.phone2computer.transfer
adb shell "am start -W \
  -a android.intent.action.VIEW \
  -d 'phone2computer://pair?server=http%3A%2F%2F10.0.2.2%3A18765&token=test' \
  com.phone2computer.transfer" >/dev/null

for _ in {1..10}; do
  if adb shell pidof com.phone2computer.transfer | rg -q '[0-9]'; then
    break
  fi
  sleep 1
done

adb logcat -d -b crash >"${LOG_DIR}/mobile-emulator-crash.log"
if rg -q "FATAL EXCEPTION|com.phone2computer.transfer" "${LOG_DIR}/mobile-emulator-crash.log"; then
  cat "${LOG_DIR}/mobile-emulator-crash.log"
  exit 1
fi

adb shell pidof com.phone2computer.transfer
echo "API 29 深链连接未发生崩溃。"
