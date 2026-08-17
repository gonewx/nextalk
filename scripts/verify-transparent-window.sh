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

# 胶囊窗口的期望尺寸 (WindowConstants.windowWidth / windowHeight)
EXPECT_W=400
EXPECT_H=120

# ⚠️ 计数器一律用 $((x + 1)) 而不是 ((x++)):
# 后者在 x=0 时算术结果为 0 → 退出码 1 → set -e 会直接终止脚本，
# 导致"第一次 PASS 就静默退出"，验证结果永远不完整。

# ============================================
# X 环境判定：决定 X11 相关断言该 FAIL 还是 SKIP
# ============================================
# 无 X display 是**文档明确承诺的合法降级模式**（GDK 回退链会选 wayland，
# 位置功能降级但应用照常启动），此时把"看不到 X11 窗口"记为 FAIL 是误判。
# 只有"X 本应可用却看不到窗口"才是真回归。
X_AVAILABLE=false
if [ -n "${DISPLAY:-}" ] && command -v xdpyinfo >/dev/null 2>&1; then
    xdpyinfo >/dev/null 2>&1 && X_AVAILABLE=true
elif [ -n "${DISPLAY:-}" ] && [ "$HAVE_XWININFO" = "true" ]; then
    xwininfo -root >/dev/null 2>&1 && X_AVAILABLE=true
fi

if [ "$X_AVAILABLE" = "true" ]; then
    echo "   X display 可达 ($DISPLAY) —— X11 断言按 FAIL 计"
else
    echo "   ⚠️  X display 不可达 (DISPLAY='${DISPLAY:-}', XDG_SESSION_TYPE='${XDG_SESSION_TYPE:-}')"
    echo "      这是合法降级模式，X11 相关断言按 SKIP 计"
fi

# ============================================
# AC-BACKEND: GDK 后端回退链 (静态源码检查)
# ============================================
# 这条必须"会失败"：否则一次无关重构就能悄悄摘掉后端偏好，而所有验证仍报通过。
# 静态检查与运行期检查互补 —— X11 会话下即使摘掉它也照样能拿到 X11 窗口，
# 只有源码检查能稳定捕获回归；而它不依赖 X，任何环境下都能判定。
MAIN_CC="$PROJECT_DIR/voice_capsule/linux/runner/main.cc"
if grep -q 'setenv("GDK_BACKEND", "x11,wayland", 0)' "$MAIN_CC"; then
    echo "✅ AC-BACKEND: runner 层后端回退链 x11,wayland 存在"
    PASS=$((PASS + 1))
else
    echo "❌ AC-BACKEND: main.cc 缺少 setenv(\"GDK_BACKEND\", \"x11,wayland\", 0)"
    echo "   缺少它 → 原生 Wayland 下 gtk_window_move 无效，位置记忆整体失效"
    echo "   注意不要退回仅 x11: DISPLAY 有值但不可达时会 gtk_init_check FAILED"
    FAIL=$((FAIL + 1))
fi

# ============================================
# AC-EXIT-FLUSH: 退出路径落盘链 (静态源码检查)
# ============================================
# 保证"拖动后立刻退出不丢位置"的是两处 await。其中 tray_service 那一跳发生在
# exit(0) 之前，属进程级时序，单元测试无法覆盖 —— 只能静态守。
# （window_service 那一跳已由 test/services/flutter_window_backend_wiring_test.dart
#   的 "退出链落盘 (WindowService 层)" 覆盖。）
TRAY_SVC="$PROJECT_DIR/voice_capsule/lib/services/tray_service.dart"
WIN_SVC="$PROJECT_DIR/voice_capsule/lib/services/window_service.dart"
EXIT_FLUSH_OK=true
grep -q 'await WindowService.instance.dispose()' "$TRAY_SVC" || EXIT_FLUSH_OK=false
grep -q 'await _backend?.dispose()' "$WIN_SVC" || EXIT_FLUSH_OK=false
if [ "$EXIT_FLUSH_OK" = "true" ]; then
    echo "✅ AC-EXIT-FLUSH: 退出路径两处 await 均在位"
    PASS=$((PASS + 1))
