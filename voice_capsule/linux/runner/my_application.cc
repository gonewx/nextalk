#include "my_application.h"

#include <flutter_linux/flutter_linux.h>
#ifdef GDK_WINDOWING_X11
#include <gdk/gdkx.h>
#endif
#ifdef GDK_WINDOWING_WAYLAND
#include <gdk/gdkwayland.h>
#endif

#include <unistd.h>

#include "engine_liveness.h"
#include "flutter/generated_plugin_registrant.h"

struct _MyApplication {
  GtkApplication parent_instance;
  char** dart_entrypoint_arguments;
};

G_DEFINE_TYPE(MyApplication, my_application, GTK_TYPE_APPLICATION)

// ============================================
// NEXTALK: Dart engine 死亡看门狗
// ============================================
// 要解决的故障 (2026-08-18 实测): Dart engine 死掉后 GTK 主循环仍在 do_poll,
// 进程变成空壳却继续持有 $XDG_RUNTIME_DIR/nextalk.sock 的 LISTEN。内核照常
// 接受连接并塞进 backlog, 于是 nextalk-toggle 的 write 全部"成功", 快捷键
// 彻底失效且永不自愈 —— 当时 18 次按键全堆在 accept 队列里 (Recv-Q=18)。
// socket 的生命周期必须跟 Dart isolate 一致: isolate 没了, 进程就得退出,
// 让 fd 随进程释放, 下一次按键才能冷启动出一个健康实例。
//
// 为什么靠扫线程名而不是 embedder 回调: Flutter Linux 的公开头文件
// (fl_engine.h / fl_view.h) 压根没有 engine shutdown 通知 —— 没有信号也没有
// 回调; embedder C API 里的 shutdown_dart_vm_when_done 在 FlDartProject 这层
// 拿不到。Dart 侧心跳同样不行: 本次崩溃就发生在 ASR 引擎初始化期间, 那时
// 心跳还没建立, 恰好落在盲区里。而 io.flutter.* 线程从 engine 启动即存在,
// 覆盖包括初始化早期在内的整个生命周期。
//
// 判定逻辑与状态机在 engine_liveness.c, 便于脱离 GTK 单元测试。
// 无状态判定不依赖"曾经见过 UI 线程", 所以首轮什么时候查都不影响正确性;
// 连续 3 轮(≈3 秒)确认只为避开启动时 raster 已建、ui 未建的瞬时窗口。
static const guint kWatchdogIntervalMs = 1000;
static const int kRoundsBeforeDead = 3;

static gboolean watch_engine_liveness(gpointer user_data) {
  NextalkEngineWatchdog* watchdog =
      static_cast<NextalkEngineWatchdog*>(user_data);

  if (!nextalk_watchdog_observe(
          watchdog, nextalk_probe_engine_state("/proc/self/task"))) {
    return G_SOURCE_CONTINUE;
  }

  // 留证: engine 猝死时 Dart 已跑不了代码, diagnostic.log 只会停在最后一条
  // 业务日志; 而 UI 线程是干净退出(进程没吃到任何信号), 也不会有 coredump。
  // 这份现场是事后定位根因唯一的一手证据。
  g_autofree gchar* report_path =
      g_build_filename(g_get_user_data_dir(), "nextalk", "logs",
                       "engine-death.log", nullptr);
  nextalk_write_death_report(report_path, "/proc/self/task");

  g_warning(
      "[nextalk] Dart engine 已死 (io.flutter.ui 线程消失), 现场已写入 %s, "
      "主动退出进程以释放单实例 socket —— 否则空壳会占着 socket 让快捷键永久失效",
      report_path);
  // 用 _exit 而不是 g_application_quit: 此刻 Dart 侧已无法参与清理, 走正常
  // 退出流程可能卡在等 engine 响应上, 反而留下我们要消灭的空壳。
  // socket 文件残留无害: 下次启动 tryBecomeMainInstance 连不上就会删掉重建。
  _exit(70);  // EX_SOFTWARE: 区别于用户主动退出的 0
  return G_SOURCE_REMOVE;
}

