#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/common.sh"
ensure_environment
cd "${PROJECT_ROOT}"
uv run --frozen --module ai_trading.market_mcp.clients.configure \
  2>&1 | tee "${PROJECT_ROOT}/logs/market-mcp/configure-clients.log"
