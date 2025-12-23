import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:hotkey_manager/hotkey_manager.dart';
import 'package:yaml/yaml.dart';

import '../constants/hotkey_constants.dart';

/// 快捷键按下回调类型
typedef HotkeyPressedCallback = Future<void> Function();

/// 全局快捷键服务 - Story 3-5
///
/// 职责:
/// - 加载配置文件或使用默认快捷键
/// - 注册/注销全局快捷键
/// - 处理按键事件回调
/// - 错误处理 (快捷键冲突时使用备用快捷键)
class HotkeyService {
  HotkeyService._();
  static final HotkeyService instance = HotkeyService._();

  HotKey? _registeredHotkey;
  bool _isInitialized = false;
  bool _registrationFailed = false;

  /// 重置服务状态 (仅用于测试)
  ///
  /// 注意: 不会注销已注册的快捷键，仅重置内部状态。
  /// 生产代码中请使用 [dispose] 方法。
  @visibleForTesting
  void resetForTesting() {
    _isInitialized = false;
    _registrationFailed = false;
    _registeredHotkey = null;
    onHotkeyPressed = null;
  }

  /// 快捷键按下回调 (由 HotkeyController 注入)
  HotkeyPressedCallback? onHotkeyPressed;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 注册是否失败 (AC7: 快捷键被占用)
  bool get registrationFailed => _registrationFailed;

  /// 当前注册的快捷键
  HotKey? get currentHotkey => _registeredHotkey;

  /// 初始化并注册快捷键 (AC8: 应用启动时调用)
  ///
  /// 流程:
  /// 1. 加载配置文件或使用默认快捷键
  /// 2. 尝试注册主快捷键
  /// 3. 如果主快捷键被占用，尝试备用快捷键 (AC7)
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      // 1. 加载配置 (配置文件或默认值)
      final hotkey = await _loadHotkeyConfig();

      // 2. 注册全局快捷键
      await hotKeyManager.register(
        hotkey,
        keyDownHandler: (hotKey) async {
          if (onHotkeyPressed != null) {
            await onHotkeyPressed!();
          }
        },
      );

      _registeredHotkey = hotkey;
      _isInitialized = true;
      _registrationFailed = false;

      // ignore: avoid_print
      print('[HotkeyService] ✅ 快捷键注册成功: ${_hotkeyToString(hotkey)}');
    } catch (e) {
      _registrationFailed = true;
      // AC7: 快捷键被占用时输出警告，不崩溃
      // ignore: avoid_print
      print('[HotkeyService] ⚠️ 快捷键注册失败 (可能被其他应用占用): $e');
      // 尝试使用备用快捷键 (Ctrl+Shift+Space)
      await _tryFallbackHotkey();
    }
  }

  /// 加载快捷键配置 (AC6: 支持配置文件自定义)
  Future<HotKey> _loadHotkeyConfig() async {
    try {
      final configFile = _getConfigFile();
      if (configFile != null && await configFile.exists()) {
        final content = await configFile.readAsString();
        final yaml = loadYaml(content);

        if (yaml != null && yaml['hotkey'] != null) {
          final hotkeyConfig = yaml['hotkey'];
          final keyName = hotkeyConfig['key'] as String?;
          final modifierNames =
              (hotkeyConfig['modifiers'] as List?)?.cast<String>() ?? [];

          if (keyName != null && HotkeyConstants.keyMap.containsKey(keyName)) {
            final key = HotkeyConstants.keyMap[keyName]!;
            final modifiers = modifierNames
                .where((m) => HotkeyConstants.modifierMap.containsKey(m))
                .map((m) => HotkeyConstants.modifierMap[m]!)
                .toList();

            // ignore: avoid_print
            print('[HotkeyService] 从配置文件加载快捷键: $keyName + $modifierNames');

            return HotKey(
              key: key,
              modifiers: modifiers.isEmpty ? null : modifiers,
            );
          }
        }
      }
    } catch (e) {
      // ignore: avoid_print
      print('[HotkeyService] 配置文件读取失败，使用默认快捷键: $e');
    }

    // 返回默认快捷键
    return HotKey(
      key: HotkeyConstants.defaultKey,
      modifiers: HotkeyConstants.defaultModifiers.isEmpty
          ? null
          : HotkeyConstants.defaultModifiers,
    );
  }

  /// 获取配置文件
  File? _getConfigFile() {
    final homeDir = Platform.environment['HOME'];
    if (homeDir == null) return null;

    final configPath = '$homeDir/.config/${HotkeyConstants.configDirName}/'
        '${HotkeyConstants.configFileName}';
    return File(configPath);
  }

  /// 尝试备用快捷键 (Ctrl+Shift+Space)
  ///
  /// 当主快捷键被其他应用占用时调用
  Future<void> _tryFallbackHotkey() async {
    try {
      final fallbackHotkey = HotKey(
        key: HotkeyConstants.fallbackKey,
        modifiers: HotkeyConstants.fallbackModifiers,
      );

      await hotKeyManager.register(
        fallbackHotkey,
        keyDownHandler: (hotKey) async {
          if (onHotkeyPressed != null) {
            await onHotkeyPressed!();
          }
        },
      );

      _registeredHotkey = fallbackHotkey;
      _isInitialized = true;
      _registrationFailed = false;

      // ignore: avoid_print
      print('[HotkeyService] ✅ 备用快捷键注册成功: ${_hotkeyToString(fallbackHotkey)}');
    } catch (e) {
      // ignore: avoid_print
      print('[HotkeyService] ❌ 备用快捷键也注册失败: $e');
      _isInitialized = true; // 标记已初始化，但功能降级
    }
  }

  /// 注销快捷键 (AC9: 退出时调用)
  Future<void> unregister() async {
    if (_registeredHotkey != null) {
      try {
        await hotKeyManager.unregister(_registeredHotkey!);
        // ignore: avoid_print
        print('[HotkeyService] 快捷键已注销');
      } catch (e) {
        // ignore: avoid_print
        print('[HotkeyService] 注销失败: $e');
      }
      _registeredHotkey = null;
    }
  }

  /// 释放资源
  Future<void> dispose() async {
    await unregister();
    _isInitialized = false;
  }

  /// 快捷键转字符串 (用于日志)
  String _hotkeyToString(HotKey hotkey) {
    final parts = <String>[];
    for (final modifier in hotkey.modifiers ?? []) {
      parts.add(modifier.name);
    }

    // 获取键名
    final key = hotkey.key;
    if (key is PhysicalKeyboardKey) {
      parts.add(key.debugName ?? 'Unknown');
    } else if (key is LogicalKeyboardKey) {
      parts.add(key.debugName ?? 'Unknown');
    } else {
      parts.add('Unknown');
    }

    return parts.join('+');
  }
}
