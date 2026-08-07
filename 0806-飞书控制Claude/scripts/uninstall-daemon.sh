#!/usr/bin/env bash
# 卸载常驻的 LaunchAgent
set -euo pipefail
LABEL="com.jiangfachang.feishu-claude-bridge"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ -f "$TARGET" ]]; then
  launchctl unload "$TARGET" >/dev/null 2>&1 || true
  rm -f "$TARGET"
  echo "已卸载 LaunchAgent: $TARGET"
else
  echo "未找到已安装的 LaunchAgent: $TARGET"
fi
