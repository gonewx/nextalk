import 'dart:ffi';
import 'package:ffi/ffi.dart';
import 'package:flutter/foundation.dart';
import '../ffi/portaudio_ffi.dart';

/// 音频输入设备状态 (Story 3-9: AC5)
enum DeviceAvailability {
  /// 设备可用
  available,
  /// 设备不可用 (被占用或其他原因)
  busy,
}

/// 音频输入设备信息 (Story 3-9: AC4, AC5)
class AudioInputDevice {
  /// 设备索引 (用于显示，从 0 开始)
  final int index;

  /// PortAudio 设备索引 (用于打开设备)
  final int paDeviceIndex;

  /// 设备名称
  final String name;

  /// 设备描述 (用户友好的显示名称)
  final String description;

  /// 设备状态
  final DeviceAvailability status;

  AudioInputDevice({
    required this.index,
    required this.paDeviceIndex,
    required this.name,
    required this.description,
    required this.status,
  });

  @override
  String toString() =>
      'AudioInputDevice(index=$index, paIndex=$paDeviceIndex, name="$name", status=$status)';
}

/// 音频设备服务 (Story 3-9: AC2, AC3, AC4, AC5, AC11, AC14)
///
/// 通过 PortAudio API 枚举设备，无需外部依赖
class AudioDeviceService {
  AudioDeviceService._();

  static final AudioDeviceService instance = AudioDeviceService._();

  /// PortAudio 绑定 (延迟初始化)
  PortAudioBindings? _bindings;

  /// 缓存的设备列表
  List<AudioInputDevice>? _cachedDevices;

  /// 缓存时间戳
  DateTime? _cacheTime;

  /// 缓存有效期 (5 秒)
  static const Duration _cacheTtl = Duration(seconds: 5);

  /// 获取 PortAudio 绑定
  PortAudioBindings get _pa {
    _bindings ??= PortAudioBindings();
    return _bindings!;
  }

  /// 列出所有可用的音频输入设备
  ///
  /// 通过 PortAudio API 枚举设备，只返回有输入通道的设备
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
      // 初始化 PortAudio
      final initResult = _pa.initialize();
      if (initResult != paNoError) {
        debugPrint('AudioDeviceService: PortAudio 初始化失败: ${_pa.errorText(initResult)}');
        return devices;
      }

      try {
        final deviceCount = _pa.getDeviceCount();
        if (deviceCount < 0) {
          debugPrint('AudioDeviceService: 获取设备数量失败: ${_pa.errorText(deviceCount)}');
          return devices;
        }

        int displayIndex = 0;
        for (int i = 0; i < deviceCount; i++) {
          final infoPtr = _pa.getDeviceInfo(i);
          if (infoPtr.address == 0) continue;

          final info = infoPtr.ref;
          // 只枚举有输入通道的设备
          if (info.maxInputChannels <= 0) continue;

          final name = info.name.toDartString();

          devices.add(AudioInputDevice(
            index: displayIndex++,
            paDeviceIndex: i,
            name: name,
            description: name, // PortAudio 没有单独的描述字段
            status: DeviceAvailability.available,
          ));
        }
      } finally {
        _pa.terminate();
      }
    } catch (e) {
      debugPrint('AudioDeviceService: 枚举设备失败: $e');
    }

    // 更新缓存
    _cachedDevices = devices;
    _cacheTime = DateTime.now();

    return devices;
  }

  /// 清除设备列表缓存
  void invalidateCache() {
    _cachedDevices = null;
    _cacheTime = null;
  }

  /// 按名称查找设备 (AC3)
  /// 返回显示索引 (index)，不是 PortAudio 设备索引
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

  /// 根据显示索引获取 PortAudio 设备索引
  int getPaDeviceIndex(int displayIndex) {
    final devices = listInputDevices();
    if (displayIndex < 0 || displayIndex >= devices.length) {
      return paNoDevice;
    }
    return devices[displayIndex].paDeviceIndex;
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
