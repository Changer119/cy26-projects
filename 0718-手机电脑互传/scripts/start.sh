#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

"${PROJECT_ROOT}/scripts/build.sh" >"${LOG_DIR}/build.log" 2>&1

if launchctl print "gui/$(id -u)/${SERVICE_LABEL}" >/dev/null 2>&1; then
  echo "Phone2Computer 已在运行。"
  exit 0
fi

OUTPUT_DIR="${PHONE2COMPUTER_OUTPUT_DIR:-${HOME}/Downloads/Phone2Computer}"
mkdir -p "${OUTPUT_DIR}"

launchctl submit \
  -l "${SERVICE_LABEL}" \
  -o "${LOG_DIR}/app.log" \
  -e "${LOG_DIR}/app.log" \
  -- "${DIST_DIR}/phone2computer" --output "${OUTPUT_DIR}" --port "${APP_PORT}"
echo "${APP_PORT}" >"${PORT_FILE}"

for _ in {1..30}; do
  if curl --silent --fail "http://127.0.0.1:${APP_PORT}/health" >/dev/null; then
    launchctl print "gui/$(id -u)/${SERVICE_LABEL}" | awk '/pid =/ { print $3; exit }' >"${PID_FILE}"
    open "http://127.0.0.1:${APP_PORT}/admin"
    echo "Phone2Computer 已启动。"
    exit 0
  fi
  sleep 0.2
done

launchctl remove "${SERVICE_LABEL}" >/dev/null 2>&1 || true
rm -f "${PID_FILE}" "${PORT_FILE}"
echo "启动失败，请查看 ${LOG_DIR}/app.log" >&2
exit 1
