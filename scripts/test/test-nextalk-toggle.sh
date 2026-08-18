#!/usr/bin/env bash
# nextalk-toggle.sh 的判定逻辑测试。
#
# 为什么单独测: 该脚本是快捷键的唯一入口, 它一旦把"内核收下连接"误判成
# "应用处理了命令", 用户就会陷入"按键完全没反应且永不自愈"(2026-08-18 故障)。
# 反过来, 若把健康实例误判成空壳, 每次按快捷键都会重启应用 —— 比不修更糟。
# 两个方向都必须有回归护栏。
#
# 用法: bash scripts/test/test-nextalk-toggle.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOGGLE="$SCRIPT_DIR/scripts/nextalk-toggle.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
ng() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

# 双层隔离, 缺一不可:
#   XDG_RUNTIME_DIR -> 脚本只碰 $WORK 下的假 socket, 绝不动用户真实运行的实例
#   PATH 里的假 nextalk -> 冷启动分支只会 exec 这个桩, 不会真拉起 /opt/nextalk/nextalk
export XDG_RUNTIME_DIR="$WORK"
mkdir -p "$WORK/bin"
cat > "$WORK/bin/nextalk" <<'EOF'
#!/usr/bin/env bash
echo "COLD_START_INVOKED:$1"
EOF
chmod +x "$WORK/bin/nextalk"
export PATH="$WORK/bin:$PATH"

# 把 heredoc 里的 python 抽成模块, 供纯函数测试 import
# (脚本用 __name__ 守卫, import 时不会触发主流程)
sed -n "/<<'PYEOF'/,/^PYEOF$/p" "$TOGGLE" | sed '1d;$d' > "$WORK/toggle_logic.py"

echo "== 1. 语法 =="
bash -n "$TOGGLE" && ok "bash 语法" || ng "bash 语法"
python3 -m py_compile "$WORK/toggle_logic.py" && ok "python 语法" || ng "python 语法"

echo "== 2. 空壳判定 (is_dead_shell) =="
python3 - "$WORK" <<'PYEOF'
import sys, types
sys.path.insert(0, sys.argv[1])
import toggle_logic as t

failures = []


def check(name, cond):
    print(("  ✅ " if cond else "  ❌ ") + name)
    if not cond:
        failures.append(name)


def stub(exe, threads):
    t.process_exe = lambda pid: exe
    t.thread_names = lambda pid: threads


# 本次故障的真实现场 (PID 13473): engine 其它线程在, io.flutter.ui 全无
stub("nextalk", ["nextalk", "gmain", "gdbus", "io.flutter.rast",
                 "io.flutter.io", "dart:io EventHa", "DartWorker"])
check("真实空壳现场判定为空壳", t.is_dead_shell(1) is True)

# 健康实例的真实现场 (PID 39231): 有多个 io.flutter.ui
stub("nextalk", ["nextalk", "gmain", "io.flutter.io", "io.flutter.rast",
                 "io.flutter.ui", "io.flutter.ui", "io.flutter.ui"])
check("健康实例不被判定为空壳", t.is_dead_shell(1) is False)

# 未来 Flutter 若改线程命名: 一个 io.flutter.* 都没有 -> 不敢判定, 保守放过
stub("nextalk", ["nextalk", "gmain", "some.new.ui.thread"])
check("线程命名体系变更时保守放过", t.is_dead_shell(1) is False)

# socket 路径被别的程序占用 -> 绝不动手
stub("python3", ["python3"])
check("非 nextalk 进程绝不动手", t.is_dead_shell(1) is False)

# 读不到 exe (权限/已退出) -> 不碰
stub("", ["io.flutter.rast"])
check("读不到 exe 时不动手", t.is_dead_shell(1) is False)

sys.exit(1 if failures else 0)
PYEOF
if [ $? -eq 0 ]; then PASS=$((PASS + 5)); else FAIL=$((FAIL + 1)); fi

echo "== 3. 端到端: 只 listen 不 accept 的空壳 socket =="
# 这正是故障机制: connect+sendall 全部成功, 但没人 accept。
# 持有者是 python(非 nextalk), 按安全设计不该被杀, 脚本应判定"实例健在"退出 0
# 而不是误杀 —— 用它守住"绝不误杀非 nextalk 进程"这条线。
python3 - "$WORK/nextalk.sock" <<'PYEOF' &
import socket, sys, time
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1]); s.listen(128)   # 绝不 accept
time.sleep(20)
PYEOF
HOLDER=$!
sleep 1.5

START=$(date +%s%N)
timeout 15 "$TOGGLE" toggle
RC=$?
ELAPSED_MS=$(( ($(date +%s%N) - START) / 1000000 ))

if [ "$RC" -eq 0 ]; then
  ok "非 nextalk 持有者未被误杀 (退出码 0)"
else
  ng "非 nextalk 持有者被误判 (退出码 $RC)"
