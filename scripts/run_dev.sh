#!/bin/bash

set -e

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "========================================"
echo "  启动量化交易系统开发环境"
echo "========================================"

# 检查是否已经有进程在运行
for port in 8000 5173; do
    if lsof -ti :$port > /dev/null 2>&1; then
        echo "⚠️  警告: 端口 $port 已被占用"
        echo "请先停止之前的服务"
        exit 1
    fi
done

# 创建临时目录
TMP_DIR=$(mktemp -d)

echo ""
echo "[1/2] 启动后端服务..."
echo "----------------------------------------"

cd "$BACKEND_DIR"
source .venv/bin/activate

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "$TMP_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

echo "后端服务已启动 (PID: $BACKEND_PID)"
echo "后端日志: $TMP_DIR/backend.log"
echo "API文档: http://localhost:8000/docs"

# 等待后端启动
echo ""
echo "等待后端服务启动..."
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ 后端启动失败"
    cat "$TMP_DIR/backend.log"
    rm -rf "$TMP_DIR"
    exit 1
fi

echo ""
echo "[2/2] 启动前端服务..."
echo "----------------------------------------"

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "未检测到 node_modules，正在安装依赖..."
    npm install
fi

# 在后台运行前端
npm run dev > "$TMP_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

echo "前端服务已启动 (PID: $FRONTEND_PID)"
echo "前端日志: $TMP_DIR/frontend.log"
echo "前端页面: http://localhost:5173"

echo ""
echo "服务启动完成！"
echo "========================================"
echo ""
echo "后端服务: http://localhost:8000"
echo "前端页面: http://localhost:5173"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "服务正在监控日志（按 Ctrl+C 退出监控）"
echo ""
echo "命令: "
echo "  查看后端日志: 另开一个终端运行"
echo "    tail -f $TMP_DIR/backend.log"
echo ""
echo "  查看前端日志: 另开一个终端运行"
echo "    tail -f $TMP_DIR/frontend.log"
echo ""

cleanup() {
    echo ""
    echo "正在停止服务..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "清理临时文件..."
    rm -rf "$TMP_DIR"
    echo "服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 前台输出两个服务的日志
echo "显示后端和前端日志："
echo "========================================"

# 使用 tail -f 同时显示两个日志
echo -e "\033[34m=== 后端日志 (蓝色)\033[0m"
echo "----------------------------------------"

# 合并两个日志输出
tail -f "$TMP_DIR/backend.log" "$TMP_DIR/frontend.log" &
TAIL_PID=$!

wait