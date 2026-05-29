#!/bin/bash

set -e

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "========================================"
echo "  启动量化交易系统开发环境"
echo "========================================"

echo ""
echo "[1/3] 启动后端服务..."
echo "----------------------------------------"

cd "$BACKEND_DIR"
source .venv/bin/activate

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "后端服务已启动 (PID: $BACKEND_PID)"
echo "API文档: http://localhost:8000/docs"

echo ""
echo "[2/3] 启动前端服务..."
echo "----------------------------------------"

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "未检测到 node_modules，正在安装依赖..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

echo "前端服务已启动 (PID: $FRONTEND_PID)"
echo "前端页面: http://localhost:5173"

echo ""
echo "[3/3] 服务启动完成！"
echo "========================================"
echo ""
echo "后端服务: http://localhost:8000"
echo "前端页面: http://localhost:5173"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

cleanup() {
    echo ""
    echo "正在停止服务..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

wait