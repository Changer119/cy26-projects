#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/common.sh"
export PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
ensure_environment

if [[ ! -f "${PROJECT_ROOT}/web/dist/index.html" ]]; then
  "${PROJECT_ROOT}/scripts/web/build.sh"
fi

cd "${PROJECT_ROOT}"
exec uv run uvicorn ai_trading.main:app --host 127.0.0.1 --port 8765 --workers 1
