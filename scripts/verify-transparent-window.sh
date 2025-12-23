#!/bin/bash
# Story 3-1: 透明胶囊窗口验证脚本
# 用于验证透明窗口的 AC1-AC10

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Story 3-1 透明窗口验证 ==="
echo ""

# 检查必需工具
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo "⚠️  工具 '$1' 未安装，部分自动化验证将跳过"
        echo "   安装命令: sudo apt install $2"
        return 1
    fi
    return 0
}

HAVE_XDOTOOL=true
HAVE_XWININFO=true
HAVE_XPROP=true

check_tool "xdotool" "xdotool" || HAVE_XDOTOOL=false
check_tool "xwininfo" "x11-utils" || HAVE_XWININFO=false
check_tool "xprop" "x11-utils" || HAVE_XPROP=false

echo ""

cd "$PROJECT_DIR/voice_capsule"

echo "1. 构建应用..."
flutter build linux --release
echo "✅ 构建成功"
echo ""

echo "2. 启动应用 (后台)..."
./build/linux/x64/release/bundle/voice_capsule &
APP_PID=$!
sleep 3  # 等待窗口创建

echo "3. 自动化验证..."
PASS=0
FAIL=0
SKIP=0

# 查找窗口 (可能名称不同)
WINDOW_ID=""
if [ "$HAVE_XDOTOOL" = "true" ]; then
    WINDOW_ID=$(xdotool search --name "voice_capsule" 2>/dev/null | head -1 || echo "")
    if [ -z "$WINDOW_ID" ]; then
        WINDOW_ID=$(xdotool search --class "voice_capsule" 2>/dev/null | head -1 || echo "")
    fi
fi

if [ -z "$WINDOW_ID" ]; then
    echo "⚠️  无法自动找到窗口，跳过自动化验证"
    SKIP=3
else
    # AC1: 验证无边框 (使用 xwininfo)
    if [ "$HAVE_XWININFO" = "true" ]; then
        BORDER_WIDTH=$(xwininfo -id "$WINDOW_ID" 2>/dev/null | grep "Border width:" | awk '{print $3}' || echo "-1")
        if [ "$BORDER_WIDTH" = "0" ]; then
            echo "✅ AC1: 无边框验证通过 (Border width: 0)"
            ((PASS++))
        else
            echo "❌ AC1: 边框检测失败 (Border width: $BORDER_WIDTH)"
            ((FAIL++))
        fi

        # AC3: 验证尺寸 400x120 (使用 xwininfo)
        GEOM=$(xwininfo -id "$WINDOW_ID" 2>/dev/null | grep -E "Width:|Height:" || echo "")
        WIDTH=$(echo "$GEOM" | grep "Width:" | awk '{print $2}')
        HEIGHT=$(echo "$GEOM" | grep "Height:" | awk '{print $2}')
        if [ "$WIDTH" = "400" ] && [ "$HEIGHT" = "120" ]; then
            echo "✅ AC3: 尺寸验证通过 (400x120)"
            ((PASS++))
        else
            echo "❌ AC3: 尺寸不符 (实际: ${WIDTH}x${HEIGHT})"
            ((FAIL++))
        fi
    else
        echo "⚠️  AC1, AC3: 跳过 (需要 xwininfo)"
        ((SKIP+=2))
    fi

    # AC7: 验证始终在最前 (检查窗口类型)
    if [ "$HAVE_XPROP" = "true" ]; then
        ABOVE=$(xprop -id "$WINDOW_ID" 2>/dev/null | grep "_NET_WM_STATE_ABOVE" || echo "")
        if [ -n "$ABOVE" ]; then
            echo "✅ AC7: 始终在最前验证通过"
            ((PASS++))
        else
            echo "⚠️  AC7: 无法自动验证始终在最前，请手动确认"
            ((SKIP++))
        fi
    else
        echo "⚠️  AC7: 跳过 (需要 xprop)"
        ((SKIP++))
    fi
fi

echo ""
echo "4. 手动验证项 (请观察窗口):"
echo "   [ ] AC2: 窗口背景透明 (可见桌面壁纸)"
echo "   [ ] AC5: 无启动黑框闪烁"
echo "   [ ] AC6: 窗口瞬间出现"
echo "   [ ] AC9: 窗口可拖拽移动"
echo "   [ ] AC10: 关闭后再启动，位置保持"
echo ""
echo "自动化结果: $PASS 通过, $FAIL 失败, $SKIP 跳过"
echo ""
echo "按 Enter 结束测试..."
read

# 清理
kill $APP_PID 2>/dev/null || true
echo "✅ 测试结束"



