#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "${PROJECT_ROOT}"
case "${1:-all}" in
  go)
    go test "${2:-./...}" 2>&1 | tee "${LOG_DIR}/test.log"
    ;;
  web)
    cd web
    npm run test:run -- "${2:-}" 2>&1 | tee "${LOG_DIR}/test.log"
    ;;
  all)
    {
      go test ./...
      cd web
      npm run test:run
    } 2>&1 | tee "${LOG_DIR}/test.log"
    ;;
  *)
    echo "用法：$0 [all|go [包]|web [测试文件]]" >&2
    exit 2
    ;;
esac
