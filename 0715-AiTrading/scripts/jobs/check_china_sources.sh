#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/common.sh"
ensure_environment
cd "${PROJECT_ROOT}"
uv run --module ai_trading.integrations.china.probe "$@" 2>&1 | tee "${PROJECT_ROOT}/logs/china-sources.log"
