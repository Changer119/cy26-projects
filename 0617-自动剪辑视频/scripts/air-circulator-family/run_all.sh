#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/run_init.sh"
"${SCRIPT_DIR}/run_assets.sh"
"${SCRIPT_DIR}/run_check.sh"
"${SCRIPT_DIR}/run_animation_map.sh"
"${SCRIPT_DIR}/run_render.sh"
"${SCRIPT_DIR}/run_verify.sh"
