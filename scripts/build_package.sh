#!/bin/bash
#
# NexTalk客户端打包脚本
# 使用PyInstaller创建可分发的独立应用程序
#
# 前置条件:
# - 已安装PyInstaller: pip install pyinstaller
# - 项目虚拟环境已激活
# - 当前目录为项目根目录

set -e  # 遇到错误立即退出

# 检查PyInstaller是否已安装
if ! pip show pyinstaller > /dev/null 2>&1; then
    echo "错误: 未安装PyInstaller。请运行: pip install pyinstaller"
    exit 1
fi

# 检查当前目录结构
if [ ! -d "src/nextalk_client" ]; then
    echo "错误: 未找到src/nextalk_client目录"
    echo "请确保在项目根目录中运行此脚本"
    exit 1
fi

# 创建输出目录(如不存在)
mkdir -p dist

echo "=== 开始构建NexTalk客户端应用程序 ==="
echo "构建日期: $(date)"

# 构建客户端
echo "构建客户端可执行文件..."
pyinstaller --clean \
    --name nextalk_client \
    --onefile \
    --windowed \
    --add-data "src/nextalk_client/ui/assets:ui/assets" \
    src/nextalk_client/main.py

# 构建服务器(可选)
if [ "$1" == "--with-server" ]; then
    echo "构建服务器可执行文件..."
    pyinstaller --clean \
        --name nextalk_server \
        --onefile \
        src/nextalk_server/main.py
fi

# 复制配置文件
echo "复制配置文件..."
mkdir -p dist/config
cp config/default_config.ini dist/config/

# 创建README文件
cat > dist/README.txt << EOF
NexTalk语音识别输入系统
=======================

快速入门:
1. 首次运行前，复制config目录中的默认配置到~/.config/nextalk/config.ini
2. 运行nextalk_server启动服务器
3. 运行nextalk_client启动客户端
4. 使用Ctrl+Shift+Space(默认热键)开始语音识别

更多信息请访问:
https://github.com/nexttalk/nextalk
EOF

echo "=== 构建完成 ==="
echo "输出目录: $(pwd)/dist"
echo "客户端: dist/nextalk_client"
if [ "$1" == "--with-server" ]; then
    echo "服务器: dist/nextalk_server"
fi 