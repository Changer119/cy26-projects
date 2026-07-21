#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

{
  cd "${MOBILE_ROOT}"
  ./gradlew assembleDebug
  mkdir -p "${PROJECT_ROOT}/dist"
  cp "${MOBILE_ROOT}/app/build/outputs/apk/debug/app-debug.apk" \
    "${PROJECT_ROOT}/dist/Phone2Computer-v2-debug.apk"
  cp "${MOBILE_ROOT}/app/build/outputs/apk/debug/app-debug.apk" \
    "${PROJECT_ROOT}/web/public/Phone2Computer-v2.apk"
  shasum -a 256 "${PROJECT_ROOT}/dist/Phone2Computer-v2-debug.apk" \
    > "${PROJECT_ROOT}/dist/Phone2Computer-v2-debug.apk.sha256"
  "${ANDROID_SDK_ROOT}/build-tools/36.0.0/apksigner" verify --verbose \
    "${PROJECT_ROOT}/dist/Phone2Computer-v2-debug.apk"
  "${ANDROID_SDK_ROOT}/build-tools/36.0.0/aapt2" dump badging \
    "${PROJECT_ROOT}/dist/Phone2Computer-v2-debug.apk" \
    | rg "^(package|minSdkVersion|targetSdkVersion|launchable-activity)"
} 2>&1 | tee "${LOG_DIR}/mobile-build.log"
