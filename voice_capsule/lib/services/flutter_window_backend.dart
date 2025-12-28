import 'dart:async';
import 'dart:ui';

import 'package:screen_retriever/screen_retriever.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:window_manager/window_manager.dart';

import '../constants/window_constants.dart';

/// Flutter 原生窗口后端
/// SCP-002: 简化版 - 唯一的窗口后端实现
class FlutterWindowBackend with WindowListener {
  FlutterWindowBackend();

  SharedPreferences? _prefs;
  bool _isInitialized = false;
  bool _isVisible = false;

  final StreamController<void> _onMovedController =
      StreamController<void>.broadcast();

  String get name => 'FlutterWindowBackend';

  bool get isInitialized => _isInitialized;

  bool get isVisible => _isVisible;

  /// 监听窗口移动结束事件
  Stream<void> get onMoved => _onMovedController.stream;

  Future<void> initialize() async {
    if (_isInitialized) return;

    await windowManager.ensureInitialized();
    _prefs = await SharedPreferences.getInstance();

    // 注册窗口事件监听
    windowManager.addListener(this);

    const windowOptions = WindowOptions(
      size: Size(WindowConstants.windowWidth, WindowConstants.windowHeight),
      center: true,
      skipTaskbar: true,
      titleBarStyle: TitleBarStyle.hidden,
      alwaysOnTop: true,
    );

    await windowManager.waitUntilReadyToShow(windowOptions, () async {
      await windowManager.setAsFrameless();
      await _restorePosition();
      await windowManager.show(inactive: true);
      await windowManager.hide();
      _isVisible = false;
    });

    _isInitialized = true;
  }

  Future<void> show() async {
    if (!_isInitialized) return;
    if (_isVisible) return;

    await windowManager.show(inactive: true);
    await windowManager.setSkipTaskbar(true);
    _isVisible = true;

    // 在窗口可见后再设置位置
    await Future.delayed(const Duration(milliseconds: 50));
    await _restorePosition();
  }

  Future<void> hide() async {
    if (!_isInitialized) return;
    if (!_isVisible) return;

    await savePosition();
    await windowManager.hide();
    _isVisible = false;
  }

  Future<void> setPosition(double x, double y) async {
    if (!_isInitialized) return;
    await windowManager.setPosition(Offset(x, y));
  }

  Future<(double x, double y)?> getPosition() async {
    if (!_isInitialized) return null;
    final pos = await windowManager.getPosition();
    return (pos.dx, pos.dy);
  }

  Future<void> savePosition() async {
    if (!_isInitialized || _prefs == null) return;

    try {
      final position = await windowManager.getPosition();
      await _prefs!.setDouble(WindowConstants.positionXKey, position.dx);
      await _prefs!.setDouble(WindowConstants.positionYKey, position.dy);
    } catch (e) {
      // 忽略保存失败
    }
  }

  Future<void> setSize(double width, double height) async {
    if (!_isInitialized) return;
    await windowManager.setSize(Size(width, height));
  }

  Future<void> setState(String state) async {
    // Flutter 窗口不直接处理状态，由 UI 层处理
  }

  Future<void> setText(String text) async {
    // Flutter 窗口不直接处理文本，由 UI 层处理
  }

  Future<void> resetPosition() async {
    if (_prefs != null) {
      await _prefs!.remove(WindowConstants.positionXKey);
      await _prefs!.remove(WindowConstants.positionYKey);
    }
    await _setDefaultPosition();
  }

  Future<void> startDragging() async {
    if (!_isInitialized) return;
    await windowManager.startDragging();
  }

  Future<void> _restorePosition() async {
    if (_prefs == null) return;

    final x = _prefs!.getDouble(WindowConstants.positionXKey);
    final y = _prefs!.getDouble(WindowConstants.positionYKey);

    if (x != null && y != null) {
      if (WindowConstants.isValidPosition(x, y)) {
        await windowManager.setPosition(Offset(x, y));
        return;
      }
    }

    await _setDefaultPosition();
  }

  Future<void> _setDefaultPosition() async {
    try {
      final primaryDisplay = await screenRetriever.getPrimaryDisplay();
      final screenWidth = primaryDisplay.size.width;
      final screenHeight = primaryDisplay.size.height;

      final x = (screenWidth - WindowConstants.windowWidth) / 2;
      final y = screenHeight - WindowConstants.windowHeight - 80;

      await windowManager.setPosition(Offset(x, y));
      return;
    } catch (e) {
      // 回退到普通居中
    }

    await windowManager.center();
  }

  void dispose() {
    savePosition();
    windowManager.removeListener(this);
    if (!_onMovedController.isClosed) {
      _onMovedController.close();
    }
    _isInitialized = false;
  }

  // WindowListener 实现
  @override
  void onWindowMove() {}

  @override
  void onWindowMoved() {
    savePosition();
    _onMovedController.add(null);
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
}
