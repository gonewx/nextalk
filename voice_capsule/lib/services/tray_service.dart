import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:system_tray/system_tray.dart';

import '../constants/settings_constants.dart';
import '../constants/tray_constants.dart';
import 'hotkey_service.dart';
import 'language_service.dart';
import 'model_manager.dart';
import 'settings_service.dart';
import 'window_service.dart';

/// 退出回调类型 - 用于注入 Pipeline 释放逻辑
typedef ExitCallback = Future<void> Function();

/// 显示初始化向导回调类型
typedef ShowInitWizardCallback = void Function(EngineType targetEngine);

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

  /// 显示初始化向导回调 (当模型不存在时)
  ShowInitWizardCallback? onShowInitWizard;

  /// ModelManager 引用 (用于检查模型状态)
  ModelManager? _modelManager;

  /// Story 3-7: 当前托盘状态
  TrayStatus _currentStatus = TrayStatus.normal;

  /// Story 2-7: 实际使用的引擎类型 (可能与配置不同)
  EngineType? _actualEngineType;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 初始化是否失败 (用于诊断)
  bool get initializationFailed => _initializationFailed;

  /// Story 3-7: 当前托盘状态
  TrayStatus get currentStatus => _currentStatus;

  /// Story 2-7: 获取实际使用的引擎类型
  EngineType? get actualEngineType => _actualEngineType;

  /// Story 2-7: 设置实际使用的引擎类型 (由 main.dart 在初始化时调用)
  void setActualEngineType(EngineType type) {
    _actualEngineType = type;
  }

  /// 设置 ModelManager 引用 (由 main.dart 在初始化时调用)
  void setModelManager(ModelManager manager) {
    _modelManager = manager;
  }

  /// Story 2-7: 检查是否发生了引擎回退
  bool get hasEngineFallback {
    if (_actualEngineType == null) return false;
    return _actualEngineType != SettingsService.instance.engineType;
  }

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

  /// Story 3-8: 公开重建菜单方法 (Task 4.1)
  /// 语言切换时需要调用此方法更新菜单文本
  Future<void> rebuildMenu() async {
    if (!_isInitialized) return;
    await _buildMenu();
    debugPrint('TrayService: 菜单已重建');
  }

  /// 获取托盘图标绝对路径
  Future<String> _getIconPath() async {
    final executableDir = File(Platform.resolvedExecutable).parent;
    return '${executableDir.path}/data/flutter_assets/${TrayConstants.iconPath}';
  }

  /// 构建托盘右键菜单
  /// Story 3-7: 新增"重新连接 Fcitx5"菜单项 (AC16)
  /// Story 3-8: 国际化菜单文本 + 语言切换子菜单 (AC2, AC5, AC6)
  /// Story 2-7: 引擎切换子菜单 (AC6), 显示实际引擎 (AC7)
  Future<void> _buildMenu() async {
    final currentModelType = SettingsService.instance.modelType;
    final configuredEngineType = SettingsService.instance.engineType;
    final lang = LanguageService.instance;

    // Story 2-7: 获取实际使用的引擎 (可能因回退与配置不同)
    final actualEngine = _actualEngineType ?? configuredEngineType;

    final menu = Menu();
    await menu.buildFrom([
      MenuItemLabel(label: TrayConstants.appName, enabled: false),
      MenuSeparator(),
      MenuItemLabel(
        label: lang.tr('tray_show_hide'),
        onClicked: (_) => _toggleWindow(),
      ),
      MenuItemLabel(
        label: lang.tr('tray_reconnect'),
        onClicked: (_) => _reconnectFcitx(),
      ),
      MenuSeparator(),
      // Story 2-7: 模型设置子菜单 (AC6, AC7)
      // 简化设计：checkbox 表示当前实际使用的引擎
      SubMenu(
        label: lang.tr('tray_model_settings'),
        children: [
          // Zipformer 子菜单 (含版本选择)
          SubMenu(
            label: lang.tr('tray_engine_zipformer'),
            children: [
              MenuItemCheckbox(
                label: lang.tr('tray_model_int8'),
                checked: actualEngine == EngineType.zipformer &&
                    currentModelType == ModelType.int8,
                onClicked: (_) => _switchToZipformer(ModelType.int8),
              ),
              MenuItemCheckbox(
                label: lang.tr('tray_model_standard'),
                checked: actualEngine == EngineType.zipformer &&
                    currentModelType == ModelType.standard,
                onClicked: (_) => _switchToZipformer(ModelType.standard),
              ),
            ],
          ),
          // SenseVoice 单项 (无版本选择)
          MenuItemCheckbox(
            label: lang.tr('tray_engine_sensevoice'),
            checked: actualEngine == EngineType.sensevoice,
            onClicked: (_) => _switchEngine(EngineType.sensevoice),
          ),
        ],
      ),
      MenuSeparator(),
      // Story 3-8: 语言切换子菜单 (AC2)
      SubMenu(
        label: lang.tr('tray_language'),
        children: [
          MenuItemCheckbox(
            label: '简体中文',
            checked: lang.isZh,
            onClicked: (_) => _switchLanguage('zh'),
          ),
          MenuItemCheckbox(
            label: 'English',
            checked: !lang.isZh,
            onClicked: (_) => _switchLanguage('en'),
          ),
        ],
      ),
      MenuItemLabel(
        label: lang.tr('tray_settings'),
        onClicked: (_) => _openConfigDirectory(),
      ),
      MenuSeparator(),
      MenuItemLabel(
        label: lang.tr('tray_exit'),
        onClicked: (_) => _exitApp(),
      ),
    ]);
    await _systemTray.setContextMenu(menu);
  }

  /// Story 3-8: 切换语言 (AC3)
  Future<void> _switchLanguage(String languageCode) async {
    await LanguageService.instance.switchLanguage(languageCode);
    // 语言切换后重建菜单以更新文本
    await rebuildMenu();
    debugPrint('TrayService: 语言已切换为 $languageCode');
  }

  /// 切换到 Zipformer 引擎并设置模型版本
  Future<void> _switchToZipformer(ModelType modelType) async {
    // 检查 Zipformer 模型是否存在
    if (_modelManager != null && !_modelManager!.isEngineReady(EngineType.zipformer)) {
      // 模型不存在，显示初始化向导
      debugPrint('TrayService: Zipformer 模型不存在，显示初始化向导');
      _showInitWizardForEngine(EngineType.zipformer);
      return;
    }

    // 使用实际引擎类型判断是否需要切换（可能因回退与配置不同）
    final actualEngine = _actualEngineType ?? SettingsService.instance.engineType;
    final currentModelType = SettingsService.instance.modelType;

    // 如果实际使用的已经是 Zipformer 且版本相同，无需操作
    if (actualEngine == EngineType.zipformer &&
        currentModelType == modelType) {
      return;
    }

    // 先切换模型版本
    if (currentModelType != modelType) {
      await SettingsService.instance.switchModelType(modelType);
    }

    // 再切换引擎 (如果实际使用的不是 Zipformer)
    if (actualEngine != EngineType.zipformer) {
      await _switchEngine(EngineType.zipformer);
    } else {
      // 引擎不变但版本变了，重建菜单并发送通知
      await _buildMenu();
      try {
        await Process.run('notify-send', [
          '-a',
          'Nextalk',
          '-i',
          'dialog-information',
          'Nextalk',
          LanguageService.instance.tr('tray_model_switch_notice'),
        ]);
      } catch (e) {
        debugPrint('TrayService: 发送通知失败: $e');
      }
    }
  }

  /// Story 2-7: 切换 ASR 引擎 (AC6)
  /// 注意：由于 onnxruntime 限制，引擎切换需要销毁并重建 Pipeline
  Future<void> _switchEngine(EngineType newType) async {
    // 检查目标引擎的模型是否存在
    if (_modelManager != null && !_modelManager!.isEngineReady(newType)) {
      // 模型不存在，显示初始化向导
      debugPrint('TrayService: ${newType.name} 模型不存在，显示初始化向导');
      _showInitWizardForEngine(newType);
      return;
    }

    // 使用实际引擎类型判断是否需要切换（可能因回退与配置不同）
    final actualEngine = _actualEngineType ?? SettingsService.instance.engineType;
    if (actualEngine == newType) {
      return; // 已经是目标引擎，无需切换
    }

    final lang = LanguageService.instance;

    // 发送切换中通知
    try {
      await Process.run('notify-send', [
        '-a',
        'Nextalk',
        '-i',
        'dialog-information',
        'Nextalk',
        lang.tr('tray_engine_switching'),
      ]);
    } catch (e) {
      debugPrint('TrayService: 发送切换通知失败: $e');
    }

    final success = await SettingsService.instance.switchEngineType(newType);
    if (success) {
      // 更新实际引擎类型 (Story 2-7: AC7)
      _actualEngineType = newType;

      // 重新构建菜单以更新选中状态
      await _buildMenu();
      debugPrint('TrayService: 引擎切换成功: $newType');

      // 获取本地化的引擎显示名称
      final engineDisplayName = _getEngineDisplayName(newType);

      // 发送切换成功通知 (包含引擎名称)
      try {
        await Process.run('notify-send', [
          '-a',
          'Nextalk',
          '-i',
          'dialog-information',
          'Nextalk',
          lang.trWithParams('tray_engine_switch_success', {'engine': engineDisplayName}),
        ]);
      } catch (e) {
        debugPrint('TrayService: 发送通知失败: $e');
      }
    } else {
      debugPrint('TrayService: 引擎切换失败');
      // 发送切换失败通知 (包含回退引擎名称)
      final fallbackEngineName = _getEngineDisplayName(SettingsService.instance.engineType);
      try {
        await Process.run('notify-send', [
          '-a',
          'Nextalk',
          '-i',
          'dialog-warning',
          'Nextalk',
          lang.trWithParams('tray_engine_switch_fallback', {'engine': fallbackEngineName}),
        ]);
      } catch (e) {
        debugPrint('TrayService: 发送通知失败: $e');
      }
    }
  }

  /// 获取引擎的本地化显示名称 (Story 2-7: AC6)
  String _getEngineDisplayName(EngineType type) {
    final lang = LanguageService.instance;
    return switch (type) {
      EngineType.zipformer => lang.tr('tray_engine_zipformer'),
      EngineType.sensevoice => lang.tr('tray_engine_sensevoice'),
    };
  }

  /// 显示初始化向导以下载指定引擎的模型
  void _showInitWizardForEngine(EngineType targetEngine) {
    // 发送通知告知用户需要下载模型
    final lang = LanguageService.instance;
    final engineName = _getEngineDisplayName(targetEngine);
    try {
      Process.run('notify-send', [
        '-a',
        'Nextalk',
        '-i',
        'dialog-information',
        'Nextalk',
        lang.trWithParams('tray_model_not_found', {'engine': engineName}),
      ]);
    } catch (e) {
      debugPrint('TrayService: 发送通知失败: $e');
    }

    // 显示窗口并触发初始化向导
    WindowService.instance.show();
    if (onShowInitWizard != null) {
      onShowInitWizard!(targetEngine);
    }
  }

  /// 打开配置目录
  Future<void> _openConfigDirectory() async {
    await SettingsService.instance.openConfigDirectory();
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
