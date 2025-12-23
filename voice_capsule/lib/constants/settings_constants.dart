import 'dart:io';

/// 模型类型枚举
enum ModelType {
  /// int8 量化版本 (更快，内存占用更小)
  int8,

  /// 标准版本 (更准确)
  standard,
}

/// 设置服务常量
class SettingsConstants {
  SettingsConstants._();

  // ===== SharedPreferences 键名 =====

  /// 键名前缀
  static const String keyPrefix = 'nextalk_';

  /// 模型类型键名
  static const String keyModelType = '${keyPrefix}model_type';

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

  /// 默认模型类型
  static const ModelType defaultModelType = ModelType.standard;

  // ===== 配置文件模板 =====

  /// 默认配置文件内容
  static const String defaultSettingsYaml = '''# Nextalk 设置文件
# 修改后重启应用或通过托盘菜单切换模型生效

model:
  # 自定义模型下载地址 (留空使用默认地址)
  # 默认: https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2
  custom_url: ""

  # 模型版本: int8 | standard
  # int8: 量化版本，速度快，内存占用小
  # standard: 标准版本，精度高
  type: int8
''';
}
