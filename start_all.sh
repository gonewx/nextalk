#!/bin/bash
# NexTalk 一键启动脚本 (Linux/macOS)
# 自动启动 FunASR 服务器和 NexTalk 客户端

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印横幅
echo "============================================================"
echo " NexTalk 语音识别系统 - 一键启动"
echo "============================================================"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Python 3${NC}"
    echo "请先安装 Python 3.8+"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 使用 Python 脚本
python3 start_all.py

# 检查退出码
if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[错误] 启动失败，请检查错误信息${NC}"
    exit 1
fi

exit 0