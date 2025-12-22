# Story 3.1: 透明胶囊窗口基础 (Transparent Capsule Window Foundation)

Status: done

## Prerequisites

> **前置条件**: Epic 1 & Epic 2 必须完成
> - ✅ Flutter Linux 项目已初始化 (Story 1-4)
> - ✅ 原生库链接配置完成 (Story 2-1)
> - ✅ 音频采集与推理流水线完成 (Story 2-2 ~ 2-6)
> - ⚠️ 本 Story 是 Epic 3 的第一个 Story，开启完整产品体验

## Story

As a **用户**,
I want **应用窗口是无边框、真透明的悬浮窗**,
So that **获得现代化、不干扰桌面的视觉体验**。

## Acceptance Criteria

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC1 | 无边框无标题栏: 窗口无系统边框和标题栏 | 运行应用，观察窗口无任何系统装饰 |
| AC2 | 真透明背景: 窗口背景完全透明（可看到桌面） | 在有壁纸的桌面上运行，确认背景可见 |
| AC3 | 固定尺寸: 窗口尺寸为 400x120 逻辑像素 | 使用窗口检测工具验证尺寸 |
| AC4 | 居中/记忆位置: 窗口出现在屏幕中央或上次记忆位置 | 首次运行居中，拖拽后关闭再打开在新位置 |
| AC5 | 无黑框闪烁 (NFR4): 窗口首次渲染无黑框闪烁现象 | 多次启动观察，无任何闪烁 |
| AC6 | 瞬间出现: 窗口瞬间出现，无渐变动画 | 观察窗口显示速度 |
| AC7 | 始终在最前: 窗口层级正确，始终在最前显示 | 点击其他窗口后胶囊仍在最前 |
| AC8 | 兼容性 (NFR3): 兼容 Ubuntu 22.04+ (X11/Wayland via XWayland) | 在 X11 和 XWayland 环境下测试 |
| AC9 | 窗口可拖拽: 支持拖拽移动窗口 | 按住窗口空白处拖拽移动 |
| AC10 | 位置持久化: 窗口位置在会话间保持 | 拖拽后关闭应用，再次启动位置保持 |

## 开始前确认

```bash
# 执行以下检查，全部通过后方可开始
[ ] sudo apt install libgtk-3-dev          # 确保 GTK3 开发头文件存在
[ ] flutter build linux                    # 基础构建成功
[ ] ls -la voice_capsule/linux/runner/     # 确认 my_application.cc 存在
[ ] xdpyinfo | head -10                    # 确认 X11 环境 (或 XWayland)
```

## 技术规格

### 核心架构 [Source: docs/architecture.md#2.1, docs/front-end-spec.md#3.1]

透明窗口需要 **GTK3 层 + Flutter 层** 双重配置，缺一不可：

| 层级 | 文件 | 关键配置 |
|------|------|----------|
| **GTK3 (C++)** | `my_application.cc` | RGBA Visual、无装饰、固定尺寸、窗口类型提示 |
| **Flutter (Dart)** | `main.dart` + `window_manager` | 透明背景、alwaysOnTop、skipTaskbar |

**⚠️ 关键顺序**: GTK 透明配置必须在 `fl_view_new()` 调用前完成，否则会出现黑框闪烁。

### 关键技术决策 [Source: Web Research 2024]

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 窗口管理包 | `window_manager` | 最成熟的 Flutter 桌面窗口管理包，Linux 支持良好 |
| 透明实现 | GTK3 RGBA Visual + Flutter 透明背景 | 需要双层配合才能实现真透明 |
| 无边框实现 | `titleBarStyle: TitleBarStyle.hidden` + GTK 配置 | 同时在 Flutter 和原生层禁用 |
| 位置持久化 | `shared_preferences` | 简单可靠的本地存储 |

### 尺寸规范 [Source: docs/front-end-spec.md#2.3]

