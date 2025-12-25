import 'dart:io';

/// 模型类型枚举 (版本选择)
enum ModelType {
  /// int8 量化版本 (更快，内存占用更小)
  int8,

  /// 标准版本 (更准确)
  standard,
}

/// ASR 引擎类型枚举 (Story 2-7)
enum EngineType {
  /// Zipformer 流式引擎 (边听边识别，低延迟)
  zipformer,

  /// SenseVoice 离线引擎 (VAD 分段后识别，高精度)
  sensevoice,
}

/// 设置服务常量
class SettingsConstants {
  SettingsConstants._();

  // ===== SharedPreferences 键名 =====

  /// 键名前缀
  static const String keyPrefix = 'nextalk_';

  /// 模型类型键名 (Zipformer 版本: int8 | standard)
  static const String keyModelType = '${keyPrefix}model_type';

  /// 引擎类型键名 (Story 2-7: zipformer | sensevoice)
  static const String keyEngineType = '${keyPrefix}engine_type';

  // ===== 配置文件路径 =====

  /// XDG 配置目录
  static String get configHome {
    final xdgConfig = Platform.environment['XDG_CONFIG_HOME'];
    if (xdgConfig != null && xdgConfig.isNotEmpty) return xdgConfig;
    final home = Platform.environment['HOME']!;
    return '$home/.config';
  }

  /// Nextalk 配置目录
  static String get configDir => '$configHome/nextalk';

  /// 设置文件路径
  static String get settingsFilePath => '$configDir/settings.yaml';

  // ===== 默认值 =====

  /// 默认模型类型 (Zipformer 版本)
  static const ModelType defaultModelType = ModelType.standard;

  /// 默认引擎类型 (Story 2-7 AC5: 默认使用 SenseVoice 引擎)
  static const EngineType defaultEngineType = EngineType.sensevoice;

  /// SenseVoice 默认配置: 是否启用逆文本正则化 (ITN)
  static const bool defaultSenseVoiceUseItn = true;

  /// SenseVoice 默认配置: 语言 (auto 自动检测)
  static const String defaultSenseVoiceLanguage = 'auto';

  // ===== 配置文件模板 =====

  /// 默认配置文件内容 (Story 2-7 AC5: 支持多引擎配置)
  static const String defaultSettingsYaml = '''# Nextalk 设置文件
# 修改后重启应用生效

model:
  # ASR 引擎类型: zipformer | sensevoice
  # zipformer: 流式识别，边听边识别，低延迟 (<200ms)
  # sensevoice: 离线识别，VAD 分段后识别，高精度，自动标点
  engine: sensevoice

  # Zipformer 配置 (流式引擎)
  zipformer:
    # 模型版本: int8 | standard
    # int8: 量化版本，速度快，内存占用小
    # standard: 标准版本，精度高
    type: int8

    # 自定义模型下载地址 (留空使用默认地址)
    custom_url: ""

  # SenseVoice 配置 (离线引擎)
  sensevoice:
    # 是否启用逆文本正则化 (ITN)
    # true: 自动转换数字、日期等格式 (如 "一百二十三" → "123")
    use_itn: true

    # 识别语言: auto | zh | en | ja | ko | yue
    # auto: 自动检测语言
    language: auto

    # 自定义模型下载地址 (留空使用默认地址)
    custom_url: ""

hotkey:
  # 触发语音输入的快捷键
  #
  # 推荐配置:
  #   key: altRight, modifiers: []     - 单独按右 Alt 键 (默认)
  #   key: space, modifiers: [ctrl]    - Ctrl+Space
  #   key: f12, modifiers: []          - 单独按 F12
  #
  # 支持的主键:
  #   修饰键: altRight, altLeft (仅作为单独按键使用)
  #   功能键: f1-f12, space, escape/esc, tab, enter, backspace, capsLock
  #   方向键: up/arrowUp, down/arrowDown, left/arrowLeft, right/arrowRight
  #   编辑键: insert, delete, home, end, pageUp, pageDown
  #   字母键: a-z
  #   数字键: 0-9, numpad0-numpad9
  #   小键盘: numpadEnter, numpadAdd, numpadSubtract, numpadMultiply, numpadDivide
  #   符号键: minus, equal, bracketLeft, bracketRight, backslash, semicolon, quote, backquote, comma, period, slash
  key: altRight

  # 修饰键 (可选): ctrl, shift, alt, meta
  # 示例: modifiers: [ctrl, shift]
  modifiers: []
''';
}
