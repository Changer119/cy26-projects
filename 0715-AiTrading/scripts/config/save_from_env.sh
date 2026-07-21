#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/common.sh"
ensure_environment
cd "${PROJECT_ROOT}"
exec uv run ai-trading configure-from-env --destination "${PROJECT_ROOT}/.env"
