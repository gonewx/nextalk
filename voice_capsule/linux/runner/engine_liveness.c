#include "engine_liveness.h"

#include <dirent.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

NextalkEngineState nextalk_probe_engine_state(const char* task_dir) {
  DIR* dir = opendir(task_dir);
  if (dir == NULL) {
    // 读不到 /proc: 无从判断, 绝不判死
    return NEXTALK_ENGINE_NOT_STARTED;
  }

  bool has_ui = false;
  bool has_any_flutter = false;
  struct dirent* entry;
  while ((entry = readdir(dir)) != NULL) {
    if (entry->d_name[0] == '.') continue;   // 跳过 . 与 ..

    char path[512];
    int written =
        snprintf(path, sizeof(path), "%s/%s/comm", task_dir, entry->d_name);
    if (written < 0 || (size_t)written >= sizeof(path)) continue;  // 路径过长

    FILE* f = fopen(path, "r");
    if (f == NULL) continue;   // 线程刚退出, 跳过

    char name[64];
    if (fgets(name, sizeof(name), f) != NULL) {
      char* newline = strchr(name, '\n');
      if (newline != NULL) *newline = '\0';

      if (strcmp(name, NEXTALK_FLUTTER_UI_THREAD) == 0) {
        has_ui = true;
      }
      if (strncmp(name, NEXTALK_FLUTTER_THREAD_PREFIX,
                  strlen(NEXTALK_FLUTTER_THREAD_PREFIX)) == 0) {
        has_any_flutter = true;
      }
    }
    fclose(f);
    if (has_ui) break;   // 已确定活着, 无需继续扫
  }
  closedir(dir);

  if (has_ui) return NEXTALK_ENGINE_ALIVE;
  if (!has_any_flutter) return NEXTALK_ENGINE_NOT_STARTED;
  return NEXTALK_ENGINE_DEAD_SHELL;
}

void nextalk_watchdog_init(NextalkEngineWatchdog* w, int rounds_before_dead) {
  w->consecutive_dead = 0;
  w->rounds_before_dead = rounds_before_dead;
}

bool nextalk_watchdog_observe(NextalkEngineWatchdog* w,
                             NextalkEngineState state) {
  if (state != NEXTALK_ENGINE_DEAD_SHELL) {
    w->consecutive_dead = 0;
    return false;
  }

  // 连续确认: 避开启动时 raster 线程已建、ui 线程还没建的瞬时窗口
  w->consecutive_dead++;
  return w->consecutive_dead >= w->rounds_before_dead;
}

// 把 /proc/<pid>/<name> 的首行原样抄进 out
static void append_proc_line(FILE* out, const char* label, const char* path,
                             const char* prefix) {
  FILE* f = fopen(path, "r");
  if (f == NULL) return;
  char line[256];
  while (fgets(line, sizeof(line), f) != NULL) {
    if (prefix == NULL || strncmp(line, prefix, strlen(prefix)) == 0) {
      fprintf(out, "%s%s", label, line);
      if (prefix != NULL) break;   // 只要匹配到的那一行
    }
  }
  fclose(f);
}

void nextalk_write_death_report(const char* path, const char* task_dir) {
  FILE* out = fopen(path, "a");
  if (out == NULL) return;   // 留证失败不能妨碍退出进程

  fprintf(out, "\n===== Dart engine 猝死现场 =====\n");
  fprintf(out, "pid: %ld\n", (long)getpid());
  fprintf(out, "unix_time: %lld\n", (long long)time(NULL));

  // 还剩哪些线程 —— 能看出 engine 死到什么程度(raster/io 是否也没了)
  fprintf(out, "remaining_threads:\n");
  DIR* dir = opendir(task_dir);
  if (dir != NULL) {
    struct dirent* entry;
    while ((entry = readdir(dir)) != NULL) {
      if (entry->d_name[0] == '.') continue;
      char comm_path[512];
      int written = snprintf(comm_path, sizeof(comm_path), "%s/%s/comm",
                             task_dir, entry->d_name);
      if (written < 0 || (size_t)written >= sizeof(comm_path)) continue;
      FILE* f = fopen(comm_path, "r");
      if (f == NULL) continue;
      char name[64];
      if (fgets(name, sizeof(name), f) != NULL) {
        fprintf(out, "  %s: %s", entry->d_name, name);
      }
      fclose(f);
    }
    closedir(dir);
  }

  // 内存水位: 用来排除 OOM / 地址空间耗尽这类猜测
  append_proc_line(out, "  ", "/proc/self/status", "VmRSS");
  append_proc_line(out, "  ", "/proc/self/status", "VmSize");
  append_proc_line(out, "  ", "/proc/self/status", "Threads");
  // 系统整体可用内存
  append_proc_line(out, "  ", "/proc/meminfo", "MemAvailable");

  fprintf(out, "===== 现场结束 =====\n");
  fclose(out);
}

