import 'dart:ffi';
import 'package:ffi/ffi.dart';
import 'package:flutter/foundation.dart';
import '../ffi/portaudio_ffi.dart';
import '../ffi/libpulse_ffi.dart';

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

  /// PortAudio 设备索引 (用于打开设备，-1 表示使用默认设备)
  final int paDeviceIndex;

  /// 设备名称 (内部名称，用于配置存储)
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
/// 优先使用 libpulse 枚举设备（与系统设置一致），
/// 如果 libpulse 不可用则回退到 PortAudio
class AudioDeviceService {
  AudioDeviceService._();

  static final AudioDeviceService instance = AudioDeviceService._();

  /// PortAudio 绑定 (延迟初始化)
  PortAudioBindings? _paBindings;

  /// 缓存的设备列表
  List<AudioInputDevice>? _cachedDevices;

  /// 缓存时间戳
  DateTime? _cacheTime;

  /// 缓存有效期 (5 秒)
  static const Duration _cacheTtl = Duration(seconds: 5);

  /// 是否使用 libpulse 枚举
  bool? _usePulse;

  /// 获取 PortAudio 绑定
  PortAudioBindings get _pa {
    _paBindings ??= PortAudioBindings();
    return _paBindings!;
  }

  /// 列出所有可用的音频输入设备
  ///
  /// 优先使用 libpulse 枚举（与系统设置显示一致），失败则回退到 PortAudio
  List<AudioInputDevice> listInputDevices({bool forceRefresh = false}) {
    // 检查缓存是否有效
    if (!forceRefresh &&
        _cachedDevices != null &&
        _cacheTime != null &&
        DateTime.now().difference(_cacheTime!) < _cacheTtl) {
      debugPrint('[AudioDeviceService] 📋 使用缓存设备列表 (${_cachedDevices!.length} 个设备)');
      return _cachedDevices!;
    }

    debugPrint('[AudioDeviceService] 📋 开始枚举音频设备...');

    // 优先使用 libpulse 枚举（设备名与系统设置一致）
    final pulseDevices = _listInputDevicesViaPulse();
    if (pulseDevices != null && pulseDevices.isNotEmpty) {
      _usePulse = true;
      _cachedDevices = pulseDevices;
      _cacheTime = DateTime.now();
      debugPrint('[AudioDeviceService] ✓ 使用 libpulse 枚举 (${pulseDevices.length} 个设备)');
      return pulseDevices;
    }

    // 回退到 PortAudio
    debugPrint('[AudioDeviceService] ⚠️ libpulse 不可用，回退到 PortAudio');
    _usePulse = false;
    final paDevices = _listInputDevicesViaPortAudio();
    _cachedDevices = paDevices;
    _cacheTime = DateTime.now();
    debugPrint('[AudioDeviceService] ✓ 使用 PortAudio 枚举 (${paDevices.length} 个设备)');
    return paDevices;
  }

  /// 使用 libpulse 枚举设备
  List<AudioInputDevice>? _listInputDevicesViaPulse() {
    try {
      debugPrint('[AudioDeviceService] 🔍 尝试 libpulse 枚举...');
      final enumerator = PulseDeviceEnumerator();
      final sources = enumerator.enumerate();

      if (sources == null) {
        debugPrint('[AudioDeviceService] ⚠️ libpulse 枚举返回 null');
        return null;
      }
      if (sources.isEmpty) {
        debugPrint('[AudioDeviceService] ⚠️ libpulse 枚举返回空列表');
        return null;
      }

      debugPrint('[AudioDeviceService] 📋 libpulse 发现 ${sources.length} 个 source:');
      final devices = <AudioInputDevice>[];
      int displayIndex = 0;

      for (final source in sources) {
        if (source.isMonitor) {
          debugPrint('[AudioDeviceService]   - "${source.name}" (monitor，跳过)');
          continue;
        }

        debugPrint('[AudioDeviceService]   ✓ "${source.name}" -> "${source.description}"');
        devices.add(AudioInputDevice(
          index: displayIndex++,
          paDeviceIndex: paNoDevice, // libpulse 设备不使用 PortAudio 索引
          name: source.name,
          description: source.description,
          status: DeviceAvailability.available,
        ));
      }

      return devices.isEmpty ? null : devices;
    } catch (e) {
      debugPrint('[AudioDeviceService] ❌ libpulse 枚举失败: $e');
      return null;
    }
  }

  /// 使用 PortAudio 枚举设备（回退方案）
  List<AudioInputDevice> _listInputDevicesViaPortAudio() {
    final devices = <AudioInputDevice>[];

    try {
      final initResult = _pa.initialize();
      if (initResult != paNoError) {
        debugPrint(
            'AudioDeviceService: PortAudio 初始化失败: ${_pa.errorText(initResult)}');
        return devices;
      }

      try {
        final deviceCount = _pa.getDeviceCount();
        if (deviceCount < 0) {
          debugPrint(
              'AudioDeviceService: 获取设备数量失败: ${_pa.errorText(deviceCount)}');
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

          // 过滤掉底层 ALSA 硬件设备，只保留 default/pipewire/pulse
          if (name.contains('hw:') || name.contains('plughw:')) continue;

          devices.add(AudioInputDevice(
            index: displayIndex++,
            paDeviceIndex: i,
            name: name,
            description: name,
            status: DeviceAvailability.available,
          ));
        }
      } finally {
        _pa.terminate();
      }
    } catch (e) {
      debugPrint('AudioDeviceService: PortAudio 枚举设备失败: $e');
    }

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
          device.description.contains(name) ||
          name.contains(device.description)) {
        return device.index;
      }
    }

    return -1;
  }

  /// 通过配置名称（可能是 description 或 name）获取设备的 libpulse name
  /// 用于传递给 pa_simple_new
  String? getDevicePulseName(String configName, {List<AudioInputDevice>? cachedDevices}) {
    if (configName == 'default' || configName.isEmpty) {
      return null; // 使用默认设备
    }

    final devices = cachedDevices ?? listInputDevices();

    // 1. 精确匹配 description 或 name
    for (final device in devices) {
      if (device.description == configName || device.name == configName) {
        return device.name;
      }
    }

    // 2. 子串匹配
    for (final device in devices) {
      if (device.description.contains(configName) ||
          configName.contains(device.description) ||
          device.name.contains(configName) ||
          configName.contains(device.name)) {
        return device.name;
      }
    }

    return null; // 未找到，将使用默认设备
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

  /// 是否正在使用 libpulse 枚举
  bool get isUsingPulse => _usePulse ?? false;
}