// Implements GApplication::activate.
static void my_application_activate(GApplication* application) {
  MyApplication* self = MY_APPLICATION(application);
  GtkWindow* window =
      GTK_WINDOW(gtk_application_window_new(GTK_APPLICATION(application)));

  // ============================================
  // NEXTALK: Transparent Capsule Window Configuration
  // ⚠️ CRITICAL: All transparency config MUST happen BEFORE fl_view_new()
  // ============================================

  // 设置无边框窗口
  gtk_window_set_decorated(window, FALSE);

  // 设置窗口类型为 UTILITY (在所有平台上统一使用)
  gtk_window_set_type_hint(window, GDK_WINDOW_TYPE_HINT_UTILITY);

  // ⚠️ 关键：不在任务栏/Dock 显示图标
  gtk_window_set_skip_taskbar_hint(window, TRUE);
  gtk_window_set_skip_pager_hint(window, TRUE);

  // ⚠️ 关键：禁止接受焦点 - 防止抢占其他应用的输入焦点
  gtk_window_set_accept_focus(window, FALSE);
  gtk_window_set_focus_on_map(window, FALSE);

  // 透明化设置
  GdkScreen* screen = gtk_window_get_screen(window);
  GdkVisual* visual = gdk_screen_get_rgba_visual(screen);
  if (visual != nullptr && gdk_screen_is_composited(screen)) {
    gtk_widget_set_visual(GTK_WIDGET(window), visual);
  }
  gtk_widget_set_app_paintable(GTK_WIDGET(window), TRUE);

  // 设置窗口大小
  gtk_window_set_default_size(window, 400, 120);

  // ============================================
  // END: Transparency configuration
  // ============================================

  // 创建 Flutter 项目和视图
  g_autoptr(FlDartProject) project = fl_dart_project_new();
  fl_dart_project_set_dart_entrypoint_arguments(project, self->dart_entrypoint_arguments);

  FlView* view = fl_view_new(project);
  gtk_container_add(GTK_CONTAINER(window), GTK_WIDGET(view));

  // ⚠️ 关键修复: 设置 FlView 背景透明 (Flutter 官方修复方案)
  GdkRGBA background_color = {0.0, 0.0, 0.0, 0.0};
  fl_view_set_background_color(view, &background_color);

  fl_register_plugins(FL_PLUGIN_REGISTRY(view));

  // 显示然后隐藏，让 window_manager 插件控制显示
  gtk_widget_show_all(GTK_WIDGET(window));
  gtk_widget_hide(GTK_WIDGET(window));

  // NEXTALK: 启动 engine 死亡看门狗 (详见文件顶部说明)。
  // 状态随进程存活, 故意不释放。
  NextalkEngineWatchdog* watchdog = g_new0(NextalkEngineWatchdog, 1);
  nextalk_watchdog_init(watchdog, kRoundsBeforeDead);
  g_timeout_add(kWatchdogIntervalMs, watch_engine_liveness, watchdog);
}

// Implements GApplication::local_command_line.
static gboolean my_application_local_command_line(GApplication* application, gchar*** arguments, int* exit_status) {
  MyApplication* self = MY_APPLICATION(application);
  // Strip out the first argument as it is the binary name.
  self->dart_entrypoint_arguments = g_strdupv(*arguments + 1);

  g_autoptr(GError) error = nullptr;
  if (!g_application_register(application, nullptr, &error)) {
     g_warning("Failed to register: %s", error->message);
     *exit_status = 1;
     return TRUE;
  }

  g_application_activate(application);
  *exit_status = 0;

  return TRUE;
}

// Implements GApplication::startup.
static void my_application_startup(GApplication* application) {
  //MyApplication* self = MY_APPLICATION(object);

  // Perform any actions required at application startup.

  G_APPLICATION_CLASS(my_application_parent_class)->startup(application);
}

// Implements GApplication::shutdown.
static void my_application_shutdown(GApplication* application) {
  //MyApplication* self = MY_APPLICATION(object);

  // Perform any actions required at application shutdown.

  G_APPLICATION_CLASS(my_application_parent_class)->shutdown(application);
}

// Implements GObject::dispose.
static void my_application_dispose(GObject* object) {
  MyApplication* self = MY_APPLICATION(object);
  g_clear_pointer(&self->dart_entrypoint_arguments, g_strfreev);
  G_OBJECT_CLASS(my_application_parent_class)->dispose(object);
}

static void my_application_class_init(MyApplicationClass* klass) {
  G_APPLICATION_CLASS(klass)->activate = my_application_activate;
  G_APPLICATION_CLASS(klass)->local_command_line = my_application_local_command_line;
  G_APPLICATION_CLASS(klass)->startup = my_application_startup;
  G_APPLICATION_CLASS(klass)->shutdown = my_application_shutdown;
  G_OBJECT_CLASS(klass)->dispose = my_application_dispose;
}

static void my_application_init(MyApplication* self) {}

MyApplication* my_application_new() {
  // Set the program name to the application ID, which helps various systems
  // like GTK and desktop environments map this running application to its
  // corresponding .desktop file. This ensures better integration by allowing
  // the application to be recognized beyond its binary name.
  g_set_prgname(APPLICATION_ID);

  return MY_APPLICATION(g_object_new(my_application_get_type(),
                                     "application-id", APPLICATION_ID,
                                     "flags", G_APPLICATION_NON_UNIQUE,
                                     nullptr));
}
