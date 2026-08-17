#include "my_application.h"

#include <stdlib.h>

int main(int argc, char** argv) {
  // ============================================
  // NEXTALK: 用 GDK 原生回退链优先 x11 (XWayland)
  // ============================================
  // 必须早于 GTK/GDK 初始化，因此只能放在 g_application_run 之前。
  //
  // 为什么优先 x11: Wayland 原生后端下 gtk_window_move() 完全 no-op、
  // gtk_window_get_position() 恒返回 (0,0)。胶囊的默认定位与位置记忆
  // 全部失效，还会把脏值 (0,0) 写进 prefs。项目 .desktop 早已选定
  // x11 路线，这里让所有启动入口（.desktop / nextalk-toggle 冷启动回退 /
  // 直接执行二进制）后端一致。
  //
  // 为什么用回退链而不是自己探测 DISPLAY: "x11,wayland" 让 GDK 依次尝试、
  // 由 GDK 自己判定可用性。实测对照 ——
  //   X 可用             → backend=x11     （两种做法都对）
  //   无 DISPLAY         → backend=wayland （两种做法都对）
  //   DISPLAY=:99 不可达 → backend=wayland；而"仅 x11 + 探测 getenv(DISPLAY)
  //                        非空"在此处 gtk_init_check FAILED，应用直接起不来
  // 纯 Wayland 会话里残留的 DISPLAY=:0、失效的 SSH X 转发都会命中那个盲区。
  // 可启动性优先于位置正确性：拿不到 X 时回落 wayland，位置功能降级但应用照常启动。
  //
  // overwrite=0: 用户显式设置的 GDK_BACKEND 不被覆盖，保留逃逸阀。
  setenv("GDK_BACKEND", "x11,wayland", 0);

  g_autoptr(MyApplication) app = my_application_new();
  return g_application_run(G_APPLICATION(app), argc, argv);
}
