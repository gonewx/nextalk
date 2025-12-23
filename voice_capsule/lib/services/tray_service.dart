import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:system_tray/system_tray.dart';

import '../constants/tray_constants.dart';
import 'hotkey_service.dart';
import 'window_service.dart';

/// 退出回调类型 - 用于注入 Pipeline 释放逻辑
typedef ExitCallback = Future<void> Function();

/// Story 3-7: 托盘状态枚举 (用于图标切换, AC19)
/// system_tray 不支持角标，使用不同图标文件模拟
enum TrayStatus {
  /// 正常状态
  normal,

  /// 警告状态 (如连接断开)
  warning,

  /// 错误状态 (如严重错误)
  error,
}

/// 系统托盘服务 - Story 3-4
///
/// 功能:
/// - 初始化系统托盘图标
/// - 构建上下文菜单 (显示/隐藏、设置、退出)
/// - 处理托盘图标点击事件 (左键切换窗口)
/// - 处理菜单点击事件
/// - 资源释放 (退出时调用 onBeforeExit 回调)
///
/// 错误处理:
/// - 如果系统不支持托盘 (如某些 Wayland 配置)，优雅降级继续运行
class TrayService {
  TrayService._();

  static final TrayService instance = TrayService._();

  final SystemTray _systemTray = SystemTray();
  bool _isInitialized = false;
  bool _initializationFailed = false;

  /// 退出前回调 (由 main.dart 或 Story 3-6 注入 Pipeline 释放逻辑)
  ExitCallback? onBeforeExit;

  /// Story 3-7: 重新连接 Fcitx5 回调 (AC16)
  Future<void> Function()? onReconnectFcitx;

  /// Story 3-7: 当前托盘状态
  TrayStatus _currentStatus = TrayStatus.normal;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 初始化是否失败 (用于诊断)
  bool get initializationFailed => _initializationFailed;

  /// Story 3-7: 当前托盘状态
  TrayStatus get currentStatus => _currentStatus;

  /// Story 3-7: 更新托盘状态 (切换图标, AC19)
  /// system_tray 不支持角标，使用不同图标文件模拟
  Future<void> updateStatus(TrayStatus status) async {
    if (!_isInitialized || _currentStatus == status) return;
    _currentStatus = status;

    final iconName = switch (status) {
      TrayStatus.normal => TrayConstants.iconPath,
      TrayStatus.warning => TrayConstants.iconWarningPath,
      TrayStatus.error => TrayConstants.iconErrorPath,
    };

    try {
      final executableDir = File(Platform.resolvedExecutable).parent;
      final iconPath = '${executableDir.path}/data/flutter_assets/$iconName';
      await _systemTray.setImage(iconPath);
    } catch (e) {
      debugPrint('TrayService: 更新图标失败: $e');
    }
  }

  /// 初始化托盘服务 (必须在 WindowService 之后调用)
  ///
  /// 如果初始化失败 (系统不支持托盘、图标文件缺失等)，
  /// 将记录错误并继续运行，托盘功能不可用。
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      final iconPath = await _getIconPath();

      await _systemTray.initSystemTray(
        title: TrayConstants.appName,
        iconPath: iconPath,
        toolTip: TrayConstants.appName,
      );

      await _buildMenu();

      _systemTray.registerSystemTrayEventHandler(_handleTrayEvent);

      _isInitialized = true;
    } catch (e) {
      // 降级: 托盘不可用时继续运行，但无托盘图标
      _initializationFailed = true;
      debugPrint('TrayService: 初始化失败，托盘功能不可用: $e');
      // 应用仍可通过快捷键 (Story 3-5) 使用
    }
  }

  /// 获取托盘图标绝对路径
  Future<String> _getIconPath() async {
    final executableDir = File(Platform.resolvedExecutable).parent;
    return '${executableDir.path}/data/flutter_assets/${TrayConstants.iconPath}';
  }

  /// 构建托盘右键菜单
  /// Story 3-7: 新增"重新连接 Fcitx5"菜单项 (AC16)
  Future<void> _buildMenu() async {
    final menu = Menu();
    await menu.buildFrom([
      MenuItemLabel(label: TrayConstants.menuTitle, enabled: false),
      MenuSeparator(),
      MenuItemLabel(
        label: TrayConstants.menuShowHide,
        onClicked: (_) => _toggleWindow(),
      ),
      MenuItemLabel(
        label: TrayConstants.menuReconnectFcitx,  // AC16: 新增
        onClicked: (_) => _reconnectFcitx(),
      ),
      MenuItemLabel(label: TrayConstants.menuSettings, enabled: false),
      MenuSeparator(),
      MenuItemLabel(
        label: TrayConstants.menuExit,
        onClicked: (_) => _exitApp(),
      ),
    ]);
    await _systemTray.setContextMenu(menu);
  }

  /// Story 3-7: 重新连接 Fcitx5 (AC16)
  Future<void> _reconnectFcitx() async {
    if (onReconnectFcitx != null) {
      try {
        await onReconnectFcitx!();
        await updateStatus(TrayStatus.normal);
        debugPrint('TrayService: Fcitx5 重连成功');
      } catch (e) {
        debugPrint('TrayService: Fcitx5 重连失败: $e');
        await updateStatus(TrayStatus.warning);
      }
    } else {
      debugPrint('TrayService: onReconnectFcitx 回调未设置');
    }
  }

  /// 处理托盘图标事件
  void _handleTrayEvent(String eventName) {
    if (eventName == kSystemTrayEventClick) {
      // 左键点击 - 切换窗口显隐 (AC10)
      _toggleWindow();
    } else if (eventName == kSystemTrayEventRightClick) {
      // 右键点击 - 弹出菜单 (AC3)
      _systemTray.popUpContextMenu();
    }
  }

  /// 切换窗口显隐 (AC6, AC10, AC11)
  Future<void> _toggleWindow() async {
    final ws = WindowService.instance;
    if (ws.isVisible) {
      await ws.hide();
    } else {
      await ws.show();
    }
  }

  /// 退出应用 - ⚠️ 必须释放所有资源 (AC7, AC8)
  Future<void> _exitApp() async {
    // 0. 注销全局快捷键 (Story 3-5 AC9)
    await HotkeyService.instance.dispose();

    // 1. 调用外部注入的释放回调 (Pipeline/AudioCapture/SherpaService)
    //    由 Story 3-6 或 main.dart 在初始化时注入
    if (onBeforeExit != null) {
      await onBeforeExit!();
    }

    // 2. 释放窗口服务
    WindowService.instance.dispose();

    // 3. 销毁托盘
    await _systemTray.destroy();

    // 4. 退出进程
    exit(0);
  }

  /// 释放托盘资源
  Future<void> dispose() async {
    if (!_isInitialized) return;
    await _systemTray.destroy();
    _isInitialized = false;
  }
}




