#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common.sh"

{
  SDK_MANAGER="$(command -v sdkmanager)"
  "${SDK_MANAGER}" --sdk_root="${ANDROID_SDK_ROOT}" \
    "cmdline-tools;latest" "emulator" "system-images;android-29;default;x86_64"
  AVD_MANAGER="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/avdmanager"

  AVD_HOME="${HOME}/.android/avd"
  if [[ ! -d "${AVD_HOME}/phone2computer_api29.avd" ]]; then
    echo no | "${AVD_MANAGER}" create avd \
      --name phone2computer_api29 \
      --package "system-images;android-29;default;x86_64" \
      --device "pixel_3a"
  fi
} 2>&1 | tee "${LOG_DIR}/mobile-emulator-setup.log"
