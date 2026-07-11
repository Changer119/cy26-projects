#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_DIR/frontend"
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    npm install
fi

mkdir -p "$PROJECT_DIR/logs"

echo "启动前端 http://localhost:3000 ..."
npm run dev 2>&1 | tee "$PROJECT_DIR/logs/frontend.log"
