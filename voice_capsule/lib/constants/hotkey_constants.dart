import 'package:flutter/services.dart';
import 'package:hotkey_manager/hotkey_manager.dart';

/// 快捷键常量
/// Story 3-5: 全局快捷键监听
class HotkeyConstants {
  HotkeyConstants._();

  // ===== 默认快捷键 =====
  /// 默认主键: Right Alt (使用 PhysicalKeyboardKey)
  static const PhysicalKeyboardKey defaultKey = PhysicalKeyboardKey.altRight;

  /// 默认修饰键: 无
  static const List<HotKeyModifier> defaultModifiers = [];

  // ===== 备用快捷键 (当默认快捷键被占用时使用) =====
  /// 备用主键: Space
  static const PhysicalKeyboardKey fallbackKey = PhysicalKeyboardKey.space;

  /// 备用修饰键: Ctrl+Shift
  static const List<HotKeyModifier> fallbackModifiers = [
    HotKeyModifier.control,
    HotKeyModifier.shift,
  ];

  // ===== 配置文件 =====
  /// 配置文件名
  static const String configFileName = 'config.yaml';

  /// 配置目录名 (在 ~/.config/ 下)
  static const String configDirName = 'nextalk';

  // ===== 键位映射 =====
  /// 支持的键位名称到 PhysicalKeyboardKey 映射
  /// 用于配置文件解析
  static final Map<String, PhysicalKeyboardKey> keyMap = {
    // 修饰键
    'alt': PhysicalKeyboardKey.altLeft,
    'altLeft': PhysicalKeyboardKey.altLeft,
    'altRight': PhysicalKeyboardKey.altRight,
    'ctrl': PhysicalKeyboardKey.controlLeft,
    'ctrlLeft': PhysicalKeyboardKey.controlLeft,
    'ctrlRight': PhysicalKeyboardKey.controlRight,
    'shift': PhysicalKeyboardKey.shiftLeft,
    'shiftLeft': PhysicalKeyboardKey.shiftLeft,
    'shiftRight': PhysicalKeyboardKey.shiftRight,
    'meta': PhysicalKeyboardKey.metaLeft,
    'metaLeft': PhysicalKeyboardKey.metaLeft,
    'metaRight': PhysicalKeyboardKey.metaRight,
    // 功能键
    'space': PhysicalKeyboardKey.space,
    'f1': PhysicalKeyboardKey.f1,
    'f2': PhysicalKeyboardKey.f2,
    'f3': PhysicalKeyboardKey.f3,
    'f4': PhysicalKeyboardKey.f4,
    'f5': PhysicalKeyboardKey.f5,
    'f6': PhysicalKeyboardKey.f6,
    'f7': PhysicalKeyboardKey.f7,
    'f8': PhysicalKeyboardKey.f8,
    'f9': PhysicalKeyboardKey.f9,
    'f10': PhysicalKeyboardKey.f10,
    'f11': PhysicalKeyboardKey.f11,
    'f12': PhysicalKeyboardKey.f12,
  };

  /// 修饰键名称到 HotKeyModifier 映射
  static const Map<String, HotKeyModifier> modifierMap = {
    'ctrl': HotKeyModifier.control,
    'control': HotKeyModifier.control,
    'shift': HotKeyModifier.shift,
    'alt': HotKeyModifier.alt,
    'meta': HotKeyModifier.meta,
  };
}
