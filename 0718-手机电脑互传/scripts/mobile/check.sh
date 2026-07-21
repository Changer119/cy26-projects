#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

{
  "${SCRIPT_DIR}/test.sh"
  "${SCRIPT_DIR}/lint.sh"
  "${SCRIPT_DIR}/build.sh"
} 2>&1 | tee "${LOG_DIR}/mobile-check.log"