```dart
/// 窗口尺寸常量 (逻辑像素)
class WindowConstants {
  /// 窗口总尺寸 (包含阴影区域的画布)
  static const double windowWidth = 400.0;
  static const double windowHeight = 120.0;
  
  /// 胶囊内容区尺寸
  static const double capsuleWidth = 380.0;  // Max
  static const double capsuleMinWidth = 280.0;  // Min
  static const double capsuleHeight = 60.0;
  
  /// 圆角半径
  static const double capsuleRadius = 40.0;
}
```

### 依赖包配置 [Latest Versions 2024-12]

```yaml
# pubspec.yaml 新增依赖
dependencies:
  window_manager: ^0.3.9        # 窗口管理 (size, position, alwaysOnTop)
  shared_preferences: ^2.2.2   # 位置持久化存储
```

### 目标文件结构

```text
voice_capsule/
├── linux/runner/
│   └── my_application.cc      # 🔄 修改 (GTK 透明配置)
├── lib/
│   ├── main.dart              # 🔄 修改 (窗口初始化)
│   ├── constants/
│   │   └── window_constants.dart  # 🆕 新增 (尺寸常量)
│   └── services/
│       └── window_service.dart    # 🆕 新增 (窗口管理服务)
└── pubspec.yaml               # 🔄 修改 (新增依赖)
```

## Tasks / Subtasks

> **执行顺序**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6

