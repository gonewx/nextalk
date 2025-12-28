import 'dart:async';
import 'dart:ui';

import 'package:shared_preferences/shared_preferences.dart';
import 'package:window_manager/window_manager.dart';

import '../constants/window_constants.dart';
import 'flutter_window_backend.dart';

/// 窗口管理服务
/// SCP-002: 简化版 - 只使用 Flutter 原生窗口
///
/// 功能:
/// - 透明无边框窗口管理
/// - 位置记忆和恢复
/// - 拖拽支持
class WindowService with WindowListener {
  WindowService._();

  static final WindowService instance = WindowService._();

  /// Flutter 窗口后端
  FlutterWindowBackend? _backend;

  bool _isInitialized = false;
  SharedPreferences? _prefs;

  /// 是否处于初始化向导模式 (此时快捷键释放不应隐藏窗口)
  bool _isInInitWizardMode = false;

  /// 是否阻止自动隐藏 (用于显示需要用户操作的 UI，如错误状态)
  bool _preventAutoHide = false;

  // ============================================
  // 公开属性
  // ============================================

  /// 窗口是否可见
  bool get isVisible => _backend?.isVisible ?? false;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 是否处于初始化向导模式
  bool get isInInitWizardMode => _isInInitWizardMode;

  /// 是否阻止自动隐藏
  bool get preventAutoHide => _preventAutoHide;
  set preventAutoHide(bool value) => _preventAutoHide = value;

  // ============================================
  // 初始化
  // ============================================

  /// 初始化窗口服务
  ///
  /// [showOnStartup] 是否在启动时显示窗口，默认 false (托盘驻留)
  Future<void> initialize({bool showOnStartup = false}) async {
    if (_isInitialized) return;

    _prefs = await SharedPreferences.getInstance();

    // 初始化 Flutter 窗口后端
    _backend = FlutterWindowBackend();
    await _backend!.initialize();
    _log('Flutter window backend initialized');

    if (showOnStartup) {
      await show();
    } else {
      await hide();
    }

    _isInitialized = true;
  }

  // ============================================
  // 窗口控制
  // ============================================

  /// 显示窗口
  Future<void> show() async {
    if (!_isInitialized || _backend == null) {
      throw StateError('WindowService not initialized');
    }

    await _backend!.show();
  }

  /// 隐藏窗口
  Future<void> hide() async {
    if (!_isInitialized || _backend == null) return;

    await _backend!.hide();
  }

  /// 设置窗口尺寸 (用于初始化向导)
  Future<void> setSize(double width, double height) async {
    if (!_isInitialized || _backend == null) return;
    await _backend!.setSize(width, height);
  }

  /// 重置为正常胶囊尺寸
  Future<void> resetToNormalSize() async {
    _isInInitWizardMode = false;
    await setSize(WindowConstants.windowWidth, WindowConstants.windowHeight);
  }

  /// 设置为初始化向导尺寸
  Future<void> setInitWizardSize() async {
    _isInInitWizardMode = true;
    await setSize(
        WindowConstants.initWizardWidth, WindowConstants.initWizardHeight);
  }

  /// 动态调整窗口高度以适应内容
  Future<void> setExpandedMode(bool expanded) async {
    if (!_isInitialized || _backend == null) return;
    final targetHeight = expanded
        ? WindowConstants.windowHeightExpanded
        : WindowConstants.windowHeight;
    await _backend!.setSize(WindowConstants.windowWidth, targetHeight);
  }

  /// 设置状态 (兼容性占位)
  Future<void> setState(String state) async {
    if (!_isInitialized || _backend == null) return;
    await _backend!.setState(state);
  }

  /// 设置文本 (兼容性占位)
  Future<void> setText(String text) async {
    if (!_isInitialized || _backend == null) return;
    await _backend!.setText(text);
  }

  /// 保存当前位置
  Future<void> savePosition() async {
    if (!_isInitialized || _backend == null) return;
    await _backend!.savePosition();
  }

  /// 开始拖拽窗口
  Future<void> startDragging() async {
    if (!_isInitialized || _backend == null) return;
    await _backend!.startDragging();
  }

  // ============================================
  // WindowListener 实现
  // ============================================

  @override
  void onWindowMove() {}

  @override
  void onWindowMoved() {
    savePosition();
  }

  @override
  void onWindowClose() {
    savePosition();
    dispose();
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

  // ============================================
  // 清理
  // ============================================

  void dispose() {
    _backend?.dispose();
    _isInitialized = false;
  }

  void _log(String message) {
    // ignore: avoid_print
    print('[WindowService] $message');
  }
}