fi
if kill -0 $HOLDER 2>/dev/null; then
  ok "持有进程仍存活 (未被误杀)"
else
  ng "持有进程被误杀"
fi
# ACK 超时 0.6s + 判定开销, 不该拖到秒级以上
if [ "$ELAPSED_MS" -lt 4000 ]; then
  ok "未收到 ACK 时的判定耗时可接受 (${ELAPSED_MS}ms)"
else
  ng "判定耗时过长 (${ELAPSED_MS}ms)"
fi
kill $HOLDER 2>/dev/null; wait $HOLDER 2>/dev/null

echo "== 4. 残留 socket 文件 (无人持有) 应要求冷启动 =="
rm -f "$WORK/nextalk.sock"
python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])   # bind 后立刻关闭, 留下残留文件
s.close()
" "$WORK/nextalk.sock"
OUT=$(timeout 15 "$TOGGLE" toggle 2>&1)
if echo "$OUT" | grep -q "COLD_START_INVOKED:--toggle"; then
  ok "残留 socket 触发冷启动并透传 --toggle"
else
  ng "残留 socket 未正确冷启动 (输出: $OUT)"
fi

echo "== 5. hide 在无实例时不应拉起应用 =="
rm -f "$WORK/nextalk.sock"
OUT=$(timeout 15 "$TOGGLE" hide 2>&1)
if echo "$OUT" | grep -q "COLD_START_INVOKED"; then
  ng "hide 误拉起应用"
else
  ok "hide 无实例时静默退出"
fi

echo "== 6. 端到端: 真实 nextalk 空壳应被清理并冷启动 =="
# 核心修复路径。需要一个进程同时满足三个条件才能精确复现故障现场:
#   exe 名含 nextalk + 有 io.flutter.* 线程但无 io.flutter.ui + listen 不 accept
# 用最小 C 程序模拟(python 无法伪造 /proc/pid/exe)。没有编译器时跳过。
if ! command -v cc >/dev/null 2>&1; then
  echo "  ⏭️  跳过: 无 C 编译器"
else
  rm -f "$WORK/nextalk.sock"
  cat > "$WORK/shell.c" <<'EOF'
// 模拟 Dart engine 已死的 nextalk 空壳: 持有 listen socket 但永不 accept,
// 线程里有 io.flutter.rast / io.flutter.io 却没有 io.flutter.ui。
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

static void* worker(void* arg) {
  prctl(PR_SET_NAME, (char*)arg, 0, 0, 0);
  sleep(60);
  return NULL;
}

int main(int argc, char** argv) {
  pthread_t t1, t2;
  pthread_create(&t1, NULL, worker, (void*)"io.flutter.rast");
  pthread_create(&t2, NULL, worker, (void*)"io.flutter.io");

  int fd = socket(AF_UNIX, SOCK_STREAM, 0);
  struct sockaddr_un a;
  memset(&a, 0, sizeof(a));
  a.sun_family = AF_UNIX;
  strncpy(a.sun_path, argv[1], sizeof(a.sun_path) - 1);
  if (bind(fd, (struct sockaddr*)&a, sizeof(a)) != 0) return 1;
  if (listen(fd, 128) != 0) return 1;   // 绝不 accept
  printf("READY\n");
  fflush(stdout);
  sleep(60);
  return 0;
}
EOF
  if cc -o "$WORK/bin/nextalk-shell" "$WORK/shell.c" -lpthread 2>"$WORK/cc.log"; then
    "$WORK/bin/nextalk-shell" "$WORK/nextalk.sock" > "$WORK/shell.out" 2>&1 &
    SHELL_PID=$!
    for _ in $(seq 1 30); do
      grep -q READY "$WORK/shell.out" 2>/dev/null && break
      sleep 0.1
    done

    OUT=$(timeout 20 "$TOGGLE" toggle 2>&1)
    RC=$?

    if echo "$OUT" | grep -q "空壳进程"; then
      ok "识别出 Dart engine 已死的空壳"
    else
      ng "未识别空壳 (输出: $OUT)"
    fi
    if ! kill -0 $SHELL_PID 2>/dev/null; then
      ok "空壳进程已被清理"
    else
      ng "空壳进程仍存活"
      kill -9 $SHELL_PID 2>/dev/null
    fi
    if echo "$OUT" | grep -q "COLD_START_INVOKED:--toggle"; then
      ok "清理后冷启动并透传 --toggle"
    else
      ng "清理后未冷启动 (输出: $OUT)"
    fi
    if [ "$RC" -eq 0 ]; then
      ok "整体退出码 0"
    else
      ng "整体退出码 $RC"
    fi
    wait $SHELL_PID 2>/dev/null
  else
    echo "  ⏭️  跳过: 编译失败 ($(head -1 "$WORK/cc.log"))"
  fi
fi

echo
echo "结果: $PASS 通过, $FAIL 失败"
[ "$FAIL" -eq 0 ]
