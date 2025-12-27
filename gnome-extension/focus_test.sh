#!/bin/bash
#
# 焦点测试脚本 - 延时触发，验证 overlay 是否抢焦点
#
set -e

SERVICE="com.gonewx.nextalk.Panel"
PATH_OBJ="/com/gonewx/nextalk/Panel"
INTERFACE="com.gonewx.nextalk.Panel"

call_method() {
    gdbus call --session \
        --dest "$SERVICE" \
        --object-path "$PATH_OBJ" \
        --method "${INTERFACE}.$1" \
        "${@:2}" 2>/dev/null
}

echo "============================================"
echo "  焦点测试 - 验证 overlay 不抢焦点"
echo "============================================"
echo ""
echo "测试步骤："
echo "  1. 5 秒后将自动显示 Nextalk overlay"
echo "  2. 请在这 5 秒内切换到文本编辑器（如 gedit）"
echo "  3. 开始在编辑器中连续打字"
echo "  4. overlay 显示时观察："
echo "     - ✅ 打字不中断 = 测试通过"
echo "     - ❌ 打字中断/焦点跳转 = 测试失败"
echo ""
echo "准备好了吗？按 Enter 开始倒计时..."
read

echo ""
echo "⏳ 5 秒倒计时，请切换到编辑器并开始打字！"
echo ""

for i in 5 4 3 2 1; do
    echo "   $i..."
    sleep 1
done

echo ""
echo "🎤 显示 overlay！（继续打字，不要停！）"

# 显示 overlay
call_method Show true
call_method SetState "listening"
call_method SetText "🎤 正在聆听..."

sleep 3

# 切换状态
call_method SetState "processing"
call_method SetText "⏳ 识别中..."

sleep 2

# 显示结果
call_method SetState "success"
call_method SetText "✅ 测试文本"

sleep 2

# 隐藏
call_method Show false

echo ""
echo "============================================"
echo "  测试结束"
echo "============================================"
echo ""
echo "请回答："
echo "  在 overlay 显示的瞬间，你的打字是否中断了？"
echo ""
echo "  - 没中断，一直能打字 → ✅ 焦点测试通过！方案可行！"
echo "  - 中断了，焦点跳走了 → ❌ 焦点测试失败"
echo ""
