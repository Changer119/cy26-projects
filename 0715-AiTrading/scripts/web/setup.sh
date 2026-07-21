#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_ROOT="${PROJECT_ROOT}/web"

mkdir -p "${PROJECT_ROOT}/logs"
cd "${WEB_ROOT}"
npm ci 2>&1 | tee "${PROJECT_ROOT}/logs/web-setup.log"
