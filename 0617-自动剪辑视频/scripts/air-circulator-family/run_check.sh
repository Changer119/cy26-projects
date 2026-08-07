#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/air-circulator-family-ad"
LOG_FILE="${ROOT_DIR}/logs/air_circulator_family_check.log"

mkdir -p "${ROOT_DIR}/logs"
cd "${PROJECT_DIR}"

{
  echo "[air-circulator-family-check] $(date '+%Y-%m-%d %H:%M:%S')"
  npx --yes hyperframes@0.6.110 lint --verbose
  npx --yes hyperframes@0.6.110 validate
  npx --yes hyperframes@0.6.110 inspect --samples 15
} 2>&1 | tee "${LOG_FILE}"
