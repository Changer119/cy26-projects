#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

adb logcat -v time -s Phone2Computer | tee "${LOG_DIR}/mobile-logcat.log"
