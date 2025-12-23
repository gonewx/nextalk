import 'dart:async';
import 'dart:ui';

import 'package:shared_preferences/shared_preferences.dart';
import 'package:window_manager/window_manager.dart';

import '../constants/window_constants.dart';

/// 窗口管理服务
/// Story 3-1: 透明胶囊窗口基础
///
/// 功能:
/// - 初始化透明无边框窗口
/// - 窗口显示/隐藏控制
/// - 位置持久化 (SharedPreferences)
/// - 拖拽移动支持
class WindowService with WindowListener {
  WindowService._();

  static final WindowService instance = WindowService._();

  bool _isInitialized = false;
  bool _isVisible = false;
  SharedPreferences? _prefs;

  final StreamController<void> _onMovedController =
      StreamController<void>.broadcast();

  /// 窗口是否可见
  bool get isVisible => _isVisible;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 监听窗口移动结束事件 (用于保存位置)
  Stream<void> get onMoved => _onMovedController.stream;

  /// 初始化窗口 (在 main() 中调用)
  ///
  /// [showOnStartup] 是否在启动时显示窗口，默认 false (托盘驻留)
  ///
  /// 配置:
  /// - 透明背景
  /// - 无标题栏
  /// - 固定尺寸 400x120
  /// - 跳过任务栏
  /// - 始终在最前
  Future<void> initialize({bool showOnStartup = false}) async {
    if (_isInitialized) return;

    await windowManager.ensureInitialized();

    _prefs = await SharedPreferences.getInstance();

    // 注册窗口事件监听
    windowManager.addListener(this);

    const windowOptions = WindowOptions(
      size: Size(WindowConstants.windowWidth, WindowConstants.windowHeight),
      center: true,
      skipTaskbar: true, // 不在任务栏显示
      titleBarStyle: TitleBarStyle.hidden, // 无标题栏
      alwaysOnTop: true, // 始终在最前
    );

    await windowManager.waitUntilReadyToShow(windowOptions, () async {
      // 与参考项目保持一致：只做最基本的设置
      await windowManager.setAsFrameless();
      await _restorePosition();
      await windowManager.show();
      // 不调用 focus()，避免抢夺焦点

      // 根据参数决定是否保持显示
      if (!showOnStartup) {
        await windowManager.hide();
        _isVisible = false;
      } else {
        _isVisible = true;
      }
    });

    _isInitialized = true;
  }

  /// 显示窗口 (在记忆位置或屏幕中央)
  Future<void> show() async {
    if (!_isInitialized) {
      throw StateError(
          'WindowService not initialized. Call initialize() first.');
    }

    if (_isVisible) return;

    await windowManager.show();
    // 关键：在 show 之后立即设置 skipTaskbar，确保窗口管理器应用此设置
    await windowManager.setSkipTaskbar(true);
    // 注意：不调用 focus()，避免抢夺目标应用的焦点
    // 这样 Fcitx5 的 InputContext 焦点会保持在用户正在输入的应用中
    _isVisible = true;

    // 关键修复：在窗口可见后再设置位置
    // GTK/Wayland 在窗口隐藏时 setPosition() 可能被忽略
    await Future.delayed(const Duration(milliseconds: 50));
    await _restorePosition();
  }

  /// 隐藏窗口
  ///
  /// 抛出 [StateError] 如果服务未初始化。
  Future<void> hide() async {
    if (!_isInitialized) {
      throw StateError(
          'WindowService not initialized. Call initialize() first.');
    }
    if (!_isVisible) return;

    // 保存当前位置 - AC10
    await savePosition();

    await windowManager.hide();
    _isVisible = false;
  }

  /// Story 3-7: 设置窗口尺寸 (用于初始化向导)
  Future<void> setSize(double width, double height) async {
    if (!_isInitialized) return;
    await windowManager.setSize(Size(width, height));
  }

  /// Story 3-7: 重置为正常胶囊尺寸
  Future<void> resetToNormalSize() async {
    await setSize(WindowConstants.windowWidth, WindowConstants.windowHeight);
  }

  /// Story 3-7: 设置为初始化向导尺寸
  Future<void> setInitWizardSize() async {
    await setSize(
        WindowConstants.initWizardWidth, WindowConstants.initWizardHeight);
  }

  /// 保存当前位置
  Future<void> savePosition() async {
    if (!_isInitialized || _prefs == null) return;

    try {
      final position = await windowManager.getPosition();
      await _prefs!.setDouble(WindowConstants.positionXKey, position.dx);
      await _prefs!.setDouble(WindowConstants.positionYKey, position.dy);
    } catch (e) {
      // 忽略保存失败 (例如窗口已关闭)
    }
  }

  /// 恢复保存的位置 (含边界校验)
  Future<void> _restorePosition() async {
    if (_prefs == null) return;

    final x = _prefs!.getDouble(WindowConstants.positionXKey);
    final y = _prefs!.getDouble(WindowConstants.positionYKey);

    if (x != null && y != null) {
      // 使用 WindowConstants 中定义的边界校验
      if (WindowConstants.isValidPosition(x, y)) {
        await windowManager.setPosition(Offset(x, y));
        return;
      }
    }

    // 位置无效或未保存，回退到居中
    await windowManager.center();
  }

  /// 开始拖拽窗口 (在 GestureDetector.onPanStart 中调用)
  Future<void> startDragging() async {
    if (!_isInitialized) return;
    await windowManager.startDragging();
  }

  // ============================================
  // WindowListener 实现
  // ============================================

  @override
  void onWindowMove() {
    // 窗口移动中 (可用于实时更新 UI)
  }

  @override
  void onWindowMoved() {
    // 窗口移动结束 - 保存位置
    savePosition();
    _onMovedController.add(null);
  }

  @override
  void onWindowClose() {
    // 窗口关闭前保存位置并清理资源
    savePosition();
    _cleanup();
  }

  /// 内部清理方法 (避免重复清理)
  void _cleanup() {
    if (!_isInitialized) return;
    windowManager.removeListener(this);
    if (!_onMovedController.isClosed) {
      _onMovedController.close();
    }
    _isInitialized = false;
  }

  /// 释放资源 (供外部调用，如应用生命周期管理)
  void dispose() {
    savePosition();
    _cleanup();
  }

  @override
  void onWindowFocus() {}

  @override
  void onWindowBlur() {}

  @override
  void onWindowMaximize() {}

  @override
  void onWindowUnmaximize() {}

  @override
  void onWindowMinimize() {}

  @override
  void onWindowRestore() {}

  @override
  void onWindowResize() {}

  @override
  void onWindowResized() {}

  @override
  void onWindowEnterFullScreen() {}

  @override
  void onWindowLeaveFullScreen() {}

  @override
  void onWindowEvent(String eventName) {}

  @override
  void onWindowDocked() {}

  @override
  void onWindowUndocked() {}
}
