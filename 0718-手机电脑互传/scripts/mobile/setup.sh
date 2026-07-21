#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"

{
  command -v brew >/dev/null
  brew list openjdk@17 >/dev/null 2>&1 || brew install openjdk@17
  brew list android-commandlinetools >/dev/null 2>&1 || brew install android-commandlinetools

  source "${SCRIPT_DIR}/common.sh"
  SDK_MANAGER="$(command -v sdkmanager)"
  yes | "${SDK_MANAGER}" --sdk_root="${ANDROID_SDK_ROOT}" --licenses >/dev/null || true
  "${SDK_MANAGER}" --sdk_root="${ANDROID_SDK_ROOT}" \
    "platform-tools" "platforms;android-36" "build-tools;36.0.0"

  if [[ ! -x "${MOBILE_ROOT}/gradlew" ]]; then
    BOOTSTRAP_DIR="${MOBILE_ROOT}/.gradle-bootstrap"
    mkdir -p "${BOOTSTRAP_DIR}"
    ARCHIVE="${BOOTSTRAP_DIR}/gradle-9.4.1-bin.zip"
    if [[ ! -f "${ARCHIVE}" ]]; then
      curl -fL "https://services.gradle.org/distributions/gradle-9.4.1-bin.zip" -o "${ARCHIVE}"
    fi
    unzip -q -o "${ARCHIVE}" -d "${BOOTSTRAP_DIR}"
    "${BOOTSTRAP_DIR}/gradle-9.4.1/bin/gradle" \
      -p "${MOBILE_ROOT}" wrapper --gradle-version 9.4.1
  fi
} 2>&1 | tee "${LOG_DIR}/mobile-setup.log"