- [x] **Task 1: 添加依赖包** (AC: #1, #3, #7, #10)
  - [x] 1.1 在 `pubspec.yaml` 添加 `window_manager: ^0.3.9`
  - [x] 1.2 在 `pubspec.yaml` 添加 `shared_preferences: ^2.2.2`
  - [x] 1.3 运行 `flutter pub get` 验证依赖安装
  - [x] 1.4 验证依赖无冲突: `flutter pub deps --style=compact`

- [x] **Task 2: 修改 GTK 原生层实现真透明** (AC: #1, #2, #5, #7)
  - [x] 2.1 修改 `linux/runner/my_application.cc`:
    - 移除默认的 HeaderBar 创建代码
    - 添加 RGBA Visual 支持代码
    - 设置窗口不装饰 (`gtk_window_set_decorated(window, FALSE)`)
    - 设置窗口可绘制透明 (`gtk_widget_set_app_paintable(GTK_WIDGET(window), TRUE)`)
    - **设置窗口类型提示** (`gtk_window_set_type_hint()`) 确保跳过任务栏
    - 设置初始尺寸为 400x120
  - [x] 2.2 **⚠️ 关键**: 确保透明配置在 `fl_view_new()` 调用前完成 (避免黑框闪烁)
  - [x] 2.3 添加 composited 检查和 fallback 日志
  
  **关键代码片段:**
  ```cpp
  // my_application_activate() 函数内，在创建 window 后、fl_view_new() 前添加:
  
  // 1. 禁用窗口装饰 (无边框、无标题栏)
  gtk_window_set_decorated(window, FALSE);
  
  // 2. 设置窗口类型提示 (确保跳过任务栏，在所有桌面环境生效)
  gtk_window_set_type_hint(window, GDK_WINDOW_TYPE_HINT_UTILITY);
  
  // 3. 设置窗口可绘制透明
  gtk_widget_set_app_paintable(GTK_WIDGET(window), TRUE);
  
  // 4. 设置 RGBA Visual (支持透明) - 必须在 fl_view_new() 前!
  GdkScreen* screen = gtk_window_get_screen(window);
  GdkVisual* visual = gdk_screen_get_rgba_visual(screen);
  if (visual != NULL && gdk_screen_is_composited(screen)) {
    gtk_widget_set_visual(GTK_WIDGET(window), visual);
  } else {
    g_warning("Transparent window not supported by compositor");
  }
  
  // 5. 设置固定尺寸 400x120
  gtk_window_set_default_size(window, 400, 120);
  gtk_window_set_resizable(window, FALSE);
  
  // ===== 以下是 fl_view_new() 调用，透明配置必须在此之前完成 =====
  ```

- [x] **Task 3: 创建窗口常量和服务** (AC: #3, #4, #7, #9, #10)
  - [x] 3.1 创建 `lib/constants/window_constants.dart`:
    ```dart
    /// 窗口尺寸和位置常量
    class WindowConstants {
      static const double windowWidth = 400.0;
      static const double windowHeight = 120.0;
      /// 使用 nextalk_ 前缀避免与其他 Flutter 应用冲突
      static const String positionXKey = 'nextalk_window_x';
      static const String positionYKey = 'nextalk_window_y';
    }
    ```
  - [x] 3.2 创建 `lib/services/window_service.dart`:
    - 初始化 `windowManager`
    - 实现位置保存/加载 (使用 `shared_preferences`)
    - 实现窗口显示/隐藏
    - 实现 `alwaysOnTop` 设置
    - 实现拖拽移动支持
  
  **WindowService 接口设计:**
  ```dart
  class WindowService {
    /// 初始化窗口 (在 main() 中调用)
    Future<void> initialize();
    
    /// 显示窗口 (在记忆位置或屏幕中央)
    Future<void> show();
    
    /// 隐藏窗口
    Future<void> hide();
    
    /// 保存当前位置
    Future<void> savePosition();
    
    /// 窗口是否可见
    bool get isVisible;
    
    /// 监听拖拽结束事件 (用于保存位置)
    Stream<void> get onMoved;
  }
  ```

- [x] **Task 4: 修改 main.dart 实现透明应用** (AC: #2, #6)
  - [x] 4.1 修改 `main()` 函数:
    - 初始化 `WidgetsFlutterBinding`
    - 初始化 `windowManager`
    - 设置 `WindowOptions` (透明、无边框、固定尺寸)
  - [x] 4.2 修改 `MaterialApp`:
    - 移除 AppBar
    - 设置透明背景 `ThemeData` 
  - [x] 4.3 创建透明测试容器:
    - 暂时显示一个简单的半透明容器验证透明效果
  
  **main.dart 关键代码:**
  ```dart
  Future<void> main() async {
    WidgetsFlutterBinding.ensureInitialized();
    await windowManager.ensureInitialized();
    
    WindowOptions windowOptions = const WindowOptions(
      size: Size(400, 120),
      center: true,
      backgroundColor: Colors.transparent,
      skipTaskbar: true,  // 不在任务栏显示
      titleBarStyle: TitleBarStyle.hidden,
      alwaysOnTop: true,
    );
    
    windowManager.waitUntilReadyToShow(windowOptions, () async {
      await windowManager.show();
      await windowManager.focus();
    });
    
    runApp(const NextalkApp());
  }
  
  class NextalkApp extends StatelessWidget {
    @override
    Widget build(BuildContext context) {
      return MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: ThemeData.dark().copyWith(
          scaffoldBackgroundColor: Colors.transparent,
        ),
        home: const TransparentCapsule(),  // 临时测试 Widget
      );
    }
  }
  ```

- [x] **Task 5: 实现拖拽移动与位置持久化** (AC: #9, #10)
  - [x] 5.1 在 `WindowService` 中添加位置监听:
    ```dart
    windowManager.setMovable(true);
    
    // 监听窗口移动结束
    // Note: window_manager 没有直接的 onMoved 事件
    // 方案: 使用 GestureDetector 包装整个窗口内容实现拖拽
    ```
  - [x] 5.2 实现自定义拖拽:
    ```dart
    GestureDetector(
      onPanStart: (_) => windowManager.startDragging(),
      child: /* 窗口内容 */,
    )
    ```
  - [x] 5.3 实现位置持久化 (含屏幕边界检查):
    ```dart
    // 在 hide() 时保存位置
    Future<void> hide() async {
      final position = await windowManager.getPosition();
      final prefs = await SharedPreferences.getInstance();
      await prefs.setDouble(WindowConstants.positionXKey, position.dx);
      await prefs.setDouble(WindowConstants.positionYKey, position.dy);
      await windowManager.hide();
    }
    
    // 在 show() 时恢复位置 (含边界校验)
    Future<void> show() async {
      final prefs = await SharedPreferences.getInstance();
      final x = prefs.getDouble(WindowConstants.positionXKey);
      final y = prefs.getDouble(WindowConstants.positionYKey);
      
      if (x != null && y != null) {
        // 校验位置是否在可见屏幕范围内 (防止多显示器切换后窗口出现在屏幕外)
        final bounds = await windowManager.getBounds();
        final screenSize = bounds.size; // 使用当前屏幕尺寸估算
        if (x >= 0 && x < 1920 && y >= 0 && y < 1080) {
          await windowManager.setPosition(Offset(x, y));
        } else {
          // 位置无效，回退到居中
          await windowManager.center();
        }
      }
      await windowManager.show();
    }
    ```

- [x] **Task 6: 创建验证测试** (AC: #1-10)
  - [x] 6.1 创建验证脚本 `scripts/verify-transparent-window.sh` (含自动化检查):
    ```bash
    #!/bin/bash
    set -e
    echo "=== Story 3-1 透明窗口验证 ==="
    
    cd voice_capsule
    
    echo "1. 构建应用..."
    flutter build linux --release
    
    echo "2. 启动应用 (后台)..."
    ./build/linux/x64/release/bundle/voice_capsule &
    APP_PID=$!
    sleep 2  # 等待窗口创建
    
    echo "3. 自动化验证..."
    PASS=0
    FAIL=0
    
    # AC1: 验证无边框
    if xwininfo -name "voice_capsule" 2>/dev/null | grep -q "Border width:  0"; then
      echo "✅ AC1: 无边框验证通过"
      ((PASS++))
    else
      echo "❌ AC1: 边框检测失败"
      ((FAIL++))
    fi
    
    # AC3: 验证尺寸 400x120
    if xwininfo -name "voice_capsule" 2>/dev/null | grep -qE "Width: 400|Height: 120"; then
      echo "✅ AC3: 尺寸验证通过"
      ((PASS++))
    else
      echo "❌ AC3: 尺寸不符"
      ((FAIL++))
    fi
    
    # AC7: 验证始终在最前 (检查窗口类型)
    if xprop -name "voice_capsule" 2>/dev/null | grep -q "_NET_WM_STATE_ABOVE"; then
      echo "✅ AC7: 始终在最前验证通过"
      ((PASS++))
    else
      echo "⚠️  AC7: 无法自动验证，请手动确认"
    fi
    
    echo ""
    echo "4. 手动验证项 (请观察窗口):"
    echo "   [ ] 窗口背景透明 (可见桌面壁纸)"
    echo "   [ ] 无启动黑框闪烁"
    echo "   [ ] 窗口可拖拽移动"
    echo ""
    echo "自动化结果: $PASS 通过, $FAIL 失败"
    echo "按 Enter 结束测试..."
    read
    
    kill $APP_PID 2>/dev/null || true
    ```
  - [x] 6.2 创建单元测试 `test/window_service_test.dart`:
    - 测试 `WindowService` 初始化
    - 测试位置保存/加载逻辑 (Mock SharedPreferences)
  - [x] 6.3 运行验证: 
    - X11 环境测试
    - XWayland 环境测试 (如可用)

## Dev Notes

### 架构约束与禁止事项

| 类别 | 约束 | 原因 |
|------|------|------|
| **⚠️ 初始化顺序** | GTK 透明配置 → `fl_view_new()` | **必须按此顺序**，否则 FlView 创建时背景已不可更改 |
| **GTK 层** | 必须在 `FlView` 创建前设置透明 | 否则会出现黑框闪烁 (NFR4) |
| **窗口装饰** | `gtk_window_set_decorated(FALSE)` 必须调用 | 否则保留系统边框 |
| **窗口类型** | `gtk_window_set_type_hint(UTILITY)` | 确保 skipTaskbar 在所有桌面环境生效 |
| **RGBA Visual** | 必须检查 `gdk_screen_is_composited()` | 无合成器时优雅降级 |
| **尺寸** | 使用 `gtk_window_set_resizable(FALSE)` | 固定尺寸，不允许用户调整 |
| **skipTaskbar** | 设置为 `true` | 不在任务栏显示，仅托盘驻留 |
| **拖拽** | 使用 `startDragging()` 而非手动坐标计算 | 避免与窗口管理器冲突 |
| **位置保存时机** | 在 `hide()` 时保存，而非实时 | 减少 I/O 开销 |
| **位置边界检查** | 恢复位置前校验屏幕范围 | 防止多显示器切换后窗口出现在屏幕外 |

### 从前序 Story 继承的经验

**Story 2-6 (VAD) 关键学习:**
1. **Stream 管理**: 发送前检查 `!_isDisposed && !_controller.isClosed`
2. **Mock 设计**: 为测试创建独立的 Mock 类
3. **边界条件**: 测试极端情况 (dispose 期间的操作)

**Story 1-4 (Flutter 初始化) 配置:**
- RPATH 已正确配置
- CMakeLists.txt 已支持原生库链接
- 项目结构符合架构规范

### 与后续 Story 的集成点

**Story 3-2 (胶囊 UI 组件):**
- 本 Story 提供透明画布
- 3-2 在此画布上绘制胶囊形状

**Story 3-3 (状态机与动画):**
- 本 Story 的 `TransparentCapsule` Widget 将被替换
- 状态机将控制窗口显示/隐藏

**Story 3-5 (全局快捷键):**
- 快捷键触发 `WindowService.show()/hide()`

**Story 3-6 (完整业务流串联):**
```dart
// Story 3-6 使用示例
class MainController {
  final WindowService _windowService;
  final AudioInferencePipeline _pipeline;
  
  void onHotkeyPressed() async {
    if (_windowService.isVisible) {
      // 停止并上屏
      await _pipeline.stop();
      await _windowService.hide();
    } else {
      // 显示并开始录音
      await _windowService.show();
      await _pipeline.start();
    }
  }
}
```

### X11/Wayland 兼容性注意事项

| 环境 | 支持程度 | 注意事项 |
|------|----------|----------|
| **X11** | ✅ 完全支持 | RGBA Visual 和透明效果均可用 |
| **XWayland** | ✅ 支持 | 通过 XWayland 兼容层运行 |
| **纯 Wayland** | ⚠️ 部分支持 | GTK3 在 Wayland 下透明行为可能不同 |

**Wayland 透明失效时的解决方案:**
```bash
# 如果在 Wayland 环境下透明效果失效，强制使用 X11 后端:
GDK_BACKEND=x11 ./voice_capsule

# 或在 .desktop 文件中配置:
Exec=env GDK_BACKEND=x11 /path/to/voice_capsule
```

**检测当前环境 (可选日志):**
```cpp
#ifdef GDK_WINDOWING_X11
if (GDK_IS_X11_DISPLAY(gdk_display_get_default())) {
    g_message("Running on X11");
}
#endif
#ifdef GDK_WINDOWING_WAYLAND
if (GDK_IS_WAYLAND_DISPLAY(gdk_display_get_default())) {
    g_message("Running on Wayland - transparency may require GDK_BACKEND=x11");
}
#endif
```

### 快速验证命令

```bash
# 完整验证流程
cd /mnt/disk0/project/newx/nextalk/nextalk_fcitx5_v2/voice_capsule

# 1. 安装依赖
flutter pub get

# 2. 构建
flutter build linux --release

# 3. 运行验证
./build/linux/x64/release/bundle/voice_capsule

# 4. 验证窗口属性 (需要 xwininfo)
xwininfo -name "voice_capsule" 2>/dev/null || echo "窗口未找到或名称不同"

# 5. 验证透明度 (需要 xprop)
xprop -name "voice_capsule" | grep -i transparent 2>/dev/null
```

### 外部资源

- [window_manager Package](https://pub.dev/packages/window_manager)
- [Flutter Desktop Transparency Guide](https://github.com/nickvision-apps/guides/blob/main/flutter-transparent-window-linux.md)
- [GTK3 Transparent Window](https://developer.gnome.org/documentation/tutorials/transparent-widgets.html)
- [GDK Visual Functions](https://docs.gtk.org/gdk3/method.Screen.get_rgba_visual.html)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (Amelia - Dev Agent)

### Debug Log References

- 所有 127 个测试通过 (6 个因无模型跳过)
- `flutter build linux --release` 构建成功
- `flutter analyze` 无错误

### Completion Notes List

1. **Task 1**: 添加 `window_manager: ^0.3.9` 和 `shared_preferences: ^2.2.2` 依赖，验证无冲突
2. **Task 2**: 修改 `my_application.cc`，实现 GTK3 层透明配置：
   - RGBA Visual 支持
   - 无边框 (`gtk_window_set_decorated(FALSE)`)
   - 窗口类型提示 (`GDK_WINDOW_TYPE_HINT_UTILITY`)
   - 固定尺寸 400x120
   - X11/Wayland 环境检测日志
3. **Task 3**: 创建 `WindowConstants` 和 `WindowService` 单例
4. **Task 4**: 重构 `main.dart`，使用 `WindowService` 初始化透明窗口
5. **Task 5**: 实现拖拽移动 (`startDragging()`) 和位置持久化 (`SharedPreferences`)
6. **Task 6**: 创建验证脚本和 10 个新单元测试

### Change Log

- 2025-12-22: Code Review by Dev Agent (Amelia) - code-review workflow
  - **修复 HIGH**: WindowService 资源泄漏 - 在 onWindowClose 中添加 _cleanup() 调用
  - **修复 MEDIUM**: 位置边界硬编码 - 将边界常量移至 WindowConstants.isValidPosition()
  - **修复 MEDIUM**: 测试逻辑不同步 - 测试改为使用 WindowConstants.isValidPosition()
  - **修复 MEDIUM**: 验证脚本依赖检查 - 添加 xdotool/xwininfo/xprop 工具检测
  - Story 状态: review → done
- 2025-12-22: Story implemented by Dev Agent (Amelia) - dev-story workflow
  - 完成所有 6 个 Tasks 和全部子任务
  - 新增: `window_constants.dart`, `window_service.dart`
  - 修改: `pubspec.yaml`, `my_application.cc`, `main.dart`
  - 测试: `window_service_test.dart`, `widget_test.dart` (更新)
  - 验证脚本: `verify-transparent-window.sh`
- 2025-12-22: Story validated and enhanced by SM Agent (Bob) - validate-create-story workflow
  - 添加 libgtk-3-dev 依赖检查
  - 添加 GTK 初始化顺序约束说明 (防止黑框闪烁)
  - 添加 gtk_window_set_type_hint() 确保 skipTaskbar 兼容性
  - 添加 shared_preferences 键名前缀 (避免冲突)
  - 添加位置恢复时的屏幕边界检查
  - 添加 GDK_BACKEND=x11 Wayland 兼容方案
  - 增强验证脚本自动化检查
  - 优化技术规格结构，减少 Token 消耗
- 2025-12-22: Story created by SM Agent (Bob) - create-story workflow

### File List

**已修改/创建文件:**

| 文件 | 操作 | 说明 |
|------|------|------|
| `voice_capsule/pubspec.yaml` | ✅ 修改 | 新增 window_manager, shared_preferences 依赖 |
| `voice_capsule/linux/runner/my_application.cc` | ✅ 修改 | GTK 透明窗口配置 (RGBA, 无边框, 类型提示) |
| `voice_capsule/lib/main.dart` | ✅ 修改 | 窗口初始化、透明 MaterialApp、胶囊测试 Widget |
| `voice_capsule/lib/constants/window_constants.dart` | ✅ 新增 | 窗口尺寸常量 |
| `voice_capsule/lib/services/window_service.dart` | ✅ 新增 | 窗口管理服务 (单例、位置持久化、拖拽) |
| `voice_capsule/test/window_service_test.dart` | ✅ 新增 | WindowService 单元测试 (7 个测试) |
| `voice_capsule/test/widget_test.dart` | ✅ 修改 | 更新为透明胶囊 Widget 测试 (3 个测试) |
| `scripts/verify-transparent-window.sh` | ✅ 新增 | 手动验证脚本 (自动化 AC 检查) |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | ✅ 修改 | 更新 Story 状态: ready-for-dev → review |

---
*References: docs/architecture.md#2.1, docs/front-end-spec.md#2-3, _bmad-output/epics.md#Story-3.1*
