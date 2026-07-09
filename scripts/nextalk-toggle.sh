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
if command -v nextalk >/dev/null 2>&1; then
  exec nextalk "--${CMD}"
fi
exec /opt/nextalk/nextalk "--${CMD}"
