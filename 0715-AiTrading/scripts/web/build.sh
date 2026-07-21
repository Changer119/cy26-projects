#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_ROOT="${PROJECT_ROOT}/web"

mkdir -p "${PROJECT_ROOT}/logs"
cd "${WEB_ROOT}"
if [[ ! -d node_modules ]]; then
  "${PROJECT_ROOT}/scripts/web/setup.sh"
fi
npm run build 2>&1 | tee "${PROJECT_ROOT}/logs/web-build.log"
