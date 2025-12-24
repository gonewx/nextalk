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

    // 功能键 F1-F12
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

    // 常用键
    'space': PhysicalKeyboardKey.space,
    'escape': PhysicalKeyboardKey.escape,
    'esc': PhysicalKeyboardKey.escape,
    'tab': PhysicalKeyboardKey.tab,
    'enter': PhysicalKeyboardKey.enter,
    'backspace': PhysicalKeyboardKey.backspace,
    'capsLock': PhysicalKeyboardKey.capsLock,

    // 方向键
    'arrowUp': PhysicalKeyboardKey.arrowUp,
    'arrowDown': PhysicalKeyboardKey.arrowDown,
    'arrowLeft': PhysicalKeyboardKey.arrowLeft,
    'arrowRight': PhysicalKeyboardKey.arrowRight,
    'up': PhysicalKeyboardKey.arrowUp,
    'down': PhysicalKeyboardKey.arrowDown,
    'left': PhysicalKeyboardKey.arrowLeft,
    'right': PhysicalKeyboardKey.arrowRight,

    // 编辑键
    'insert': PhysicalKeyboardKey.insert,
    'delete': PhysicalKeyboardKey.delete,
    'home': PhysicalKeyboardKey.home,
    'end': PhysicalKeyboardKey.end,
    'pageUp': PhysicalKeyboardKey.pageUp,
    'pageDown': PhysicalKeyboardKey.pageDown,

    // 字母键 A-Z
    'a': PhysicalKeyboardKey.keyA,
    'b': PhysicalKeyboardKey.keyB,
    'c': PhysicalKeyboardKey.keyC,
    'd': PhysicalKeyboardKey.keyD,
    'e': PhysicalKeyboardKey.keyE,
    'f': PhysicalKeyboardKey.keyF,
    'g': PhysicalKeyboardKey.keyG,
    'h': PhysicalKeyboardKey.keyH,
    'i': PhysicalKeyboardKey.keyI,
    'j': PhysicalKeyboardKey.keyJ,
    'k': PhysicalKeyboardKey.keyK,
    'l': PhysicalKeyboardKey.keyL,
    'm': PhysicalKeyboardKey.keyM,
    'n': PhysicalKeyboardKey.keyN,
    'o': PhysicalKeyboardKey.keyO,
    'p': PhysicalKeyboardKey.keyP,
    'q': PhysicalKeyboardKey.keyQ,
    'r': PhysicalKeyboardKey.keyR,
    's': PhysicalKeyboardKey.keyS,
    't': PhysicalKeyboardKey.keyT,
    'u': PhysicalKeyboardKey.keyU,
    'v': PhysicalKeyboardKey.keyV,
    'w': PhysicalKeyboardKey.keyW,
    'x': PhysicalKeyboardKey.keyX,
    'y': PhysicalKeyboardKey.keyY,
    'z': PhysicalKeyboardKey.keyZ,

    // 数字键 0-9 (主键盘)
    '0': PhysicalKeyboardKey.digit0,
    '1': PhysicalKeyboardKey.digit1,
    '2': PhysicalKeyboardKey.digit2,
    '3': PhysicalKeyboardKey.digit3,
    '4': PhysicalKeyboardKey.digit4,
    '5': PhysicalKeyboardKey.digit5,
    '6': PhysicalKeyboardKey.digit6,
    '7': PhysicalKeyboardKey.digit7,
    '8': PhysicalKeyboardKey.digit8,
    '9': PhysicalKeyboardKey.digit9,

    // 小键盘数字键
    'numpad0': PhysicalKeyboardKey.numpad0,
    'numpad1': PhysicalKeyboardKey.numpad1,
    'numpad2': PhysicalKeyboardKey.numpad2,
    'numpad3': PhysicalKeyboardKey.numpad3,
    'numpad4': PhysicalKeyboardKey.numpad4,
    'numpad5': PhysicalKeyboardKey.numpad5,
    'numpad6': PhysicalKeyboardKey.numpad6,
    'numpad7': PhysicalKeyboardKey.numpad7,
    'numpad8': PhysicalKeyboardKey.numpad8,
    'numpad9': PhysicalKeyboardKey.numpad9,
    'numpadEnter': PhysicalKeyboardKey.numpadEnter,
    'numpadAdd': PhysicalKeyboardKey.numpadAdd,
    'numpadSubtract': PhysicalKeyboardKey.numpadSubtract,
    'numpadMultiply': PhysicalKeyboardKey.numpadMultiply,
    'numpadDivide': PhysicalKeyboardKey.numpadDivide,
    'numpadDecimal': PhysicalKeyboardKey.numpadDecimal,

    // 符号键
    'minus': PhysicalKeyboardKey.minus,
    'equal': PhysicalKeyboardKey.equal,
    'bracketLeft': PhysicalKeyboardKey.bracketLeft,
    'bracketRight': PhysicalKeyboardKey.bracketRight,
    'backslash': PhysicalKeyboardKey.backslash,
    'semicolon': PhysicalKeyboardKey.semicolon,
    'quote': PhysicalKeyboardKey.quote,
    'backquote': PhysicalKeyboardKey.backquote,
    'comma': PhysicalKeyboardKey.comma,
    'period': PhysicalKeyboardKey.period,
    'slash': PhysicalKeyboardKey.slash,
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
