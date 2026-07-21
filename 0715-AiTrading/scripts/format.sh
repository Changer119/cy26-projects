#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
ensure_environment

cd "${PROJECT_ROOT}"
if (( $# > 0 )); then
  {
    uv run ruff check --fix "$@"
    uv run ruff format "$@"
  } 2>&1 | tee "${PROJECT_ROOT}/logs/format.log"
else
  {
    uv run ruff check --fix src tests
    uv run ruff format src tests
  } 2>&1 | tee "${PROJECT_ROOT}/logs/format.log"
fi
