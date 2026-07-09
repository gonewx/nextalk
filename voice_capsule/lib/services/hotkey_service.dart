import 'dart:io';

import 'package:yaml/yaml.dart';

import '../constants/hotkey_constants.dart';
import '../constants/settings_constants.dart';

/// 快捷键按下回调类型
typedef HotkeyPressedCallback = Future<void> Function();

/// Story 3-10: 当前快捷键触发模式
///
/// 用于托盘/设置界面展示用户当前实际生效的快捷键方案。
enum HotkeyMode {
  /// Portal 全局快捷键（第四代，应用内注册，零配置）
  portal,

  /// 系统快捷键 + nextalk-toggle 回退（第三代，需用户手动配置）
  system,
}

/// 快捷键配置数据
class HotkeyConfig {
  final String key;
  final List<String> modifiers;

  const HotkeyConfig({
    required this.key,
    required this.modifiers,
  });

  /// 默认快捷键配置 (Alt+Space)
  static const HotkeyConfig defaultConfig = HotkeyConfig(
    key: 'space',
    modifiers: ['alt'],
  );

  /// 转换为人类可读格式
  String toDisplayString() {
    final parts = <String>[];

    // 添加修饰键
    for (final modifier in modifiers) {
      parts.add(_modifierDisplayName(modifier));
    }

    // 添加主键
    parts.add(_keyDisplayName(key));

    return parts.join(' + ');
  }

  String _modifierDisplayName(String modifier) {
    return switch (modifier) {
      'ctrl' || 'ctrlLeft' || 'ctrlRight' => 'Ctrl',
      'shift' || 'shiftLeft' || 'shiftRight' => 'Shift',
      'alt' || 'altLeft' || 'altRight' => 'Alt',
      'super' || 'superLeft' || 'superRight' => 'Super',
      _ => modifier,
    };
  }

  String _keyDisplayName(String key) {
    return switch (key) {
      'altRight' => 'Right Alt',
      'altLeft' => 'Left Alt',
      'space' => 'Space',
      _ when key.length == 1 => key.toUpperCase(),
      _ => key,
    };
  }

  @override
  String toString() => toDisplayString();
}

/// 快捷键配置服务 - SCP-002 简化版
///
/// 职责:
/// - 加载配置文件或使用默认快捷键
/// - 提供当前快捷键配置信息
///
/// 注意: SCP-002 极简架构下，快捷键由系统原生快捷键设置配置，
/// 本服务仅用于读取配置和显示信息，不再同步到输入法插件
class HotkeyService {
  HotkeyService._();
  static final HotkeyService instance = HotkeyService._();

  HotkeyConfig? _currentConfig;
  bool _isInitialized = false;

  /// Story 3-10: 当前快捷键模式（默认系统快捷键；Portal 注册成功后由
  /// main.dart 更新为 portal）。供托盘与 UI 展示当前生效方案。
  HotkeyMode hotkeyMode = HotkeyMode.system;

  /// 快捷键按下回调 (由 HotkeyController 注入)
  /// 保留此字段以保持向后兼容
  HotkeyPressedCallback? onHotkeyPressed;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 当前快捷键配置
  HotkeyConfig? get currentConfig => _currentConfig;

  /// 初始化服务
  ///
  /// 流程:
  /// 1. 加载配置文件或使用默认快捷键
  Future<void> initialize() async {
    if (_isInitialized) return;

    // 加载配置
    _currentConfig = await _loadHotkeyConfig();

    // ignore: avoid_print
    print('[HotkeyService] ✅ 配置加载完成: ${_currentConfig!.toDisplayString()}');

    _isInitialized = true;
  }

  /// 加载快捷键配置
  Future<HotkeyConfig> _loadHotkeyConfig() async {
    try {
      final configFile = _getConfigFile();
      if (await configFile.exists()) {
        final content = await configFile.readAsString();
        final yaml = loadYaml(content);

        if (yaml != null && yaml['hotkey'] != null) {
          final hotkeyConfig = yaml['hotkey'];
          final keyName = hotkeyConfig['key'] as String?;
          final modifierNames =
              (hotkeyConfig['modifiers'] as List?)?.cast<String>() ?? [];

          if (keyName != null && HotkeyConstants.keyToFcitx5.containsKey(keyName)) {
            // ignore: avoid_print
            print('[HotkeyService] 从配置文件加载快捷键: $keyName + $modifierNames');

            return HotkeyConfig(
              key: keyName,
              modifiers: modifierNames
                  .where((m) => HotkeyConstants.modifierToFcitx5.containsKey(m))
                  .toList(),
            );
          }
        }
      }
    } catch (e) {
      // ignore: avoid_print
      print('[HotkeyService] 配置文件读取失败，使用默认快捷键: $e');
    }

    // 返回默认快捷键
    return HotkeyConfig.defaultConfig;
  }

  /// 获取配置文件
  File _getConfigFile() {
    return File(SettingsConstants.settingsFilePath);
  }

  /// 释放资源
  Future<void> dispose() async {
    _isInitialized = false;
    _currentConfig = null;
    hotkeyMode = HotkeyMode.system;
    onHotkeyPressed = null;
  }
}