else
    echo "❌ AC-EXIT-FLUSH: 退出路径缺少 await，exit(0) 可能先于位置写入完成"
    echo "   需要: tray_service.dart 的 await WindowService.instance.dispose()"
    echo "   需要: window_service.dart 的 await _backend?.dispose()"
    FAIL=$((FAIL + 1))
fi

# 唤起胶囊：未唤起时窗口尚未 map，X11 报的是 pre-map 几何（实测 +58+0），
# 位置断言必须在唤起之后做。
echo "   唤起胶囊..."
"$SCRIPT_DIR/nextalk-toggle.sh" show >/dev/null 2>&1 || true
sleep 2

# 查找窗口
# ⚠️ 必须按应用真实标识 com.gonewx.nextalk 查找 (APPLICATION_ID / StartupWMClass)。
# 旧脚本搜 "voice_capsule" 实测匹配 0 个，找不到时只 SKIP 不 FAIL，等于永不报错。
# ⚠️ 同一 WM_CLASS 下实测有 3 个窗口 (16x16 托盘、10x10 辅助、400x120 胶囊)，
# 必须挑出 400x120 那个，否则尺寸/位置断言会误判。
WINDOW_ID=""
if [ "$HAVE_XWININFO" = "true" ]; then
    WINDOW_ID=$(xwininfo -root -tree 2>/dev/null |
        grep "com.gonewx.nextalk" |
        grep -E "[[:space:]]${EXPECT_W}x${EXPECT_H}\+" |
        grep -oE '0x[0-9a-f]+' | head -1 || echo "")
fi
if [ -z "$WINDOW_ID" ] && [ "$HAVE_XDOTOOL" = "true" ]; then
    # xwininfo 不可用时用 xdotool 逐个候选筛尺寸
    for CAND in $(xdotool search --class "com.gonewx.nextalk" 2>/dev/null || true); do
        CW=$(xdotool getwindowgeometry "$CAND" 2>/dev/null | awk '/Geometry:/ {split($2,a,"x"); print a[1]}')
        if [ "$CW" = "$EXPECT_W" ]; then
            WINDOW_ID=$CAND
            break
        fi
    done
fi

if [ -z "$WINDOW_ID" ]; then
    if [ "$X_AVAILABLE" != "true" ]; then
        # 合法降级：没有可达的 X display，应用回落 wayland，本就看不到 X11 窗口
        echo "⚠️  AC-BACKEND-RUNTIME, AC1, AC3, AC-POSITION, AC7: 跳过 (无可达 X display)"
        SKIP=$((SKIP + 5))
    elif [ "$HAVE_XWININFO" != "true" ] && [ "$HAVE_XDOTOOL" != "true" ]; then
        # 工具缺失 ≠ 后端回归，不能误诊
        echo "⚠️  AC-BACKEND-RUNTIME, AC1, AC3, AC-POSITION, AC7: 跳过 (缺少 xwininfo/xdotool)"
        echo "      安装命令: sudo apt install x11-utils xdotool"
        SKIP=$((SKIP + 5))
    else
        # ❌ X 可达、工具齐备却看不到窗口 = 应用没跑在 x11/XWayland 后端上
        # （或未成功唤起），正是本项要防的回归
        echo "❌ AC-BACKEND-RUNTIME: X11 下找不到 com.gonewx.nextalk 的 ${EXPECT_W}x${EXPECT_H} 窗口"
        echo "   X display 可达且工具齐备，说明应用未运行在 x11/XWayland 后端 (或胶囊未成功唤起)"
        echo "   排查: xwininfo -root -tree | grep com.gonewx.nextalk"
        FAIL=$((FAIL + 1))
    fi
