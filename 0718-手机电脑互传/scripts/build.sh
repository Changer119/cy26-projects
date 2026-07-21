#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "${PROJECT_ROOT}/web"
npm run build

cd "${PROJECT_ROOT}"
go build -o "${DIST_DIR}/phone2computer" ./cmd/phone2computer
