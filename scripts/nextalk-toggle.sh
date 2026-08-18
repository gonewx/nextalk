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
  # 发送命令并**等应用层回 ACK**，而不是只看 write 有没有成功。
  #
  # 为什么非要 ACK: Unix socket 的 listen backlog 会让 connect()/sendall() 在
  # 完全没人 accept 的情况下照样成功——内核只负责把连接塞进队列。于是当
  # Dart engine 已死、进程空壳仍持有 socket 时，"写成功"被误判成"应用处理了"，
  # 脚本 exit 0 再也不走下面的冷启动回退，用户按几十次都是零反应且永不自愈
  # (2026-08-18 实测: 18 次按键全部堆在 accept 队列, ss 显示 Recv-Q=18)。
  #
  # 退出码约定: 0=已送达或实例确认健在  1=无可用实例, 由本脚本冷启动
  python3 - "$SOCK" "$CMD" <<'PYEOF'
import os, signal, socket, struct, sys, time

ACK = 0x06            # 与 single_instance.dart 的 SingleInstance.ackByte 对齐
ACK_TIMEOUT = 0.6     # 正常应用毫秒级回 ACK; 留足余量给正在推理的忙实例

EXIT_DELIVERED = 0    # 命令已被应用消费, 或实例健在(仅未回 ACK)
EXIT_NEED_START = 1   # 无可用实例, 调用方应冷启动


def send_and_wait_ack(path, cmd):
    """发送命令并等 ACK。True=收到 ACK; False=连上但没等到; OSError=连不上。"""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.settimeout(1.0)
        s.connect(path)
        data = cmd.encode("utf-8")
        s.sendall(struct.pack("<I", len(data)) + data)
        s.settimeout(ACK_TIMEOUT)
        try:
            # recv 返回 b"" 表示对端已关闭, 同样算没等到 ACK
            return s.recv(1) == bytes([ACK])
        except socket.timeout:
            return False
    finally:
        s.close()


def listening_inode(path):
    """取该路径上处于 LISTEN 的 socket inode。

    同一路径在 /proc/net/unix 里会有多行: LISTEN 的那行 St=01, 已建立的连接
    St=03。只有 LISTEN 那行的持有者才是主实例。
    字段: Num RefCount Protocol Flags Type St Inode Path
    """
    try:
        with open("/proc/net/unix") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 8 and parts[7] == path and parts[5] == "01":
                    return parts[6]
    except OSError:
        pass
    return None


def holder_pid(inode):
    """遍历 /proc/*/fd 找持有该 inode 的进程 (unix socket 的 fd 只暴露 inode)。"""
    target = "socket:[%s]" % inode
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        fd_dir = "/proc/%s/fd" % name
        try:
            for fd in os.listdir(fd_dir):
                try:
                    if os.readlink(os.path.join(fd_dir, fd)) == target:
                        return int(name)
                except OSError:
                    continue        # fd 瞬时消失, 跳过
        except OSError:
            continue                # 非本用户进程或已退出, 跳过
    return None


def thread_names(pid):
    names = []
    try:
        for tid in os.listdir("/proc/%d/task" % pid):
            try:
                with open("/proc/%d/task/%s/comm" % (pid, tid)) as f:
                    names.append(f.read().strip())
            except OSError:
                continue
    except OSError:
        pass
    return names


def process_exe(pid):
    try:
        return os.path.basename(os.readlink("/proc/%d/exe" % pid))
    except OSError:
        return ""


def is_dead_shell(pid):
    """持有 socket 的进程是否是 "Dart engine 已死、只剩 GTK 主循环" 的空壳。

    只有返回 True 才允许清理。**任何拿不准的情形都返回 False**——误杀健康实例
    会让用户每次按快捷键都重启一次应用, 比不修更糟。
    """
    if "nextalk" not in process_exe(pid):
        # 读不到(权限/已退出), 或该路径被别的程序占用: 绝不动手
        return False

    names = thread_names(pid)
    # comm 上限 15 字符, io.flutter.raster 会被截成 io.flutter.rast;
    # io.flutter.ui 只 13 字符, 不受截断影响。
    if not any(n.startswith("io.flutter.") for n in names):
        # 连一个 io.flutter.* 都没有: 大概是 Flutter 改了线程命名体系,
        # 此时无从判断存活, 宁可退化成旧行为也不误杀。
        return False
    # engine 的其它线程都在、独独 UI 线程没了 —— 正是 Dart isolate 已死的签名
    return "io.flutter.ui" not in names


def reap(pid, path):
    """终止空壳并清掉 socket 文件, 让调用方能冷启动。"""
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    for _ in range(20):             # 最多等 2s
        time.sleep(0.1)
        if not os.path.exists("/proc/%d" % pid):
            break
    else:
        try:
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.2)
        except OSError:
            pass
    try:
        os.unlink(path)
    except OSError:
        pass                        # 已被新实例接管或本就不存在


def main(argv):
    path, cmd = argv[1], argv[2]

    try:
        acked = send_and_wait_ack(path, cmd)
    except OSError:
        # 连不上: 残留 socket 文件, 冷启动时 bind 会自行清理
        return EXIT_NEED_START

    if acked:
        return EXIT_DELIVERED

    # 连上却没等到 ACK。两种可能: 旧版应用不回 ACK(健康), 或空壳(内核收下无人处理)。
    inode = listening_inode(path)
    pid = holder_pid(inode) if inode else None
    if pid is None:
        return EXIT_NEED_START      # 没人持有 LISTEN, 视为无实例

    if not is_dead_shell(pid):
        return EXIT_DELIVERED       # 实例健在(含未回 ACK 的旧版), 不误杀

    sys.stderr.write(
        "[nextalk-toggle] 检测到 Dart engine 已死的空壳进程 %d, 清理后冷启动\n" % pid)
    reap(pid, path)
    return EXIT_NEED_START


# __name__ 守卫让测试能 import 这些函数而不触发主流程
# (heredoc 经 stdin 交给 python 时 __name__ 就是 __main__, 正常执行)
if __name__ == "__main__":
    sys.exit(main(sys.argv))
PYEOF
  if [ $? -eq 0 ]; then
    exit 0
  fi
  # 退出码非 0: 无可用实例(连不上/空壳已清理), 继续走下面的冷启动
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
