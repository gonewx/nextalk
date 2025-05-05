#!/bin/bash

# 启动NexTalk服务器和客户端的脚本

# 确定脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境（如果存在）
if [ -d ".venv" ]; then
    echo "激活虚拟环境..."
    source .venv/bin/activate
fi

# 启动服务器（在后台运行）
echo "正在启动NexTalk服务器..."
python -m nextalk_server &
SERVER_PID=$!

# 等待服务器启动完成
echo "等待服务器启动（3秒）..."
sleep 3

# 启动客户端
echo "正在启动NexTalk客户端..."
python -m nextalk_client

# 当客户端退出时，关闭服务器
echo "客户端已退出，正在关闭服务器..."
kill $SERVER_PID

echo "NexTalk已完全关闭。" 