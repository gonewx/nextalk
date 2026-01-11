import 'dart:io';

import 'package:flutter/foundation.dart';

/// 音频输入设备状态 (Story 3-9: AC5)
enum DeviceAvailability {
  /// 设备可用
  available,
  /// 设备不可用 (被占用或其他原因)
  busy,
}

/// 音频输入设备信息 (Story 3-9: AC4, AC5)
class AudioInputDevice {
  /// 设备索引 (用于显示)
  final int index;

  /// 设备名称 (PulseAudio source name)
  final String name;

  /// 设备描述 (用户友好的显示名称)
  final String description;

  /// 设备状态
  final DeviceAvailability status;

  AudioInputDevice({
    required this.index,
    required this.name,
    required this.description,
    required this.status,
  });

  @override
  String toString() =>
      'AudioInputDevice(index=$index, name="$name", desc="$description", status=$status)';
}

/// 音频设备服务 (Story 3-9: AC2, AC3, AC4, AC5, AC11, AC14)
///
/// 通过 PipeWire/PulseAudio (pactl) 枚举设备，与系统设置保持一致
class AudioDeviceService {
  AudioDeviceService._();

  static final AudioDeviceService instance = AudioDeviceService._();

  /// 缓存的设备列表
  List<AudioInputDevice>? _cachedDevices;

  /// 缓存时间戳
  DateTime? _cacheTime;

  /// 缓存有效期 (5 秒)
  static const Duration _cacheTtl = Duration(seconds: 5);

  /// 列出所有可用的音频输入设备
  ///
  /// 通过 pactl 枚举 PipeWire/PulseAudio 的输入源
  /// 只显示至少有一个端口可用的设备，与系统设置保持一致
  List<AudioInputDevice> listInputDevices({bool forceRefresh = false}) {
    // 检查缓存是否有效
    if (!forceRefresh &&
        _cachedDevices != null &&
        _cacheTime != null &&
        DateTime.now().difference(_cacheTime!) < _cacheTtl) {
      return _cachedDevices!;
    }

    final devices = <AudioInputDevice>[];

    try {
      // 使用 pactl list sources 获取详细信息（包括端口可用性）
      final result = Process.runSync('pactl', ['list', 'sources']);
      if (result.exitCode != 0) {
        debugPrint('AudioDeviceService: pactl 执行失败: ${result.stderr}');
        return devices;
      }

      final output = result.stdout as String;
      final sources = _parseSourcesWithPortAvailability(output);

      int index = 0;
      for (final source in sources) {
        // 过滤掉输出设备的 monitor (回环)
        if (source['name']!.contains('.monitor')) continue;

        // 只显示至少有一个端口可用的设备（与系统设置一致）
        if (source['hasAvailablePort'] != 'true') continue;

        devices.add(AudioInputDevice(
          index: index++,
          name: source['name']!,
          description: source['description'] ?? source['name']!,
          status: DeviceAvailability.available,
        ));
      }
    } catch (e) {
      debugPrint('AudioDeviceService: 枚举设备失败: $e');
    }

    // 更新缓存
    _cachedDevices = devices;
    _cacheTime = DateTime.now();

    return devices;
  }

  /// 解析 pactl list sources 输出，提取设备信息和端口可用性
  List<Map<String, String>> _parseSourcesWithPortAvailability(String output) {
    final sources = <Map<String, String>>[];
    final lines = output.split('\n');

    Map<String, String>? currentSource;
    bool inPortsSection = false;
    bool hasAvailablePort = false;

    for (final line in lines) {
      // 检测新的 Source 开始 (支持中英文)
      if (line.startsWith('Source #') || line.startsWith('信源 #')) {
        // 保存上一个 source
        if (currentSource != null) {
          currentSource['hasAvailablePort'] = hasAvailablePort.toString();
          sources.add(currentSource);
        }
        // 开始新的 source
        currentSource = {};
        inPortsSection = false;
        hasAvailablePort = false;
        continue;
      }

      if (currentSource == null) continue;

      final trimmed = line.trim();

      // 解析名称 (支持中英文)
      if (trimmed.startsWith('Name:') || trimmed.startsWith('名称：')) {
        final value = trimmed.contains(':')
            ? trimmed.split(':').sublist(1).join(':').trim()
            : trimmed.split('：').sublist(1).join('：').trim();
        currentSource['name'] = value;
      }
      // 解析描述 (支持中英文)
      else if (trimmed.startsWith('Description:') || trimmed.startsWith('描述：')) {
        final value = trimmed.contains(':')
            ? trimmed.split(':').sublist(1).join(':').trim()
            : trimmed.split('：').sublist(1).join('：').trim();
        currentSource['description'] = value;
      }
      // 检测端口部分开始 (支持中英文)
      else if (trimmed.startsWith('Ports:') || trimmed.startsWith('端口：')) {
        inPortsSection = true;
      }
      // 检测端口部分结束
      else if (inPortsSection &&
          (trimmed.startsWith('Active Port:') ||
              trimmed.startsWith('活动端口：') ||
              trimmed.startsWith('Formats:') ||
              trimmed.startsWith('格式：'))) {
        inPortsSection = false;
      }
      // 解析端口可用性
      else if (inPortsSection && trimmed.isNotEmpty) {
        // 端口行格式: "analog-input-mic: Microphone (type: Mic, priority: 8700, available)"
        // 或 "analog-input-mic: Microphone (type: Mic, priority: 8700, not available)"
        // 检查是否包含 "available" 但不包含 "not available"
        if (trimmed.contains('available') && !trimmed.contains('not available')) {
          hasAvailablePort = true;
        }
      }
    }

    // 保存最后一个 source
    if (currentSource != null) {
      currentSource['hasAvailablePort'] = hasAvailablePort.toString();
      sources.add(currentSource);
    }

    return sources;
  }

  /// 清除设备列表缓存
  void invalidateCache() {
    _cachedDevices = null;
    _cacheTime = null;
  }

  /// 按名称查找设备 (AC3)
  int findDeviceByName(String name, {List<AudioInputDevice>? cachedDevices}) {
    final devices = cachedDevices ?? listInputDevices();

    // 1. 精确匹配
    for (final device in devices) {
      if (device.name == name || device.description == name) {
        return device.index;
      }
    }

    // 2. 子串匹配
    for (final device in devices) {
      if (device.name.contains(name) ||
          name.contains(device.name) ||
          device.description.contains(name)) {
        return device.index;
      }
    }

    return -1;
  }

  /// 检查指定设备是否可用
  DeviceAvailability getDeviceStatus(int index) {
    final devices = listInputDevices();
    if (index < 0 || index >= devices.length) {
      return DeviceAvailability.busy;
    }
    return devices[index].status;
  }
}
