#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MOBILE_ROOT="${PROJECT_ROOT}/mobile/android"
LOG_DIR="${PROJECT_ROOT}/logs"
ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-${HOME}/Library/Android/sdk}"
ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT}}"
JAVA_HOME="${JAVA_HOME:-$(brew --prefix openjdk@17 2>/dev/null)/libexec/openjdk.jdk/Contents/Home}"

export PROJECT_ROOT MOBILE_ROOT LOG_DIR ANDROID_SDK_ROOT ANDROID_HOME JAVA_HOME
export PATH="${JAVA_HOME}/bin:${ANDROID_SDK_ROOT}/platform-tools:${PATH}"

mkdir -p "${LOG_DIR}"
