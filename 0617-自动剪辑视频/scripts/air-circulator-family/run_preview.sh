#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/air-circulator-family-ad"
LOG_FILE="${ROOT_DIR}/logs/air_circulator_family_preview.log"

mkdir -p "${ROOT_DIR}/logs"
cd "${PROJECT_DIR}"

{
  echo "[air-circulator-family-preview] $(date '+%Y-%m-%d %H:%M:%S')"
  npx --yes hyperframes@0.6.110 preview --port 3019
} 2>&1 | tee "${LOG_FILE}"
