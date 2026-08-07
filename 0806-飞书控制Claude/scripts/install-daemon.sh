#!/usr/bin/env bash
# 把桥接服务注册为 macOS LaunchAgent，实现开机/登录自启常驻。
# 安装前建议先跑一次 ./start.sh 手动验证能正常收发消息。
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

LABEL="com.jiangfachang.feishu-claude-bridge"
TEMPLATE="$DIR/launchd/$LABEL.plist.template"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents"

sed -e "s#__BRIDGE_ROOT__#$DIR#g" -e "s#__HOME__#$HOME#g" "$TEMPLATE" > "$TARGET"

launchctl unload "$TARGET" >/dev/null 2>&1 || true
launchctl load -w "$TARGET"

echo "已安装并启动 LaunchAgent: $TARGET"
echo "查看状态：./scripts/status.sh"
echo "查看日志：tail -f '$DIR/logs/bridge.log'"
echo "卸载常驻：./scripts/uninstall-daemon.sh"
