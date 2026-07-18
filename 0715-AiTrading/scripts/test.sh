#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
ensure_environment

cd "${PROJECT_ROOT}"
uv run pytest "$@" 2>&1 | tee "${PROJECT_ROOT}/logs/test.log"
