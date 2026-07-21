#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

{
  cd "${MOBILE_ROOT}"
  ./gradlew lintDebug
} 2>&1 | tee "${LOG_DIR}/mobile-lint.log"
