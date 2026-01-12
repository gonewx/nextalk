/// 快捷键常量
/// Story 3-5: 全局快捷键配置 (重构版)
///
/// 提供配置键名到 Fcitx5 格式的映射
class HotkeyConstants {
  HotkeyConstants._();

  // ===== 默认快捷键 =====
  /// 默认主键名称 (Alt+Space)
  static const String defaultKey = 'space';

  /// 默认修饰键列表
  static const List<String> defaultModifiers = ['alt'];

  // ===== 键名到 Fcitx5 格式映射 =====
  /// 配置文件中的键名到 Fcitx5 按键名称的映射
  static const Map<String, String> keyToFcitx5 = {
    // 修饰键 (作为主键使用时)
    'alt': 'Alt_L',
    'altLeft': 'Alt_L',
    'altRight': 'Alt_R',
    'ctrl': 'Control_L',
    'ctrlLeft': 'Control_L',
    'ctrlRight': 'Control_R',
    'shift': 'Shift_L',
    'shiftLeft': 'Shift_L',
    'shiftRight': 'Shift_R',
    'meta': 'Super_L',
    'metaLeft': 'Super_L',
    'metaRight': 'Super_R',

    // 功能键 F1-F12
    'f1': 'F1',
    'f2': 'F2',
    'f3': 'F3',
    'f4': 'F4',
    'f5': 'F5',
    'f6': 'F6',
    'f7': 'F7',
    'f8': 'F8',
    'f9': 'F9',
    'f10': 'F10',
    'f11': 'F11',
    'f12': 'F12',

    // 常用键
    'space': 'space',
    'escape': 'Escape',
    'esc': 'Escape',
    'tab': 'Tab',
    'enter': 'Return',
    'backspace': 'BackSpace',
    'capsLock': 'Caps_Lock',

    // 方向键
    'arrowUp': 'Up',
    'arrowDown': 'Down',
    'arrowLeft': 'Left',
    'arrowRight': 'Right',
    'up': 'Up',
    'down': 'Down',
    'left': 'Left',
    'right': 'Right',

    // 编辑键
    'insert': 'Insert',
    'delete': 'Delete',
    'home': 'Home',
    'end': 'End',
    'pageUp': 'Page_Up',
    'pageDown': 'Page_Down',

    // 字母键 A-Z
    'a': 'a',
    'b': 'b',
    'c': 'c',
    'd': 'd',
    'e': 'e',
    'f': 'f',
    'g': 'g',
    'h': 'h',
    'i': 'i',
    'j': 'j',
    'k': 'k',
    'l': 'l',
    'm': 'm',
    'n': 'n',
    'o': 'o',
    'p': 'p',
    'q': 'q',
    'r': 'r',
    's': 's',
    't': 't',
    'u': 'u',
    'v': 'v',
    'w': 'w',
    'x': 'x',
    'y': 'y',
    'z': 'z',

    // 数字键 0-9 (主键盘)
    '0': '0',
    '1': '1',
    '2': '2',
    '3': '3',
    '4': '4',
    '5': '5',
    '6': '6',
    '7': '7',
    '8': '8',
    '9': '9',

    // 小键盘数字键
    'numpad0': 'KP_0',
    'numpad1': 'KP_1',
    'numpad2': 'KP_2',
    'numpad3': 'KP_3',
    'numpad4': 'KP_4',
    'numpad5': 'KP_5',
    'numpad6': 'KP_6',
    'numpad7': 'KP_7',
    'numpad8': 'KP_8',
    'numpad9': 'KP_9',
    'numpadEnter': 'KP_Enter',
    'numpadAdd': 'KP_Add',
    'numpadSubtract': 'KP_Subtract',
    'numpadMultiply': 'KP_Multiply',
    'numpadDivide': 'KP_Divide',
    'numpadDecimal': 'KP_Decimal',

    // 符号键
    'minus': 'minus',
    'equal': 'equal',
    'bracketLeft': 'bracketleft',
    'bracketRight': 'bracketright',
    'backslash': 'backslash',
    'semicolon': 'semicolon',
    'quote': 'apostrophe',
    'backquote': 'grave',
    'comma': 'comma',
    'period': 'period',
    'slash': 'slash',
  };

  // ===== 修饰键到 Fcitx5 格式映射 =====
  /// 修饰键名称到 Fcitx5 修饰键名称的映射
  static const Map<String, String> modifierToFcitx5 = {
    'ctrl': 'Control',
    'control': 'Control',
    'shift': 'Shift',
    'alt': 'Alt',
    'meta': 'Super',
  };
}
