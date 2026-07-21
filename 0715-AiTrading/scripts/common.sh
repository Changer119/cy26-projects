#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PROJECT_ROOT
export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

mkdir -p "${PROJECT_ROOT}/logs" "${PROJECT_ROOT}/data"

ensure_environment() {
  if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    "${PROJECT_ROOT}/scripts/setup.sh"
  fi
}
