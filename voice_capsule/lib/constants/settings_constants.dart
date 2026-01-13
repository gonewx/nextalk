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

  /// 音频输入设备名称键名 (Story 3-9)
  static const String keyAudioInputDevice = '${keyPrefix}audio_input_device';

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

  /// 默认音频输入设备 (Story 3-9: "default" 表示使用系统默认设备)
  static const String defaultAudioInputDevice = 'default';

  // ===== 配置文件模板 =====

  /// 检测系统是否为中文环境
  static bool get isChineseLocale {
    final lang = Platform.environment['LANG'] ?? '';
    final lcAll = Platform.environment['LC_ALL'] ?? '';
    final lcMessages = Platform.environment['LC_MESSAGES'] ?? '';
    return lang.startsWith('zh') ||
        lcAll.startsWith('zh') ||
        lcMessages.startsWith('zh');
  }

  /// 获取当前语言环境的配置文件模板
  static String get defaultSettingsYaml =>
      isChineseLocale ? _settingsYamlZh : _settingsYamlEn;

  /// 中文配置文件模板
  static const String _settingsYamlZh = '''# Nextalk 设置文件
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

# 快捷键设置
# 请通过系统设置配置全局快捷键来触发 Nextalk：
#   GNOME: 设置 → 键盘 → 自定义快捷键 → 添加快捷键
#   KDE:   系统设置 → 快捷键 → 自定义快捷键
# 命令设置为: nextalk --toggle

# 音频设置
audio:
  # 输入设备名称
  # "default": 使用系统默认设备
  # 设备名称: 使用系统设置中显示的设备名 (如 "Built-in Audio Analog Stereo")
  #
  # 使用 nextalk audio 命令配置设备
  input_device: default
''';

  /// English settings template
  static const String _settingsYamlEn = '''# Nextalk Settings
# Restart the app after making changes

model:
  # ASR engine type: zipformer | sensevoice
  # zipformer: Streaming recognition, real-time, low latency (<200ms)
  # sensevoice: Offline recognition, VAD segmented, high accuracy, auto punctuation
  engine: sensevoice

  # Zipformer configuration (streaming engine)
  zipformer:
    # Model version: int8 | standard
    # int8: Quantized version, faster, less memory
    # standard: Standard version, higher accuracy
    type: int8

    # Custom model download URL (leave empty for default)
    custom_url: ""

  # SenseVoice configuration (offline engine)
  sensevoice:
    # Enable Inverse Text Normalization (ITN)
    # true: Auto-convert numbers, dates, etc. (e.g., "one two three" → "123")
    use_itn: true

    # Recognition language: auto | zh | en | ja | ko | yue
    # auto: Auto-detect language
    language: auto

    # Custom model download URL (leave empty for default)
    custom_url: ""

# Hotkey Settings
# Configure global hotkey via system settings to trigger Nextalk:
#   GNOME: Settings → Keyboard → Custom Shortcuts → Add Shortcut
#   KDE:   System Settings → Shortcuts → Custom Shortcuts
# Set command to: nextalk --toggle

# Audio Settings
audio:
  # Input device name
  # "default": Use system default device
  # Device name: Use the device name shown in system settings (e.g., "Built-in Audio Analog Stereo")
  #
  # Use 'nextalk audio' command to configure device
  input_device: default
''';
}
