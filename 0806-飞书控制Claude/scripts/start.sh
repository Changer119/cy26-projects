#!/usr/bin/env bash
# 前台启动桥接服务（手动调试用）。
# 常驻后台请用 install-daemon.sh 注册为 LaunchAgent。
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$DIR/lib/bridge.sh"
