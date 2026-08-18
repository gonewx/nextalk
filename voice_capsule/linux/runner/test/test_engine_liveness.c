// engine_liveness 的单元测试。
//
// 为什么值得单测: 这段判定的输出直接决定"要不要 _exit 掉自己"。判错一个方向,
// 空壳继续占着 socket 让快捷键永久失效; 判错另一个方向, 健康实例被反复自杀。
// 编译运行: cc -o /tmp/t test_engine_liveness.c ../engine_liveness.c -lpthread
// 可选: 传一个真实进程 PID 作为参数, 顺带校验对该进程的判定结果。
//
// 必须早于所有 include: mkdtemp / usleep 属 POSIX 扩展, 在 -std=c11 下若不开
// feature macro 就只有隐式声明, 返回值会被当成 int 截断掉指针高位 -> 段错误。
#define _XOPEN_SOURCE 700
#define _DEFAULT_SOURCE

#include "../engine_liveness.h"

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <unistd.h>

static int failures = 0;

static void check(const char* name, bool cond) {
  printf("  %s %s\n", cond ? "✅" : "❌", name);
  if (!cond) failures++;
}

static const char* state_name(NextalkEngineState s) {
  switch (s) {
    case NEXTALK_ENGINE_ALIVE: return "ALIVE";
    case NEXTALK_ENGINE_NOT_STARTED: return "NOT_STARTED";
    case NEXTALK_ENGINE_DEAD_SHELL: return "DEAD_SHELL";
  }
  return "?";
}

// ---------- 构造假的 task 目录 ----------
static void write_comm(const char* task_dir, const char* tid,
                       const char* name) {
  char dir[512];
  snprintf(dir, sizeof(dir), "%s/%s", task_dir, tid);
  mkdir(dir, 0755);

  char path[600];
  snprintf(path, sizeof(path), "%s/comm", dir);
  FILE* f = fopen(path, "w");
  if (f == NULL) return;
  fprintf(f, "%s\n", name);   // /proc 的 comm 带尾换行, 必须一并模拟
  fclose(f);
}

static char* make_case(const char* base, const char* name) {
  static char dir[512];
  snprintf(dir, sizeof(dir), "%s/%s", base, name);
  mkdir(dir, 0755);
  return dir;
}

static void test_probe(void) {
  printf("== 状态探测 ==\n");

  char tmpl[] = "/tmp/nextalk_liveness_XXXXXX";
  char* base = mkdtemp(tmpl);
  if (base == NULL) {
    printf("  ❌ 无法创建临时目录\n");
    failures++;
    return;
  }

  // 本次故障的真实现场 (PID 13473 / 128649): engine 其它线程都在, 独独没有 ui
  char* dead = make_case(base, "dead");
  write_comm(dead, "1", "nextalk");
  write_comm(dead, "2", "gmain");
  write_comm(dead, "3", "io.flutter.rast");   // comm 15 字符截断后的真实样子
  write_comm(dead, "4", "io.flutter.io");
  write_comm(dead, "5", "DartWorker");
  check("空壳现场 -> DEAD_SHELL",
        nextalk_probe_engine_state(dead) == NEXTALK_ENGINE_DEAD_SHELL);

  // 健康实例: 有多个 io.flutter.ui
  char* alive = make_case(base, "alive");
  write_comm(alive, "1", "nextalk");
  write_comm(alive, "2", "io.flutter.rast");
  write_comm(alive, "3", "io.flutter.ui");
  write_comm(alive, "4", "io.flutter.ui");
  check("健康实例 -> ALIVE",
        nextalk_probe_engine_state(alive) == NEXTALK_ENGINE_ALIVE);

  // engine 还没起来: 只有 GTK 自己的线程
  char* early = make_case(base, "early");
  write_comm(early, "1", "nextalk");
  write_comm(early, "2", "gmain");
  write_comm(early, "3", "gdbus");
  check("engine 未启动 -> NOT_STARTED",
        nextalk_probe_engine_state(early) == NEXTALK_ENGINE_NOT_STARTED);

  // 关键安全用例: 若 Flutter 改了线程命名体系, 必须退化成 NOT_STARTED,
  // 绝不能因为"找不到 io.flutter.ui"就把健康实例判死。
  char* renamed = make_case(base, "renamed");
  write_comm(renamed, "1", "nextalk");
  write_comm(renamed, "2", "dart.ui.worker");
  write_comm(renamed, "3", "dart.raster");
  check("线程命名体系变更 -> NOT_STARTED(不判死)",
        nextalk_probe_engine_state(renamed) == NEXTALK_ENGINE_NOT_STARTED);

  // 前缀相近的名字不能被当成 ui 线程
  char* similar = make_case(base, "similar");
  write_comm(similar, "1", "io.flutter.uix");
  write_comm(similar, "2", "io.flutter.u");
  check("相近线程名不误判为 ALIVE",
        nextalk_probe_engine_state(similar) == NEXTALK_ENGINE_DEAD_SHELL);

  // 读不到目录 -> 绝不判死
  check("目录不存在 -> NOT_STARTED",
        nextalk_probe_engine_state("/nonexistent/nextalk/task") ==
            NEXTALK_ENGINE_NOT_STARTED);

  char cmd[600];
  snprintf(cmd, sizeof(cmd), "rm -rf '%s'", base);
  if (system(cmd) != 0) printf("  (清理临时目录失败, 可忽略)\n");
}

