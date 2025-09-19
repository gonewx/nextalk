#!/bin/bash
# NexTalk 客户端启动脚本 (Linux/macOS)
# 自动检查环境并启动 NexTalk 客户端

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印横幅
echo "============================================================"
echo " NexTalk 语音识别系统 - 客户端启动"
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

# 检查配置文件
CONFIG_FILE="config/nextalk.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}[错误] 配置文件不存在: $CONFIG_FILE${NC}"
    echo "请先复制 config/nextalk.yaml.template 到 config/nextalk.yaml"
    exit 1
fi

# Linux 环境检查和 X11 权限设置
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${BLUE}[信息] 检测到 Linux 环境，检查 X11 权限...${NC}"

    # 检查是否在 X11 环境中
    if [ -z "$DISPLAY" ]; then
        echo -e "${YELLOW}[警告] 未检测到 DISPLAY 环境变量${NC}"
        echo "请确保在图形界面环境下运行"
    else
        echo -e "${GREEN}[信息] DISPLAY: $DISPLAY${NC}"

        # 设置 X11 权限
        echo -e "${BLUE}[信息] 设置 X11 权限...${NC}"
        xhost +local: 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[成功] X11 权限已设置${NC}"
        else
            echo -e "${YELLOW}[警告] 无法设置 X11 权限，可能需要手动运行: xhost +local:${NC}"
        fi
    fi
fi

# 检查 FunASR 服务器连接
echo -e "${BLUE}[信息] 检查 FunASR 服务器连接...${NC}"
if command -v nc &> /dev/null; then
    if nc -z localhost 10095 2>/dev/null; then
        echo -e "${GREEN}[成功] FunASR 服务器已运行 (localhost:10095)${NC}"
    else
        echo -e "${YELLOW}[警告] FunASR 服务器未运行${NC}"
        echo "请先启动 FunASR 服务器或确保服务器地址配置正确"
    fi
else
    echo -e "${YELLOW}[警告] 无法检查服务器连接 (nc 命令不可用)${NC}"
fi

echo
echo -e "${GREEN}[启动] 正在启动 NexTalk 客户端...${NC}"
echo

# 启动 NexTalk 客户端
python3 -m nextalk -c "$CONFIG_FILE"

# 检查退出码
if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[错误] 客户端启动失败，请检查错误信息${NC}"
    echo
    echo "常见解决方案："
    echo "1. 确保 FunASR 服务器正在运行"
    echo "2. 检查配置文件 $CONFIG_FILE"
    echo "3. 在 Linux 下运行: xhost +local:"
    echo "4. 查看完整安装指南: docs/INSTALL.md"
    exit 1
fi

exit 0