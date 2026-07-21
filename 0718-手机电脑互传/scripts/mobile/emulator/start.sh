#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common.sh"

EMULATOR="${ANDROID_SDK_ROOT}/emulator/emulator"
PID_FILE="${LOG_DIR}/mobile-emulator.pid"

if adb devices | rg -q '^emulator-[0-9]+[[:space:]]+device$'; then
  echo "Android API 29 模拟器已运行。"
  exit 0
fi

nohup "${EMULATOR}" \
  -avd phone2computer_api29 \
  -no-window \
  -no-audio \
  -no-boot-anim \
  -gpu swiftshader_indirect \
  >"${LOG_DIR}/mobile-emulator.log" 2>&1 &
echo $! >"${PID_FILE}"

for _ in {1..120}; do
  if [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; then
    echo "Android API 29 模拟器已启动。"
    exit 0
  fi
  sleep 1
done

echo "模拟器启动超时，请查看 ${LOG_DIR}/mobile-emulator.log" >&2
exit 1
