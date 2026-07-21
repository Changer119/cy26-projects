#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

{
  cd "${MOBILE_ROOT}"
  ./gradlew testDebugUnitTest
} 2>&1 | tee "${LOG_DIR}/mobile-test.log"
