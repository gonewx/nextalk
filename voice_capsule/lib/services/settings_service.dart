import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:yaml/yaml.dart';

import '../constants/settings_constants.dart';

/// 模型切换回调类型 (Zipformer 版本切换)
typedef ModelSwitchCallback = Future<void> Function(ModelType newType);

/// 引擎切换回调类型 (Story 2-7: Zipformer ↔ SenseVoice)
typedef EngineSwitchCallback = Future<void> Function(EngineType newType);

/// 设置服务
///
/// 管理应用配置，支持:
/// - SharedPreferences 存储运行时配置 (模型类型)
/// - YAML 文件存储高级配置 (自定义下载 URL)
class SettingsService {
  SettingsService._();

  static final SettingsService instance = SettingsService._();

  SharedPreferences? _prefs;
  bool _isInitialized = false;

  // 缓存的 YAML 配置
  Map<String, dynamic>? _yamlConfig;

  /// 模型切换回调 (由 main.dart 注入)
  ModelSwitchCallback? onModelSwitch;

  /// Story 2-7: 引擎切换回调 (由 main.dart 注入)
  EngineSwitchCallback? onEngineSwitch;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 初始化设置服务
  Future<void> initialize() async {
    if (_isInitialized) return;

    _prefs = await SharedPreferences.getInstance();

    // 确保配置目录和文件存在
    await _ensureConfigFile();

    // 加载 YAML 配置
    await _loadYamlConfig();

    _isInitialized = true;
  }

  /// 确保配置文件存在
  Future<void> _ensureConfigFile() async {
    final configDir = Directory(SettingsConstants.configDir);
    if (!configDir.existsSync()) {
      configDir.createSync(recursive: true);
    }

    final settingsFile = File(SettingsConstants.settingsFilePath);
    if (!settingsFile.existsSync()) {
      settingsFile.writeAsStringSync(SettingsConstants.defaultSettingsYaml);
      debugPrint('SettingsService: 创建默认配置文件');
    }
  }

  /// 加载 YAML 配置
  Future<void> _loadYamlConfig() async {
    try {
      final settingsFile = File(SettingsConstants.settingsFilePath);
      if (settingsFile.existsSync()) {
        final content = settingsFile.readAsStringSync();
        final yaml = loadYaml(content);
        if (yaml is YamlMap) {
          _yamlConfig = _yamlToMap(yaml);
        }
      }
    } catch (e) {
      debugPrint('SettingsService: 加载 YAML 配置失败: $e');
      _yamlConfig = null;
    }
  }

  /// 将 YamlMap 转换为普通 Map
  Map<String, dynamic> _yamlToMap(YamlMap yaml) {
    final result = <String, dynamic>{};
    for (final key in yaml.keys) {
      final value = yaml[key];
      if (value is YamlMap) {
        result[key.toString()] = _yamlToMap(value);
      } else if (value is YamlList) {
        result[key.toString()] = value.toList();
      } else {
        result[key.toString()] = value;
      }
    }
    return result;
  }

  /// 重新加载配置 (用于检测配置文件变更)
  Future<void> reload() async {
    await _loadYamlConfig();
  }

  // ===== 模型类型 =====

  /// 获取当前模型类型
  ModelType get modelType {
    if (_prefs == null) return SettingsConstants.defaultModelType;

    final typeStr = _prefs!.getString(SettingsConstants.keyModelType);
    if (typeStr == null) {
      // 尝试从 YAML 读取
      final yamlType = _yamlConfig?['model']?['type'] as String?;
      if (yamlType == 'standard') return ModelType.standard;
      return SettingsConstants.defaultModelType;
    }

    return typeStr == 'standard' ? ModelType.standard : ModelType.int8;
  }

  /// 设置模型类型
  Future<void> setModelType(ModelType type) async {
    if (_prefs == null) return;

    final typeStr = type == ModelType.standard ? 'standard' : 'int8';
    await _prefs!.setString(SettingsConstants.keyModelType, typeStr);

    // 同步更新 YAML 配置文件
    await _updateYamlModelType(typeStr);

    debugPrint('SettingsService: 模型类型已设置为 $typeStr');
  }

  /// 更新 YAML 文件中的模型类型
  Future<void> _updateYamlModelType(String typeStr) async {
    try {
      final settingsFile = File(SettingsConstants.settingsFilePath);
      if (!settingsFile.existsSync()) return;

      final content = settingsFile.readAsStringSync();
      // 匹配 "type: xxx" 行 (保留缩进和注释)
      final updatedContent = content.replaceFirstMapped(
        RegExp(r'^(\s*type:\s*)\S+', multiLine: true),
        (match) => '${match.group(1)}$typeStr',
      );

      if (content != updatedContent) {
        settingsFile.writeAsStringSync(updatedContent);
        // 更新内存缓存
        if (_yamlConfig != null && _yamlConfig!['model'] != null) {
          (_yamlConfig!['model'] as Map<String, dynamic>)['type'] = typeStr;
        }
        debugPrint('SettingsService: YAML 配置文件已更新');
      }
    } catch (e) {
      debugPrint('SettingsService: 更新 YAML 配置文件失败: $e');
    }
  }

  /// 切换模型类型并触发回调
  Future<bool> switchModelType(ModelType newType) async {
    if (modelType == newType) return true;

    try {
      // 1. 先保存配置 (确保回调读取到新值)
      await setModelType(newType);

      // 2. 调用切换回调
      if (onModelSwitch != null) {
        await onModelSwitch!(newType);
      }

      debugPrint('SettingsService: 模型切换成功: $newType');
      return true;
    } catch (e) {
      debugPrint('SettingsService: 模型切换失败: $e');
      return false;
    }
  }