// ---------- 真实进程自检 ----------
static void* ui_thread_body(void* arg) {
  prctl(PR_SET_NAME, NEXTALK_FLUTTER_UI_THREAD, 0, 0, 0);
  sleep(3);
  (void)arg;
  return NULL;
}

static void test_against_real_process(void) {
  printf("== 真实进程自检 (/proc/self/task) ==\n");

  // 本测试进程没有任何 io.flutter.* 线程
  check("测试进程 -> NOT_STARTED",
        nextalk_probe_engine_state("/proc/self/task") ==
            NEXTALK_ENGINE_NOT_STARTED);

  // 造一个真的叫 io.flutter.ui 的线程, 验证能从真实 /proc 读出来
  pthread_t t;
  pthread_create(&t, NULL, ui_thread_body, NULL);
  usleep(300000);   // 等 prctl 生效
  check("创建同名线程后 -> ALIVE",
        nextalk_probe_engine_state("/proc/self/task") == NEXTALK_ENGINE_ALIVE);
  pthread_join(t, NULL);
  usleep(100000);
  check("线程退出后 -> NOT_STARTED",
        nextalk_probe_engine_state("/proc/self/task") ==
            NEXTALK_ENGINE_NOT_STARTED);
}

// ---------- 看门狗状态机 ----------
static void test_watchdog(void) {
  printf("== 看门狗状态机 ==\n");
  NextalkEngineWatchdog w;

  // 启动早期(NOT_STARTED)无论多少轮都不能判死
  nextalk_watchdog_init(&w, 3);
  bool ever_dead = false;
  for (int i = 0; i < 20; i++) {
    ever_dead |= nextalk_watchdog_observe(&w, NEXTALK_ENGINE_NOT_STARTED);
  }
  check("NOT_STARTED 连续 20 轮不判死", ever_dead == false);

  // 正常运行
  nextalk_watchdog_init(&w, 3);
  check("ALIVE 不判死",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_ALIVE) == false);

  // 空壳需连续确认, 避开 raster 已建/ui 未建的瞬时窗口
  check("DEAD_SHELL 第1轮不判死",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == false);
  check("DEAD_SHELL 第2轮不判死",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == false);
  check("DEAD_SHELL 第3轮判定死亡",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == true);

  // 关键: 无状态设计下, engine 死得比首轮检查还早也能判出来
  // (这是旧的"必须先见过 UI 线程"设计踩到的竞态)
  nextalk_watchdog_init(&w, 3);
  check("从未观测到 ALIVE 也能判死(第1轮)",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == false);
  nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL);
  check("从未观测到 ALIVE 也能判死(第3轮)",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == true);

  // 中途恢复必须清零, 否则长期运行会被零星抖动累积成误杀
  nextalk_watchdog_init(&w, 3);
  nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL);
  nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL);
  check("恢复 ALIVE 后计数清零",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_ALIVE) == false);
  check("清零后第1轮不判死",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == false);
  check("清零后第2轮不判死",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == false);
  check("清零后第3轮才判死",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == true);

  // NOT_STARTED 同样要清零 (engine 重启途中会短暂如此)
  nextalk_watchdog_init(&w, 2);
  nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL);
  check("NOT_STARTED 也清零计数",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_NOT_STARTED) == false);
  check("清零后需重新累计",
        nextalk_watchdog_observe(&w, NEXTALK_ENGINE_DEAD_SHELL) == false);
}

