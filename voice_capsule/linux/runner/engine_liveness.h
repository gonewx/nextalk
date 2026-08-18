// NEXTALK: Dart engine 存活探测
//
// 单独成文件的原因: 这段判定的输出直接决定"要不要 _exit 掉自己", 必须能脱离
// GTK 单元测试 (见 linux/runner/test/test_engine_liveness.c)。因此这里只用
// 标准 C, 不碰 glib / GTK。
#ifndef RUNNER_ENGINE_LIVENESS_H_
#define RUNNER_ENGINE_LIVENESS_H_

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Flutter 在 Linux 上跑 Dart isolate 的线程名。comm 上限 15 字符, 该名 13 字符,
// 不会像 io.flutter.raster(被截成 io.flutter.rast) 那样被截断。
#define NEXTALK_FLUTTER_UI_THREAD "io.flutter.ui"
#define NEXTALK_FLUTTER_THREAD_PREFIX "io.flutter."

typedef enum {
  // io.flutter.ui 在: Dart isolate 活着
  NEXTALK_ENGINE_ALIVE,
  // 一个 io.flutter.* 都没有: engine 尚未启动, 或 Flutter 改了线程命名体系。
  // 两种情况都不能判死。
  NEXTALK_ENGINE_NOT_STARTED,
  // engine 的其它线程都在、独独 io.flutter.ui 没了 —— isolate 已死的空壳签名
  NEXTALK_ENGINE_DEAD_SHELL,
} NextalkEngineState;

// 探测指定 task 目录反映的 engine 状态。
//
// task_dir 通常是 "/proc/self/task"; 参数化只为让测试能喂进构造好的假目录。
// 读不到该目录时返回 NOT_STARTED —— 无从判断就绝不判死。
NextalkEngineState nextalk_probe_engine_state(const char* task_dir);

// 看门狗状态机。与 I/O 分开, 才能穷举各种状态序列。
typedef struct {
  int consecutive_dead;     // 连续多少轮观测到空壳
  int rounds_before_dead;   // 判定死亡所需的连续轮数
} NextalkEngineWatchdog;

void nextalk_watchdog_init(NextalkEngineWatchdog* w, int rounds_before_dead);

// 喂入本轮观测结果, 返回 true 表示应判定 engine 已死并退出进程。
//
// 刻意做成**无状态判定 + 连续确认**, 不记录"曾经见过 UI 线程":
// engine 可能在极早期(本次故障是 ASR 初始化期间, 约 3 秒内)就猝死, 若要求
// "先见过才启用", 首轮检查稍晚一点就永远等不到, 看门狗直接失效 —— 这个竞态
// 实测踩到过。改用 NOT_STARTED 区分"没启动"与"启动过又死了", 就没有竞态;
// 连续确认则用来避开启动时 raster 线程已建、ui 线程还没建的瞬时窗口。
bool nextalk_watchdog_observe(NextalkEngineWatchdog* w,
                              NextalkEngineState state);

// 把 engine 死亡现场追加写入 path。
//
// 为什么非要在 C 侧写: engine 猝死时 Dart 已经跑不了代码, diagnostic.log 只会
// 停在最后一条业务日志上, 事后只能靠推断。更要紧的是 —— UI 线程是**干净退出**
// 的(进程还活着, 没吃到任何信号), 所以永远不会产生 coredump, 这是唯一能留下的
// 一手证据。记录线程名可看出 engine 还剩哪些线程, 记录内存可排除 OOM。
//
// 失败静默忽略: 留证失败绝不能妨碍"退出进程释放 socket"这件正事。
void nextalk_write_death_report(const char* path, const char* task_dir);

#ifdef __cplusplus
}
#endif

#endif  // RUNNER_ENGINE_LIVENESS_H_
