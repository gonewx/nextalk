import 'dart:io';
import 'dart:typed_data';

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

  /// 默认快捷键配置 (Right Alt)
  static const HotkeyConfig defaultConfig = HotkeyConfig(
    key: 'altRight',
    modifiers: [],
  );

  /// 转换为 Fcitx5 格式
  /// 格式: "Modifier+Modifier+Key" 或 "Key"
  String toFcitx5Format() {
    final parts = <String>[];

    // 添加修饰键
    for (final modifier in modifiers) {
      final fcitx5Modifier = HotkeyConstants.modifierToFcitx5[modifier];
      if (fcitx5Modifier != null) {
        parts.add(fcitx5Modifier);
      }
    }

    // 添加主键
    final fcitx5Key = HotkeyConstants.keyToFcitx5[key];
    if (fcitx5Key != null) {
      parts.add(fcitx5Key);
    } else {
      parts.add(key); // 回退到原始键名
    }

    return parts.join('+');
  }

  @override
  String toString() => '$key + $modifiers';
}

/// 快捷键配置服务 - Story 3-5 (重构版)
///
/// 职责:
/// - 加载配置文件或使用默认快捷键
/// - 同步配置到 Fcitx5 插件
///
/// 注意: 实际的快捷键监听由 Fcitx5 插件处理，
/// Flutter 端通过 CommandServer 接收命令
class HotkeyService {
  HotkeyService._();
  static final HotkeyService instance = HotkeyService._();

  HotkeyConfig? _currentConfig;
  bool _isInitialized = false;

  /// Fcitx5 配置 Socket 路径
  String get _fcitxConfigSocketPath {
    final runtimeDir = Platform.environment['XDG_RUNTIME_DIR'];
    if (runtimeDir != null && runtimeDir.isNotEmpty) {
      return '$runtimeDir/nextalk-fcitx5-cfg.sock';
    }
    return '/tmp/nextalk-fcitx5-cfg.sock';
  }

  /// 快捷键按下回调 (由 HotkeyController 注入)
  /// 保留此字段以保持向后兼容，但实际触发由 CommandServer 处理
  HotkeyPressedCallback? onHotkeyPressed;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 当前快捷键配置
  HotkeyConfig? get currentConfig => _currentConfig;

  /// 初始化并同步配置到 Fcitx5
  ///
  /// 流程:
  /// 1. 加载配置文件或使用默认快捷键
  /// 2. 同步配置到 Fcitx5 插件
  Future<void> initialize() async {
    if (_isInitialized) return;

    // 1. 加载配置
    _currentConfig = await _loadHotkeyConfig();

    // ignore: avoid_print
    print('[HotkeyService] ✅ 配置加载完成: ${_currentConfig!.toFcitx5Format()}');

    // 2. 同步配置到 Fcitx5 插件
    await syncToFcitx5(_currentConfig!);

    _isInitialized = true;
  }

  /// 加载快捷键配置 (AC6: 支持配置文件自定义)
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

  /// 获取配置文件 (统一使用 settings.yaml)
  File _getConfigFile() {
    return File(SettingsConstants.settingsFilePath);
  }

  /// 释放资源
  Future<void> dispose() async {
    _isInitialized = false;
    _currentConfig = null;
    onHotkeyPressed = null;
  }

  /// 同步快捷键配置到 Fcitx5 插件
  ///
  /// 通过 Unix Socket 发送配置命令到 Fcitx5 插件
  /// 格式: "config:hotkey:<key_spec>"
  Future<void> syncToFcitx5(HotkeyConfig config) async {
    try {
      final keySpec = config.toFcitx5Format();
      final command = 'config:hotkey:$keySpec';

      // ignore: avoid_print
      print('[HotkeyService] 同步配置到 Fcitx5: $command');

      await _sendConfigToFcitx5(command);

      // ignore: avoid_print
      print('[HotkeyService] ✅ 配置已同步到 Fcitx5');
    } catch (e) {
      // ignore: avoid_print
      print('[HotkeyService] ⚠️ 同步配置到 Fcitx5 失败: $e');
      // 不抛出异常，Fcitx5 可能未运行
    }
  }

  /// 发送配置命令到 Fcitx5 插件
  Future<void> _sendConfigToFcitx5(String command) async {
    Socket? socket;
    try {
      final address = InternetAddress(_fcitxConfigSocketPath, type: InternetAddressType.unix);
      socket = await Socket.connect(address, 0, timeout: const Duration(seconds: 2));

      // 协议: 4字节长度 (小端) + UTF-8 命令
      final commandBytes = Uint8List.fromList(command.codeUnits);
      final lenBytes = ByteData(4);
      lenBytes.setUint32(0, commandBytes.length, Endian.little);

      socket.add(lenBytes.buffer.asUint8List());
      socket.add(commandBytes);
      await socket.flush();

      // 等待确认 (可选，超时 1 秒)
      await socket.first.timeout(const Duration(seconds: 1), onTimeout: () => Uint8List(0));
    } finally {
      await socket?.close();
    }
  }
}
