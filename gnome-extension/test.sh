#!/bin/bash
#
# Nextalk GNOME Extension 快速测试脚本 (使用 gdbus)
# 不需要 Python，直接使用系统自带的 gdbus 命令
#
set -e

SERVICE="com.gonewx.nextalk.Panel"
PATH_OBJ="/com/gonewx/nextalk/Panel"
INTERFACE="com.gonewx.nextalk.Panel"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_help() {
    echo "Nextalk GNOME Extension 快速测试"
    echo ""
    echo "用法: $0 <命令>"
    echo ""
    echo "命令:"
    echo "  show        显示胶囊"
    echo "  hide        隐藏胶囊"
    echo "  text <文本>  设置显示文本"
    echo "  listening   设置为 listening 状态"
    echo "  processing  设置为 processing 状态"
    echo "  success     设置为 success 状态"
    echo "  idle        设置为 idle 状态"
    echo "  info        获取当前状态"
    echo "  demo        运行演示"
    echo "  check       检查扩展状态"
    echo ""
}

call_method() {
    local method=$1
    shift
    gdbus call --session \
        --dest "$SERVICE" \
        --object-path "$PATH_OBJ" \
        --method "${INTERFACE}.${method}" \
        "$@" 2>/dev/null
}

check_extension() {
    echo "检查扩展状态..."
    echo ""

    # 检查扩展是否安装
    if gnome-extensions show "nextalk@gonewx.com" &>/dev/null; then
        echo -e "${GREEN}✅ 扩展已安装${NC}"
        gnome-extensions show "nextalk@gonewx.com" | grep -E "State|Version"
    else
        echo -e "${RED}❌ 扩展未安装${NC}"
        echo "   请先运行: ./install.sh"
        return 1
    fi

    echo ""

    # 检查 D-Bus 服务
    if gdbus introspect --session --dest "$SERVICE" --object-path "$PATH_OBJ" &>/dev/null; then
        echo -e "${GREEN}✅ D-Bus 服务可用${NC}"
    else
        echo -e "${RED}❌ D-Bus 服务不可用${NC}"
        echo "   扩展可能未正确加载，请尝试:"
        echo "   1. 注销并重新登录"
        echo "   2. 查看日志: journalctl -f /usr/bin/gnome-shell | grep -i nextalk"
        return 1
    fi

    echo ""
    echo "一切就绪！可以运行测试了。"
}

run_demo() {
    echo "🎬 运行演示..."
    echo ""

    echo "→ 显示胶囊"
    call_method Show true

    echo "→ 设置状态: idle"
    call_method SetState "idle"
    call_method SetText "准备就绪"
    sleep 1

    echo "→ 设置状态: listening"
    call_method SetState "listening"
    call_method SetText "🎤 正在聆听..."
    sleep 2

    echo "→ 设置状态: processing"
    call_method SetState "processing"
    call_method SetText "⏳ 识别中..."
    sleep 1

    echo "→ 设置状态: success"
    call_method SetState "success"
    call_method SetText "✅ 你好世界"
    sleep 2

    echo "→ 隐藏胶囊"
    call_method Show false

    echo ""
    echo "✅ 演示完成!"
}

case "${1:-help}" in
    show)
        call_method Show true
        echo "胶囊已显示"
        ;;
    hide)
        call_method Show false
        echo "胶囊已隐藏"
        ;;
    text)
        if [ -z "$2" ]; then
            echo "用法: $0 text <文本>"
            exit 1
        fi
        call_method SetText "$2"
        echo "文本已设置: $2"
        ;;
    listening|processing|success|idle)
        call_method SetState "$1"
        echo "状态已设置: $1"
        ;;
    info)
        result=$(call_method GetInfo)
        echo "当前状态: $result"
        ;;
    demo)
        run_demo
        ;;
    check)
        check_extension
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "未知命令: $1"
        show_help
        exit 1
        ;;
esac
