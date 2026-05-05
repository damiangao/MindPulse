#!/bin/bash
# claude-chat 启动脚本

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${GREEN}==>${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo_step "Killing process on port $port (PID: $pid)"
        kill $pid 2>/dev/null || true
        sleep 1
    fi
}

# 杀进程
echo_step "Stopping any existing processes..."
kill_port 3001  # backend
kill_port 5173   # frontend
kill_port 3333   # playwright server

# 确保 data 目录存在
mkdir -p data

echo_step "Starting backend (port 3001)..."
cd /Users/damian/workspace/claude-chat
PYTHONPATH=. uv run python -m server.main &
BACKEND_PID=$!

# 等待 backend 启动
sleep 3

echo_step "Starting frontend (port 5173)..."
npm run dev:client &
FRONTEND_PID=$!

echo ""
echo_step "Services started:"
echo "  Backend: http://localhost:3001"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo -e "Press ${RED}Ctrl+C${NC} to stop all services"

# 等待
wait