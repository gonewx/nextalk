#!/usr/bin/env bash
# 轻量级 Nextalk 触发器 —— 推荐将系统快捷键绑定到本脚本而非 `nextalk --toggle`。
#
# 原理：`nextalk --toggle` 需要冷启动整个 Flutter 二进制（加载 GTK/引擎动态库）
# 才能向运行中的实例发送一条 socket 命令，页缓存冷时可达数百毫秒到秒级；
# 本脚本用 python3 直接向单实例 socket 写入命令（协议：4字节LE长度 + UTF-8 文本），
# 耗时约 20-50ms。仅当应用未运行时才回退到启动完整应用。
#
# 用法: nextalk-toggle.sh [toggle|show|hide]   (默认 toggle)

set -u

CMD="${1:-toggle}"
SOCK="${XDG_RUNTIME_DIR:-/tmp}/nextalk.sock"

if [ -S "$SOCK" ]; then
  if python3 - "$SOCK" "$CMD" <<'PYEOF'
import socket, struct, sys
path, cmd = sys.argv[1], sys.argv[2]
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(1.0)
    s.connect(path)
    data = cmd.encode("utf-8")
    s.sendall(struct.pack("<I", len(data)) + data)
    s.close()
except OSError:
    sys.exit(1)
PYEOF
  then
    exit 0
  fi
  # socket 文件存在但连接失败（残留文件），走完整启动
fi

# 无运行实例：启动完整应用（--hide 时无事可做）
if [ "$CMD" = "hide" ]; then
  exit 0
fi
# 启动应用，注入 GDK 后端回退链 x11,wayland。
#
# 为什么优先 x11: Wayland 原生后端下窗口定位 API 不可用（gtk_window_move no-op、
# gtk_window_get_position 恒为 0,0），胶囊位置与位置记忆全部失效。.desktop 早已
# 走 x11 路线，本脚本的冷启动回退曾是绕过它的漏口。
#
# 为什么是回退链而不是自己探测 $DISPLAY: "x11,wayland" 由 GDK 依次尝试并自行
# 判定可用性。实测 DISPLAY=:99（有值但 X server 不可达，纯 Wayland 会话的残留
# DISPLAY 或失效的 SSH X 转发都是这种）下，"仅 x11" 会 gtk_init_check FAILED
# 直接起不来，而回退链正常回落 wayland。可启动性优先于位置正确性。
#
# ${GDK_BACKEND:-...} 只在未显式设置时注入，且把空串视同未设置
# （与 voice_capsule/linux/runner/main.cc 的 overwrite=0 语义一致）。
#
# 这是过渡期双保险 —— runner 层已内建同一条回退链，等所有部署都换成新二进制后
# 本函数可以移除。
run_app() {
  exec env GDK_BACKEND="${GDK_BACKEND:-x11,wayland}" "$@"
}

if command -v nextalk >/dev/null 2>&1; then
  run_app nextalk "--${CMD}"
fi
run_app /opt/nextalk/nextalk "--${CMD}"
