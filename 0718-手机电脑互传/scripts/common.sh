#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
DIST_DIR="${PROJECT_ROOT}/dist"
PID_FILE="${LOG_DIR}/phone2computer.pid"
PORT_FILE="${LOG_DIR}/phone2computer.port"
APP_PORT="${PHONE2COMPUTER_PORT:-18765}"
SERVICE_LABEL="com.changer.phone2computer.session"

mkdir -p "${LOG_DIR}" "${DIST_DIR}"
