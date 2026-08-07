#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "${FRONTEND_DIR}"
if [[ ! -d node_modules ]]; then
  npm install 2>&1 | tee "${LOG_DIR}/install.log"
fi

echo "== TypeScript 类型检查 =="
npx tsc --noEmit

echo "== ESLint =="
npm run lint
