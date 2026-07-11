#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/wechat-karpathy-ppt-video"
SCRIPT_PATH="${HOME}/.codex/plugins/cache/openai-curated-remote/hyperframes/0.1.2/skills/hyperframes/scripts/animation-map.mjs"
LOG_FILE="${ROOT_DIR}/logs/wechat_karpathy_animation_map.log"

mkdir -p "${ROOT_DIR}/logs"
cd "${ROOT_DIR}"

{
  echo "[wechat-karpathy-animation-map] $(date '+%Y-%m-%d %H:%M:%S')"
  if ! node -e "import('@hyperframes/producer')" >/dev/null 2>&1; then
    echo "skip: @hyperframes/producer is not available in this shell environment"
    exit 0
  fi
  node "${SCRIPT_PATH}" "${PROJECT_DIR}" --out "${PROJECT_DIR}/.hyperframes/anim-map"
} 2>&1 | tee "${LOG_FILE}"
