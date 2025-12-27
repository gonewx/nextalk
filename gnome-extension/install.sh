#!/bin/bash
#
# Nextalk GNOME Shell Extension 安装脚本
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTENSION_UUID="nextalk@gonewx.com"
EXTENSION_SRC="$SCRIPT_DIR/$EXTENSION_UUID"
EXTENSION_DST="$HOME/.local/share/gnome-shell/extensions/$EXTENSION_UUID"

echo "============================================"
echo "  Nextalk GNOME Shell Extension 安装器"
echo "============================================"
echo ""

# 检查是否在 GNOME 环境
if [ "$XDG_CURRENT_DESKTOP" != "GNOME" ] && [ "$DESKTOP_SESSION" != "gnome" ]; then
    echo "⚠️  警告: 当前可能不是 GNOME 桌面环境"
    echo "   检测到: XDG_CURRENT_DESKTOP=$XDG_CURRENT_DESKTOP"
    echo ""
fi

# 检查是否在 Wayland
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    echo "✅ 检测到 Wayland 会话"
else
    echo "⚠️  警告: 当前不是 Wayland 会话 (XDG_SESSION_TYPE=$XDG_SESSION_TYPE)"
    echo "   此扩展主要用于解决 Wayland 下的焦点问题"
    echo ""
fi

# 检查源文件
if [ ! -d "$EXTENSION_SRC" ]; then
    echo "❌ 错误: 找不到扩展源文件: $EXTENSION_SRC"
    exit 1
fi

echo "📦 安装扩展..."
echo "   源: $EXTENSION_SRC"
echo "   目标: $EXTENSION_DST"
echo ""

# 创建目标目录
mkdir -p "$EXTENSION_DST"

# 复制文件
cp -r "$EXTENSION_SRC"/* "$EXTENSION_DST/"

echo "✅ 文件已复制"
echo ""

# 检查 GNOME Shell 版本
GNOME_VERSION=$(gnome-shell --version 2>/dev/null | grep -oP '\d+' | head -1 || echo "unknown")
echo "📊 GNOME Shell 版本: $GNOME_VERSION"

# 启用扩展
echo ""
echo "🔧 启用扩展..."

if command -v gnome-extensions &> /dev/null; then
    # 先禁用再启用（确保重新加载）
    gnome-extensions disable "$EXTENSION_UUID" 2>/dev/null || true
    gnome-extensions enable "$EXTENSION_UUID" 2>/dev/null || true
    echo "✅ 扩展已启用"
else
    echo "⚠️  无法自动启用扩展，请手动启用："
    echo "   gnome-extensions enable $EXTENSION_UUID"
fi

echo ""
echo "============================================"
echo "  安装完成!"
echo "============================================"
echo ""
echo "后续步骤:"
echo ""
echo "  1. 如果扩展未生效，请重启 GNOME Shell:"
echo "     - Wayland: 需要注销并重新登录"
echo "     - X11: 按 Alt+F2, 输入 'r', 按 Enter"
echo ""
echo "  2. 验证扩展状态:"
echo "     gnome-extensions show $EXTENSION_UUID"
echo ""
echo "  3. 查看日志:"
echo "     journalctl -f -o cat /usr/bin/gnome-shell | grep -i nextalk"
echo ""
echo "  4. 运行测试:"
echo "     cd $SCRIPT_DIR && python3 test_dbus_client.py demo"
echo ""
echo "  5. 焦点测试 (关键验证):"
echo "     cd $SCRIPT_DIR && python3 test_dbus_client.py focus-test"
echo ""
