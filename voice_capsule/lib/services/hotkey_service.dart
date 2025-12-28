import 'dart:io';

import 'package:yaml/yaml.dart';

import '../constants/hotkey_constants.dart';
import '../constants/settings_constants.dart';

/// 快捷键按下回调类型
typedef HotkeyPressedCallback = Future<void> Function();

/// 快捷键配置数据
class HotkeyConfig {
  final String key;
  final List<String> modifiers;

  const HotkeyConfig({
    required this.key,
    required this.modifiers,
  });

  /// 默认快捷键配置 (Ctrl+Alt+V)
  static const HotkeyConfig defaultConfig = HotkeyConfig(
    key: 'v',
    modifiers: ['ctrl', 'alt'],
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
    onHotkeyPressed = null;
  }
}
