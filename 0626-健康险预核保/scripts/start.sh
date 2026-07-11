#!/bin/bash
# 一键启动前后端（两个后台进程，日志分别写入 logs/）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

mkdir -p logs

# 启动后端
bash "$SCRIPT_DIR/start-backend.sh" &
BACKEND_PID=$!

# 等后端就绪
echo "等待后端启动..."
for i in $(seq 1 20); do
    if curl -s http://localhost:8000/api/products > /dev/null 2>&1; then
        echo "✅ 后端已就绪"
        break
    fi
    sleep 1
done

# 启动前端
bash "$SCRIPT_DIR/start-frontend.sh" &
FRONTEND_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  后端 API:  http://localhost:8000"
echo "  前端页面:  http://localhost:3000"
echo "  日志目录:  ./logs/"
echo "  退出:      Ctrl+C"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 捕获 Ctrl+C 清理子进程
trap "echo '关闭中...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
