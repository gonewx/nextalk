#!/bin/bash
#
# Nextalk GNOME Shell Extension 卸载脚本
#
set -e

EXTENSION_UUID="nextalk@gonewx.com"
EXTENSION_DST="$HOME/.local/share/gnome-shell/extensions/$EXTENSION_UUID"

echo "============================================"
echo "  Nextalk GNOME Shell Extension 卸载器"
echo "============================================"
echo ""

# 禁用扩展
if command -v gnome-extensions &> /dev/null; then
    echo "🔧 禁用扩展..."
    gnome-extensions disable "$EXTENSION_UUID" 2>/dev/null || true
fi

# 删除文件
if [ -d "$EXTENSION_DST" ]; then
    echo "🗑️  删除扩展文件..."
    rm -rf "$EXTENSION_DST"
    echo "✅ 扩展已卸载"
else
    echo "⚠️  扩展目录不存在: $EXTENSION_DST"
fi

echo ""
echo "卸载完成!"
echo ""
echo "如需完全清理，请重启 GNOME Shell:"
echo "  - Wayland: 注销并重新登录"
echo "  - X11: 按 Alt+F2, 输入 'r', 按 Enter"
echo ""