  // ===== Story 2-7: 引擎类型 =====

  /// 获取当前引擎类型
  EngineType get engineType {
    if (_prefs == null) return SettingsConstants.defaultEngineType;

    final typeStr = _prefs!.getString(SettingsConstants.keyEngineType);
    if (typeStr == null) {
      // 尝试从 YAML 读取
      final yamlEngine = _yamlConfig?['model']?['engine'] as String?;
      if (yamlEngine != null) {
        final parsed = EngineType.values.where((e) => e.name == yamlEngine);
        if (parsed.isNotEmpty) return parsed.first;
      }
      return SettingsConstants.defaultEngineType;
    }

    // 解析 SharedPreferences 中的值
    final parsed = EngineType.values.where((e) => e.name == typeStr);
    return parsed.isNotEmpty ? parsed.first : SettingsConstants.defaultEngineType;
  }

  /// 设置引擎类型
  Future<void> setEngineType(EngineType type) async {
    if (_prefs == null) return;

    final typeStr = type.name;
    await _prefs!.setString(SettingsConstants.keyEngineType, typeStr);

    // 同步更新 YAML 配置文件
    await _updateYamlEngineType(typeStr);

    debugPrint('SettingsService: 引擎类型已设置为 $typeStr');
  }

  /// 更新 YAML 文件中的引擎类型
  Future<void> _updateYamlEngineType(String typeStr) async {
    try {
      final settingsFile = File(SettingsConstants.settingsFilePath);
      if (!settingsFile.existsSync()) return;

      final content = settingsFile.readAsStringSync();
      // 匹配 "engine: xxx" 行 (保留缩进和注释)
      final updatedContent = content.replaceFirstMapped(
        RegExp(r'^(\s*engine:\s*)\S+', multiLine: true),
        (match) => '${match.group(1)}$typeStr',
      );

      if (content != updatedContent) {
        settingsFile.writeAsStringSync(updatedContent);
        // 更新内存缓存
        if (_yamlConfig != null && _yamlConfig!['model'] != null) {
          (_yamlConfig!['model'] as Map<String, dynamic>)['engine'] = typeStr;
        }
        debugPrint('SettingsService: YAML 引擎类型已更新');
      }
    } catch (e) {
      debugPrint('SettingsService: 更新 YAML 引擎类型失败: $e');
    }
  }

  /// 切换引擎类型并触发回调 (AC5: 需销毁并重建 Pipeline)
  Future<bool> switchEngineType(EngineType newType) async {
    if (engineType == newType) return true;

    try {
      // 1. 先保存配置 (确保回调读取到新值)
      await setEngineType(newType);

      // 2. 调用切换回调 (由 main.dart 注入，负责销毁旧 Pipeline 并创建新 Pipeline)
      if (onEngineSwitch != null) {
        await onEngineSwitch!(newType);
      }

      debugPrint('SettingsService: 引擎切换成功: $newType');
      return true;
    } catch (e) {
      debugPrint('SettingsService: 引擎切换失败: $e');
      return false;
    }
  }

  // ===== SenseVoice 配置 =====

  /// 获取 SenseVoice use_itn 配置
  bool get senseVoiceUseItn {
    final value = _yamlConfig?['model']?['sensevoice']?['use_itn'];
    if (value is bool) return value;
    return SettingsConstants.defaultSenseVoiceUseItn;
  }

  /// 获取 SenseVoice language 配置
  String get senseVoiceLanguage {
    final value = _yamlConfig?['model']?['sensevoice']?['language'] as String?;
    if (value != null && value.isNotEmpty) return value;
    return SettingsConstants.defaultSenseVoiceLanguage;
  }

  // ===== 自定义下载 URL =====

  /// 获取 Zipformer 自定义模型下载 URL (从 YAML 读取)
  String? get zipformerCustomUrl {
    final url = _yamlConfig?['model']?['zipformer']?['custom_url'] as String?;
    if (url == null || url.isEmpty) return null;
    return url;
  }

  /// 获取 SenseVoice 自定义模型下载 URL (从 YAML 读取)
  String? get senseVoiceCustomUrl {
    final url = _yamlConfig?['model']?['sensevoice']?['custom_url'] as String?;
    if (url == null || url.isEmpty) return null;
    return url;
  }

  /// 获取当前引擎的自定义模型下载 URL
  String? get customModelUrl {
    if (engineType == EngineType.sensevoice) {
      return senseVoiceCustomUrl;
    }
    return zipformerCustomUrl;
  }

  /// [已废弃] 旧版自定义下载 URL，为了兼容保留
  /// 使用 [zipformerCustomUrl] 或 [senseVoiceCustomUrl] 替代
  @Deprecated('Use zipformerCustomUrl or senseVoiceCustomUrl instead')
  String? get legacyCustomModelUrl {
    final url = _yamlConfig?['model']?['custom_url'] as String?;
    if (url == null || url.isEmpty) return null;
    return url;
  }

  // ===== 配置目录操作 =====

  /// 使用 xdg-open 打开配置目录
  Future<void> openConfigDirectory() async {
    final configDir = Directory(SettingsConstants.configDir);
    if (!configDir.existsSync()) {
      configDir.createSync(recursive: true);
    }

    // 确保配置文件存在
    await _ensureConfigFile();

    await Process.run('xdg-open', [SettingsConstants.configDir]);
    debugPrint('SettingsService: 打开配置目录: ${SettingsConstants.configDir}');
  }

  /// 获取配置文件路径 (用于 UI 显示)
  String get configFilePath => SettingsConstants.settingsFilePath;
}