// ---------- 死亡现场留证 ----------
static void test_death_report(void) {
  printf("== 死亡现场留证 ==\n");

  char tmpl[] = "/tmp/nextalk_report_XXXXXX";
  char* base = mkdtemp(tmpl);
  if (base == NULL) {
    printf("  ❌ 无法创建临时目录\n");
    failures++;
    return;
  }

  // 用假 task 目录模拟空壳现场
  char* task = make_case(base, "task");
  write_comm(task, "1", "nextalk");
  write_comm(task, "2", "io.flutter.rast");
  write_comm(task, "3", "io.flutter.io");

  char report[600];
  snprintf(report, sizeof(report), "%s/engine-death.log", base);
  nextalk_write_death_report(report, task);

  FILE* f = fopen(report, "r");
  check("现场文件已生成", f != NULL);
  if (f != NULL) {
    char content[4096] = {0};
    size_t n = fread(content, 1, sizeof(content) - 1, f);
    content[n] = '\0';
    fclose(f);

    check("含 pid", strstr(content, "pid:") != NULL);
    check("含时间戳", strstr(content, "unix_time:") != NULL);
    // 残留线程是判断"engine 死到什么程度"的关键
    check("含残留线程 io.flutter.rast",
          strstr(content, "io.flutter.rast") != NULL);
    check("不含 io.flutter.ui(空壳现场)",
          strstr(content, "io.flutter.ui") == NULL);
    // 内存水位用于排除 OOM 猜测
    check("含 VmRSS", strstr(content, "VmRSS") != NULL);
    check("含 MemAvailable", strstr(content, "MemAvailable") != NULL);

    // 追加写: 多次猝死的现场都要留下, 不能互相覆盖
    nextalk_write_death_report(report, task);
    f = fopen(report, "r");
    if (f != NULL) {
      char again[8192] = {0};
      size_t m = fread(again, 1, sizeof(again) - 1, f);
      again[m] = '\0';
      fclose(f);
      const char* first = strstr(again, "猝死现场");
      const char* second =
          first != NULL ? strstr(first + 1, "猝死现场") : NULL;
      check("追加写而非覆盖", second != NULL);
    }
  }

  // 不可写路径不能崩, 也不能妨碍退出流程
  nextalk_write_death_report("/nonexistent/dir/report.log", task);
  check("路径不可写时静默返回(未崩溃)", true);

  char cmd[700];
  snprintf(cmd, sizeof(cmd), "rm -rf '%s'", base);
  if (system(cmd) != 0) printf("  (清理临时目录失败, 可忽略)\n");
}

// ---------- 对真实 PID 的旁证 ----------
static void test_given_pid(const char* pid) {
  printf("== 对真实 PID %s 的判定 ==\n", pid);
  char dir[256];
  snprintf(dir, sizeof(dir), "/proc/%s/task", pid);
  NextalkEngineState s = nextalk_probe_engine_state(dir);
  printf("  判定结果: %s\n", state_name(s));
}

int main(int argc, char** argv) {
  test_probe();
  test_against_real_process();
  test_watchdog();
  test_death_report();
  if (argc > 1) test_given_pid(argv[1]);

  printf("\n%s\n", failures == 0 ? "全部通过" : "有失败项");
  return failures == 0 ? 0 : 1;
}
