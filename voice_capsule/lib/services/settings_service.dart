import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:yaml/yaml.dart';

import '../constants/settings_constants.dart';

/// 模型切换回调类型
typedef ModelSwitchCallback = Future<void> Function(ModelType newType);

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

    debugPrint('SettingsService: 模型类型已设置为 $typeStr');
  }

  /// 切换模型类型并触发回调
  Future<bool> switchModelType(ModelType newType) async {
    if (modelType == newType) return true;

    try {
      // 1. 调用切换回调
      if (onModelSwitch != null) {
        await onModelSwitch!(newType);
      }

      // 2. 保存配置
      await setModelType(newType);

      debugPrint('SettingsService: 模型切换成功: $newType');
      return true;
    } catch (e) {
      debugPrint('SettingsService: 模型切换失败: $e');
      return false;
    }
  }

  // ===== 自定义下载 URL =====

  /// 获取自定义模型下载 URL (从 YAML 读取)
  String? get customModelUrl {
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
