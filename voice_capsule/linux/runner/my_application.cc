#include "my_application.h"

#include <flutter_linux/flutter_linux.h>
#ifdef GDK_WINDOWING_X11
#include <gdk/gdkx.h>
#endif
#ifdef GDK_WINDOWING_WAYLAND
#include <gdk/gdkwayland.h>
#endif

#include "flutter/generated_plugin_registrant.h"

struct _MyApplication {
  GtkApplication parent_instance;
  char** dart_entrypoint_arguments;
};

G_DEFINE_TYPE(MyApplication, my_application, GTK_TYPE_APPLICATION)

// Implements GApplication::activate.
static void my_application_activate(GApplication* application) {
  MyApplication* self = MY_APPLICATION(application);
  GtkWindow* window =
      GTK_WINDOW(gtk_application_window_new(GTK_APPLICATION(application)));

  // ============================================
  // NEXTALK: Transparent Capsule Window Configuration
  // Story 3-1: 透明胶囊窗口基础
  // ⚠️ CRITICAL: All transparency config MUST happen BEFORE fl_view_new()
  // ============================================

  // 1. 禁用窗口装饰 (无边框、无标题栏) - AC1
  gtk_window_set_decorated(window, FALSE);

  // 2. 设置窗口类型提示 (确保跳过任务栏，在所有桌面环境生效) - AC7
  gtk_window_set_type_hint(window, GDK_WINDOW_TYPE_HINT_UTILITY);

  // 3. 禁止接受焦点 - 防止抢占其他应用的输入焦点
  gtk_window_set_accept_focus(window, FALSE);
  gtk_window_set_focus_on_map(window, FALSE);

  // 3. 设置窗口可绘制透明 - AC2
  gtk_widget_set_app_paintable(GTK_WIDGET(window), TRUE);

  // 4. 设置 RGBA Visual (支持透明) - 必须在 fl_view_new() 前! - AC2, AC5
  GdkScreen* screen = gtk_window_get_screen(window);
  GdkVisual* visual = gdk_screen_get_rgba_visual(screen);
  if (visual != NULL && gdk_screen_is_composited(screen)) {
    gtk_widget_set_visual(GTK_WIDGET(window), visual);
    g_message("NEXTALK: Transparent window enabled (RGBA visual active)");
  } else {
    g_warning("NEXTALK: Transparent window not supported by compositor - fallback to opaque");
  }

  // 5. 设置固定尺寸 400x120 (逻辑像素) - AC3
  gtk_window_set_default_size(window, 400, 120);
  gtk_window_set_resizable(window, FALSE);

  // 6. 检测运行环境并记录日志 (用于调试) - AC8
#ifdef GDK_WINDOWING_X11
  if (GDK_IS_X11_SCREEN(screen)) {
    g_message("NEXTALK: Running on X11");
  }
#endif
#ifdef GDK_WINDOWING_WAYLAND
  GdkDisplay* display = gdk_display_get_default();
  if (GDK_IS_WAYLAND_DISPLAY(display)) {
    g_message("NEXTALK: Running on Wayland - if transparency fails, try GDK_BACKEND=x11");
  }
#endif

  // ============================================
  // END: Transparency configuration
  // ============================================

  // 创建 Flutter 项目和视图
  g_autoptr(FlDartProject) project = fl_dart_project_new();
  fl_dart_project_set_dart_entrypoint_arguments(project, self->dart_entrypoint_arguments);

  FlView* view = fl_view_new(project);
  gtk_container_add(GTK_CONTAINER(window), GTK_WIDGET(view));

  // ⚠️ 关键修复: 设置 FlView 背景透明 (Flutter 官方修复方案)
  // FlView 默认背景是黑色，必须显式设置为透明
  GdkRGBA background_color = {0.0, 0.0, 0.0, 0.0};
  fl_view_set_background_color(view, &background_color);

  fl_register_plugins(FL_PLUGIN_REGISTRY(view));

  // 显示窗口 (不抢占焦点)
  gtk_widget_show_all(GTK_WIDGET(window));
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