else
    echo "✅ AC-BACKEND-RUNTIME: X11 下可见胶囊窗口 ($WINDOW_ID)"
    PASS=$((PASS + 1))

    # AC1: 验证无边框 (使用 xwininfo)
    if [ "$HAVE_XWININFO" = "true" ]; then
        BORDER_WIDTH=$(xwininfo -id "$WINDOW_ID" 2>/dev/null | grep "Border width:" | awk '{print $3}' || echo "-1")
        if [ "$BORDER_WIDTH" = "0" ]; then
            echo "✅ AC1: 无边框验证通过 (Border width: 0)"
            PASS=$((PASS + 1))
        else
            echo "❌ AC1: 边框检测失败 (Border width: $BORDER_WIDTH)"
            FAIL=$((FAIL + 1))
        fi

        # AC3: 验证尺寸 (使用 xwininfo)
        GEOM=$(xwininfo -id "$WINDOW_ID" 2>/dev/null | grep -E "Width:|Height:" || echo "")
        WIDTH=$(echo "$GEOM" | grep "Width:" | awk '{print $2}')
        HEIGHT=$(echo "$GEOM" | grep "Height:" | awk '{print $2}')
        if [ "$WIDTH" = "$EXPECT_W" ] && [ "$HEIGHT" = "$EXPECT_H" ]; then
            echo "✅ AC3: 尺寸验证通过 (${EXPECT_W}x${EXPECT_H})"
            PASS=$((PASS + 1))
        else
            echo "❌ AC3: 尺寸不符 (实际: ${WIDTH}x${HEIGHT})"
            FAIL=$((FAIL + 1))
        fi

        # AC-POSITION: 窗口几何不得为 +0+0
        # Wayland 原生后端下 gtk_window_move 是 no-op、位置恒为 (0,0)，
        # 这里正是把那个伪值当成 FAIL 信号
        POS_X=$(xwininfo -id "$WINDOW_ID" 2>/dev/null | awk '/Absolute upper-left X:/ {print $NF}')
        POS_Y=$(xwininfo -id "$WINDOW_ID" 2>/dev/null | awk '/Absolute upper-left Y:/ {print $NF}')
        if [ -z "$POS_X" ] || [ -z "$POS_Y" ]; then
            echo "❌ AC-POSITION: 无法读取窗口几何"
            FAIL=$((FAIL + 1))
        elif [ "$POS_X" = "0" ] && [ "$POS_Y" = "0" ]; then
            echo "❌ AC-POSITION: 窗口几何为 +0+0 (Wayland 伪值签名，定位 API 未生效)"
            FAIL=$((FAIL + 1))
        else
            echo "✅ AC-POSITION: 窗口几何为 +${POS_X}+${POS_Y} (非 +0+0)"
            PASS=$((PASS + 1))
        fi
    else
        echo "⚠️  AC1, AC3, AC-POSITION: 跳过 (需要 xwininfo)"
        SKIP=$((SKIP + 3))
    fi

    # AC7: 验证始终在最前 (检查窗口类型)
    if [ "$HAVE_XPROP" = "true" ]; then
        ABOVE=$(xprop -id "$WINDOW_ID" 2>/dev/null | grep "_NET_WM_STATE_ABOVE" || echo "")
        if [ -n "$ABOVE" ]; then
            echo "✅ AC7: 始终在最前验证通过"
            PASS=$((PASS + 1))
        else
            echo "⚠️  AC7: 无法自动验证始终在最前，请手动确认"
            SKIP=$((SKIP + 1))
        fi
    else
        echo "⚠️  AC7: 跳过 (需要 xprop)"
        SKIP=$((SKIP + 1))
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

# 非交互模式 (CI / NONINTERACTIVE=1 / stdin 不是终端) 不阻塞等待
if [ "${NONINTERACTIVE:-0}" != "1" ] && [ -t 0 ]; then
    echo "按 Enter 结束测试..."
    read
fi

# 清理
kill $APP_PID 2>/dev/null || true
echo "✅ 测试结束"

# 有失败项就以非零退出码结束，让 CI / 调用方能真正感知 FAIL
if [ "$FAIL" -gt 0 ]; then
    echo "❌ 存在 $FAIL 项失败"
    exit 1
fi
# 一条都没通过（全 SKIP）时不能报成功：那说明什么都没验证到，
# 静默返回 0 会让"验证通过"变成假信号
if [ "$PASS" -eq 0 ]; then
    echo "⚠️  没有任何断言通过 ($SKIP 项跳过) —— 本次未验证到任何东西"
    echo "   补齐依赖 (x11-utils / xdotool) 或在可达 X display 的会话中重跑"
    exit 2
fi
exit 0
