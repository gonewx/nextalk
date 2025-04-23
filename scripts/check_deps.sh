#!/bin/bash
#
# 检查NexTalk所需的系统依赖项
# 用法: ./check_deps.sh

# 设置严格的错误处理
set -e

# 彩色输出函数
print_green() {
    echo -e "\033[0;32m$1\033[0m"
}

print_red() {
    echo -e "\033[0;31m$1\033[0m"
}

print_yellow() {
    echo -e "\033[0;33m$1\033[0m"
}

# 显示标题
echo "==========================================="
echo "    NexTalk 系统依赖检查工具"
echo "==========================================="
echo

# 初始化状态变量
missing_deps=0
total_deps=0

# 检查命令是否存在的函数
check_command() {
    local cmd=$1
    local pkg=$2
    local desc=$3
    
    total_deps=$((total_deps+1))
    
    if command -v $cmd >/dev/null 2>&1; then
        print_green "✓ $desc 已安装 ($cmd)"
    else
        print_red "✗ $desc 未安装 ($cmd)"
        print_yellow "  建议执行: sudo apt-get install $pkg"
        missing_deps=$((missing_deps+1))
    fi
}

# 检查Python版本
check_python_version() {
    total_deps=$((total_deps+1))
    
    if command -v python3 >/dev/null 2>&1; then
        python_version=$(python3 --version | cut -d ' ' -f 2)
        if [[ $(echo "$python_version 3.10.4" | awk '{print ($1 >= $2)}') -eq 1 ]]; then
            print_green "✓ Python 版本满足要求 ($python_version)"
        else
            print_red "✗ Python 版本过低: $python_version (需要 3.10.4 或更高)"
            missing_deps=$((missing_deps+1))
        fi
    else
        print_red "✗ 未找到 Python 3"
        print_yellow "  建议执行: sudo apt-get install python3"
        missing_deps=$((missing_deps+1))
    fi
}

# 检查音频库
check_audio_libs() {
    total_deps=$((total_deps+1))
    
    if ldconfig -p | grep -q libportaudio; then
        print_green "✓ PortAudio 库已安装"
    else
        print_red "✗ PortAudio 库未安装"
        print_yellow "  建议执行: sudo apt-get install portaudio19-dev"
        missing_deps=$((missing_deps+1))
    fi
    
    # 检查ALSA
    total_deps=$((total_deps+1))
    if ldconfig -p | grep -q libasound; then
        print_green "✓ ALSA 库已安装"
    else
        print_red "✗ ALSA 库未安装"
        print_yellow "  建议执行: sudo apt-get install libasound2-dev"
        missing_deps=$((missing_deps+1))
    fi
}

# 检查CUDA支持（可选）
check_cuda_optional() {
    if command -v nvidia-smi >/dev/null 2>&1; then
        cuda_version=$(nvidia-smi | grep -oP 'CUDA Version: \K[0-9.]+')
        if [[ -n $cuda_version ]]; then
            print_green "✓ CUDA 已安装 (版本 $cuda_version)"
            # 检查CUDA兼容性
            if [[ $(echo "$cuda_version 11.2" | awk '{print ($1 >= $2)}') -eq 1 ]]; then
                print_green "  ✓ CUDA 版本与 faster-whisper 兼容"
            else
                print_yellow "  ⚠ CUDA 版本可能不兼容 faster-whisper (建议 11.2 或更高)"
            fi
        else
            print_yellow "⚠ 无法确定 CUDA 版本，请手动确认"
        fi
    else
        print_yellow "⚠ CUDA 未检测到 (可选，无CUDA将使用CPU模式)"
    fi
}

# 检查依赖项
echo "正在检查系统依赖项..."
echo

# 检查Python版本
check_python_version

# 检查文本注入工具
check_command "xdotool" "xdotool" "文本注入工具"

# 检查通知工具
check_command "notify-send" "libnotify-bin" "桌面通知工具"

# 检查音频相关库
check_audio_libs

# 检查uv包管理器（可选）
if command -v uv >/dev/null 2>&1; then
    print_green "✓ uv 包管理器已安装"
    # 检查uv版本
    uv_version=$(uv --version | head -n1)
    print_green "  版本: $uv_version"
else
    print_yellow "⚠ uv 包管理器未安装 (推荐使用，但不是必需)"
    print_yellow "  安装命令: curl -sSf https://astral.sh/uv/install.sh | sh"
fi

# 检查GPU支持（可选）
echo
echo "正在检查GPU支持（可选）..."
check_cuda_optional

# 显示结果摘要
echo
echo "==========================================="
if [ $missing_deps -eq 0 ]; then
    print_green "✓ 所有必需依赖项 ($total_deps/$total_deps) 已安装！"
    print_green "NexTalk 可以正常运行。"
    exit 0
else
    print_red "✗ 缺少 $missing_deps 个必需依赖项 (已安装 $((total_deps-missing_deps))/$total_deps)"
    print_yellow "请安装缺少的依赖项后再运行NexTalk。"
    exit 1
fi 