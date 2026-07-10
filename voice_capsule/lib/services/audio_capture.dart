import 'dart:ffi';
import 'package:ffi/ffi.dart';
import '../ffi/portaudio_ffi.dart';
import 'pulse_audio_capture.dart';
import 'audio_device_service.dart';

/// 音频采集配置
class AudioConfig {
  static const int sampleRate = 16000;
  static const int channels = 1;
  static const int framesPerBuffer = 1600; // 100ms @ 16kHz
  static const int firstFrameBuffer = 320; // 20ms @ 16kHz (首帧快速响应)
}

/// 音频采集错误类型
enum AudioCaptureError {
  none,
  initializationFailed,
  noInputDevice,
  deviceUnavailable,
  streamOpenFailed,
  streamStartFailed,
  readFailed,
}

/// 音频设备状态枚举 (Story 3-7: AC11-12)
/// 用于在录音前预检测设备可用性
enum AudioDeviceStatus {
  available, // 设备可用
  noDevice, // 无设备
  deviceBusy, // 设备被占用
  permissionDenied, // 权限不足
  unknown, // 未知状态
}

/// 音频采集服务
///
/// 优先使用 libpulse-simple 进行音频采集（与系统设置一致），
/// 回退到 PortAudio。
/// 采样参数: 16kHz, 单声道, Float32
class AudioCapture {
  final PortAudioBindings _bindings;
  Pointer<Void>? _stream;
  Pointer<Float>? _buffer;
  Pointer<Pointer<Void>>? _streamPtr;
  Pointer<PaStreamParameters>? _inputParams;
  bool _isInitialized = false;
  bool _isCapturing = false;
  bool _isWarmedUp = false; // 是否已预热
  AudioCaptureError _lastReadError = AudioCaptureError.none; // M2 修复: 记录最近的读取错误
  String? _lastErrorDetail; // 详细错误信息 (用于诊断)
  bool _lastDeviceFallback = false; // Story 3-9: 记录最近一次设备回退状态

  // 首帧预缓冲 (冷启动优化)
  Pointer<Float>? _prebuffer;
  int _prebufferSamples = 0;
  bool _hasPrebuffer = false;

  // PulseAudio 支持
  PulseAudioCapture? _pulseCapture;
  bool _usePulse = false; // 是否使用 PulseAudio

  AudioCapture() : _bindings = PortAudioBindings();

  /// 智能选择默认设备
  ///
  /// 在 PipeWire 环境下，Pa_GetDefaultInputDevice() 可能返回底层 ALSA 硬件设备
  /// (如 hw:0,0)，这些设备不支持采样率转换，会导致 paInvalidSampleRate 错误。
  ///
  /// 此方法通过枚举所有设备并过滤掉 hw:/plughw: 设备，选择一个 PipeWire 兼容的
  /// 虚拟设备作为默认设备。
  int _selectSmartDefaultDevice() {
    // ignore: avoid_print
    print('[AudioCapture] 📋 开始智能设备选择...');

    final deviceCount = _bindings.getDeviceCount();
    if (deviceCount <= 0) {
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ PortAudio 设备数量: $deviceCount，回退到默认');
      return _bindings.getDefaultInputDevice();
    }

    // ignore: avoid_print
    print('[AudioCapture] 📋 PortAudio 检测到 $deviceCount 个设备:');

    final filteredDevices = <(int, String, int, double)>[]; // (index, name, channels, sampleRate)
    final skippedDevices = <String>[];

    // 遍历所有设备
    for (int i = 0; i < deviceCount; i++) {
      final infoPtr = _bindings.getDeviceInfo(i);
      if (infoPtr.address == 0) continue;

      final info = infoPtr.ref;
      final name = info.name.toDartString();
      final inputChannels = info.maxInputChannels;
      final sampleRate = info.defaultSampleRate;

      // 跳过无输入通道的设备
      if (inputChannels <= 0) {
        // ignore: avoid_print
        print('[AudioCapture]   [$i] "$name" (输出设备，跳过)');
        continue;
      }

      // 跳过底层 ALSA 硬件设备
      if (name.contains('hw:') || name.contains('plughw:')) {
        // ignore: avoid_print
        print('[AudioCapture]   [$i] "$name" ❌ 底层硬件设备，过滤');
        skippedDevices.add(name);
        continue;
      }

      // ignore: avoid_print
      print('[AudioCapture]   [$i] "$name" ✓ 可用 (ch=$inputChannels, rate=$sampleRate)');
      filteredDevices.add((i, name, inputChannels, sampleRate));
    }

    // ignore: avoid_print
    print('[AudioCapture] 📊 统计: 可用=${filteredDevices.length}, 过滤=${skippedDevices.length}');

    if (filteredDevices.isNotEmpty) {
      final (index, name, _, _) = filteredDevices.first;
      // ignore: avoid_print
      print('[AudioCapture] 🎯 智能选择: "$name" (index=$index)');
      return index;
    }

    // 回退到 PortAudio 默认设备
    final defaultIndex = _bindings.getDefaultInputDevice();
    final defaultInfo = _bindings.getDeviceInfo(defaultIndex);
    final defaultName = defaultInfo.address != 0
        ? defaultInfo.ref.name.toDartString()
        : 'unknown';
    // ignore: avoid_print
    print('[AudioCapture] ⚠️ 无可用设备，回退到 PortAudio 默认: "$defaultName" (index=$defaultIndex)');
    return defaultIndex;
  }

  /// Story 3-9: 根据设备名称解析设备索引 (AC2, AC3)
  ///
  /// 逻辑:
  /// 1. "default" 或空 → 使用智能默认设备选择（过滤底层硬件）
  /// 2. PortAudio 设备名 → 精确匹配 → 子串匹配 → 回退智能默认
  ///
  /// 返回: (设备索引, 是否回退到默认)
  (int, bool) _resolveDeviceIndex(String? deviceName) {
    // 如果是 "default" 或空，使用智能默认设备选择
    if (deviceName == null || deviceName.isEmpty || deviceName == 'default') {
      // ignore: avoid_print
      print('[AudioCapture] 📋 使用默认设备配置');
      final defaultIndex = _selectSmartDefaultDevice();
      return (defaultIndex, false);
    }

    // 尝试在 PortAudio 设备中按名称查找
    // ignore: avoid_print
    print('[AudioCapture] 📋 查找配置的设备: "$deviceName"');
    final deviceIndex = _findPortAudioDeviceByName(deviceName);
    if (deviceIndex >= 0) {
      final infoPtr = _bindings.getDeviceInfo(deviceIndex);
      final actualName = infoPtr.address != 0 ? infoPtr.ref.name.toDartString() : deviceName;
      // ignore: avoid_print
      print('[AudioCapture] ✓ 找到设备: "$actualName" (index=$deviceIndex)');
      return (deviceIndex, false);
    }

    // 回退到智能默认设备
    final defaultIndex = _selectSmartDefaultDevice();
    // ignore: avoid_print
    print('[AudioCapture] ⚠️ 未找到设备 "$deviceName"，回退到智能默认设备');
    return (defaultIndex, true);
  }

  /// 在 PortAudio 设备列表中按名称查找设备
  int _findPortAudioDeviceByName(String deviceName) {
    final deviceCount = _bindings.getDeviceCount();
    if (deviceCount <= 0) return -1;

    for (int i = 0; i < deviceCount; i++) {
      final infoPtr = _bindings.getDeviceInfo(i);
      if (infoPtr.address == 0) continue;

      final info = infoPtr.ref;
      if (info.maxInputChannels <= 0) continue;

      final name = info.name.toDartString();

      // 精确匹配或子串匹配
      if (name == deviceName || name.contains(deviceName) || deviceName.contains(name)) {
        return i;
      }
    }

    return -1;
  }

  /// 预热音频设备
  ///
  /// 在应用启动时调用，提前初始化音频采集。
  /// 优先使用 libpulse-simple（与系统设置一致），失败则回退到 PortAudio。
  ///
  /// Story 3-9: [deviceName] 设备名称（可能是 description 或内部名称），"default" 或空使用系统默认
  ///
  /// 返回值:
  /// - [AudioCaptureError.none] 预热成功
  /// - 其他错误码表示预热失败（但不影响后续使用）
  Future<AudioCaptureError> warmup({String? deviceName}) async {
    if (_isWarmedUp) {
      return AudioCaptureError.none;
    }

    // ignore: avoid_print
    print('[AudioCapture] 开始预热音频设备...');
    // ignore: avoid_print
    print('[AudioCapture] 📋 配置的设备: ${deviceName ?? "default"}');

    // 将配置名称（可能是 description）转换为 libpulse name
    final pulseName = deviceName != null && deviceName != 'default'
        ? AudioDeviceService.instance.getDevicePulseName(deviceName)
        : null;

    if (pulseName != null) {
      // ignore: avoid_print
      print('[AudioCapture] 📋 解析为 libpulse name: $pulseName');
    }

    // 1. 优先尝试 PulseAudioCapture（与系统设置一致）
    if (PulseAudioCapture.isAvailable()) {
      // ignore: avoid_print
      print('[AudioCapture] 🔍 尝试使用 libpulse-simple...');
      _pulseCapture = PulseAudioCapture();
      final pulseResult = await _pulseCapture!.initialize(deviceName: pulseName);
      if (pulseResult == PulseAudioError.none) {
        _usePulse = true;
        _isWarmedUp = true;
        _buffer = _pulseCapture!.buffer;
        // ignore: avoid_print
        print('[AudioCapture] ✅ 使用 libpulse-simple 预热成功');
        return AudioCaptureError.none;
      }
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ libpulse-simple 初始化失败: ${_pulseCapture!.lastError}');
      _pulseCapture!.dispose();
      _pulseCapture = null;
    } else {
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ libpulse-simple 不可用');
    }

    // 2. 回退到 PortAudio
    // ignore: avoid_print
    print('[AudioCapture] 📋 回退到 PortAudio...');
    return _warmupPortAudio(deviceName: deviceName);
  }

  /// 使用 PortAudio 预热（回退方案）
  Future<AudioCaptureError> _warmupPortAudio({String? deviceName}) async {
    // 初始化 PortAudio
    final initResult = _bindings.initialize();
    if (initResult != paNoError) {
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ PortAudio 初始化失败: $initResult');
      return AudioCaptureError.initializationFailed;
    }
    _isInitialized = true;

    // 解析设备索引
    final (deviceIndex, fallback) = _resolveDeviceIndex(deviceName);
    _lastDeviceFallback = fallback;
    if (deviceIndex == paNoDevice) {
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ 无可用输入设备');
      _isWarmedUp = true;
      return AudioCaptureError.noInputDevice;
    }
    if (fallback) {
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ 配置的设备不可用，已回退到默认设备');
    }

    // 获取设备信息
    final deviceInfo = _bindings.getDeviceInfo(deviceIndex);
    if (deviceInfo == nullptr) {
      _isWarmedUp = true;
      return AudioCaptureError.deviceUnavailable;
    }

    // 分配缓冲区
    _buffer = calloc<Float>(AudioConfig.framesPerBuffer);

    // 配置输入参数
    _inputParams = calloc<PaStreamParameters>();
    _inputParams!.ref.device = deviceIndex;
    _inputParams!.ref.channelCount = AudioConfig.channels;
    _inputParams!.ref.sampleFormat = paFloat32;
    _inputParams!.ref.suggestedLatency = deviceInfo.ref.defaultLowInputLatency;
    _inputParams!.ref.hostApiSpecificStreamInfo = nullptr;

    // 打开音频流
    _streamPtr = calloc<Pointer<Void>>();
    final openResult = _bindings.openStream(
      _streamPtr!,
      _inputParams!,
      nullptr,
      AudioConfig.sampleRate.toDouble(),
      AudioConfig.framesPerBuffer,
      paClipOff,
      nullptr,
      nullptr,
    );

    if (openResult != paNoError) {
      final errorText = _bindings.errorText(openResult);
      final devName = deviceInfo.ref.name.toDartString();
      _lastErrorDetail = 'PortAudio 错误: $openResult ($errorText), 设备: "$devName", maxInputChannels=${deviceInfo.ref.maxInputChannels}, defaultSampleRate=${deviceInfo.ref.defaultSampleRate}';
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ 打开音频流失败: $openResult ($errorText)');
      // ignore: avoid_print
      print('[AudioCapture] 📋 设备信息: "$devName", maxInputChannels=${deviceInfo.ref.maxInputChannels}, defaultSampleRate=${deviceInfo.ref.defaultSampleRate}');
      // ignore: avoid_print
      print('[AudioCapture] 💡 可能原因: 1) PulseAudio/PipeWire 未运行 2) 设备被占用 3) 权限不足');
      _isWarmedUp = true;
      return AudioCaptureError.streamOpenFailed;
    }

    _stream = _streamPtr!.value;

    // 启动音频流，读取一帧数据让硬件准备好
    final startResult = _bindings.startStream(_stream!);
    if (startResult == paNoError) {
      _bindings.readStream(_stream!, _buffer!, AudioConfig.framesPerBuffer);
      _bindings.stopStream(_stream!);
    }

    _isWarmedUp = true;
    _isCapturing = false;
    _usePulse = false;

    // ignore: avoid_print
    print('[AudioCapture] ✅ 使用 PortAudio 预热成功');
    return AudioCaptureError.none;
  }

  /// Story 3-7: 检查音频设备状态 (不初始化流，仅检测)
  /// 用于在录音前预检测设备可用性
  ///
  /// 返回值:
  /// - [AudioDeviceStatus.available] 设备可用
  /// - [AudioDeviceStatus.noDevice] 未检测到麦克风
  /// - [AudioDeviceStatus.deviceBusy] 设备被其他应用占用
  /// - [AudioDeviceStatus.permissionDenied] 权限不足
  /// - [AudioDeviceStatus.unknown] 未知状态
  static Future<AudioDeviceStatus> checkDeviceStatus() async {
    final bindings = PortAudioBindings();

    // 1. 初始化 PortAudio
    final initResult = bindings.initialize();
    if (initResult != paNoError) {
      return AudioDeviceStatus.unknown;
    }

    try {
      // 2. 获取默认输入设备
      final deviceIndex = bindings.getDefaultInputDevice();
      if (deviceIndex == paNoDevice) {
        return AudioDeviceStatus.noDevice;
      }

      // 3. 获取设备信息
      final deviceInfo = bindings.getDeviceInfo(deviceIndex);
      if (deviceInfo == nullptr) {
        return AudioDeviceStatus.noDevice;
      }

      // 4. 尝试打开流以检测设备是否被占用
      final inputParams = calloc<PaStreamParameters>();
      final streamPtr = calloc<Pointer<Void>>();

      try {
        inputParams.ref.device = deviceIndex;
        inputParams.ref.channelCount = AudioConfig.channels;
        inputParams.ref.sampleFormat = paFloat32;
        inputParams.ref.suggestedLatency =
            deviceInfo.ref.defaultLowInputLatency;
        inputParams.ref.hostApiSpecificStreamInfo = nullptr;

        final openResult = bindings.openStream(
          streamPtr,
          inputParams,
          nullptr,
          AudioConfig.sampleRate.toDouble(),
          AudioConfig.framesPerBuffer,
          paClipOff,
          nullptr,
          nullptr,
        );

        if (openResult == paNoError) {
          // 成功打开，立即关闭
          bindings.closeStream(streamPtr.value);
          return AudioDeviceStatus.available;
        } else if (openResult == paDeviceUnavailable) {
          return AudioDeviceStatus.deviceBusy;
        } else if (openResult == paInvalidChannelCount) {
          return AudioDeviceStatus.permissionDenied;
        } else {
          return _mapPaError(openResult);
        }
      } finally {
        calloc.free(inputParams);
        calloc.free(streamPtr);
      }
    } finally {
      // 5. 释放 PortAudio
      bindings.terminate();
    }
  }

  /// 将 PortAudio 错误码映射到 AudioDeviceStatus
  static AudioDeviceStatus _mapPaError(int paErrorCode) {
    switch (paErrorCode) {
      case paNoDevice:
        return AudioDeviceStatus.noDevice;
      case paDeviceUnavailable:
        return AudioDeviceStatus.deviceBusy;
      case paInternalError:
        return AudioDeviceStatus.unknown;
      default:
        return AudioDeviceStatus.unknown;
    }
  }

  /// 启动音频采集
  ///
  /// Story 3-9: [deviceName] 可选设备名称，"default" 或空使用系统默认
  ///
  /// 返回值:
  /// - [AudioCaptureError.none] 成功
  /// - [AudioCaptureError.initializationFailed] PortAudio 初始化失败
  /// - [AudioCaptureError.noInputDevice] 无可用输入设备
  /// - [AudioCaptureError.streamOpenFailed] 无法打开音频流
  /// - [AudioCaptureError.streamStartFailed] 无法启动音频流
  Future<AudioCaptureError> start({String? deviceName}) async {
    if (_isCapturing) {
      return AudioCaptureError.none;
    }

    // 如果使用 PulseAudio
    if (_usePulse && _pulseCapture != null) {
      final result = await _pulseCapture!.start();
      if (result == PulseAudioError.none) {
        _isCapturing = true;
        return AudioCaptureError.none;
      }
      return AudioCaptureError.streamStartFailed;
    }

    // 如果已经预热，直接启动流 (PortAudio)
    if (_isWarmedUp && _stream != null) {
      final startResult = _bindings.startStream(_stream!);
      if (startResult != paNoError) {
        return AudioCaptureError.streamStartFailed;
      }
      _isCapturing = true;

      // 冷启动优化: 预读取首帧到预缓冲区
      await _prefillBuffer();

      return AudioCaptureError.none;
    }

    // 未预热，执行完整初始化流程
    // 1. 初始化 PortAudio
    if (!_isInitialized) {
      final initResult = _bindings.initialize();
      if (initResult != paNoError) {
        return AudioCaptureError.initializationFailed;
      }
      _isInitialized = true;
    }

    // 2. Story 3-9: 解析设备索引 (AC2, AC3)
    final (deviceIndex, fallback) = _resolveDeviceIndex(deviceName);
    _lastDeviceFallback = fallback; // 记录回退状态 (AC18)
    if (deviceIndex == paNoDevice) {
      _bindings.terminate();
      _isInitialized = false;
      return AudioCaptureError.noInputDevice;
    }
    if (fallback) {
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ 配置的设备不可用，已回退到默认设备');
    }

    // 3. 获取设备信息以获取默认延迟
    final deviceInfo = _bindings.getDeviceInfo(deviceIndex);
    if (deviceInfo == nullptr) {
      _bindings.terminate();
      _isInitialized = false;
      return AudioCaptureError.deviceUnavailable;
    }

    // 4. 分配缓冲区
    _buffer = calloc<Float>(AudioConfig.framesPerBuffer);

    // 5. 配置输入参数
    _inputParams = calloc<PaStreamParameters>();
    _inputParams!.ref.device = deviceIndex;
    _inputParams!.ref.channelCount = AudioConfig.channels;
    _inputParams!.ref.sampleFormat = paFloat32;
    _inputParams!.ref.suggestedLatency = deviceInfo.ref.defaultLowInputLatency;
    _inputParams!.ref.hostApiSpecificStreamInfo = nullptr;

    // 6. 打开音频流
    _streamPtr = calloc<Pointer<Void>>();
    final openResult = _bindings.openStream(
      _streamPtr!,
      _inputParams!,
      nullptr, // 无输出
      AudioConfig.sampleRate.toDouble(),
      AudioConfig.framesPerBuffer,
      paClipOff,
      nullptr, // 无回调，使用阻塞模式
      nullptr, // 无用户数据
    );

    if (openResult != paNoError) {
      final errorText = _bindings.errorText(openResult);
      final deviceName = deviceInfo.ref.name.toDartString();
      _lastErrorDetail = 'PortAudio 错误: $openResult ($errorText), 设备: "$deviceName", maxInputChannels=${deviceInfo.ref.maxInputChannels}, defaultSampleRate=${deviceInfo.ref.defaultSampleRate}';
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ 打开音频流失败: $openResult ($errorText)');
      // ignore: avoid_print
      print('[AudioCapture] 📋 设备信息: "$deviceName", maxInputChannels=${deviceInfo.ref.maxInputChannels}, defaultSampleRate=${deviceInfo.ref.defaultSampleRate}');
      // ignore: avoid_print
      print('[AudioCapture] 💡 可能原因: 1) PulseAudio/PipeWire 未运行 2) 设备被占用 3) 权限不足');
      _bindings.terminate(); // C1 修复: 必须调用 terminate 释放 PortAudio
      _isInitialized = false;
      _cleanup();
      return AudioCaptureError.streamOpenFailed;
    }

    _stream = _streamPtr!.value;

    // 7. 启动音频流
    final startResult = _bindings.startStream(_stream!);
    if (startResult != paNoError) {
      _bindings.closeStream(_stream!);
      _bindings.terminate(); // C1 修复: 必须调用 terminate 释放 PortAudio
      _isInitialized = false;
      _cleanup();
      return AudioCaptureError.streamStartFailed;
    }

    _isCapturing = true;

    // 冷启动优化: 预读取首帧到预缓冲区
    await _prefillBuffer();

    return AudioCaptureError.none;
  }

  /// 冷启动优化: 预填充音频缓冲区
  ///
  /// 在 start() 后立即读取一小帧数据到预缓冲区，
  /// 让第一次 read() 能够快速返回数据，避免丢失首帧语音。
  Future<void> _prefillBuffer() async {
    // 分配预缓冲区
    _prebuffer ??= calloc<Float>(AudioConfig.firstFrameBuffer);

    // 读取一小帧数据 (20ms)
    final result = _bindings.readStream(
      _stream!,
      _prebuffer!,
      AudioConfig.firstFrameBuffer,
    );

    if (result == paNoError || result == paInputOverflowed) {
      _prebufferSamples = AudioConfig.firstFrameBuffer;
      _hasPrebuffer = true;
      // ignore: avoid_print
      print('[AudioCapture] ✅ 首帧预缓冲完成 (${AudioConfig.firstFrameBuffer} samples)');
    } else {
      _hasPrebuffer = false;
      _prebufferSamples = 0;
    }
  }

  /// 读取音频数据
  ///
  /// [buffer] 目标缓冲区
  /// [samples] 要读取的样本数
  ///
  /// 返回值:
  /// - > 0: 实际读取的样本数
  /// - -1: 读取失败 (检查 [lastReadError] 获取详细错误类型)
  /// 异步读取音频数据
  ///
  /// PulseAudio 路径把阻塞的 pa_simple_read 移到后台 isolate，主事件循环
  /// 保持自由（部分识别结果可实时渲染）；PortAudio 路径的读取由回调线程
  /// 填充的环形缓冲支撑、近乎即时，直接走同步 read。
  Future<int> readAsync(Pointer<Float> buffer, int samples) async {
    if (_usePulse && _pulseCapture != null) {
      if (!_isCapturing) {
        _lastReadError = AudioCaptureError.readFailed;
        return -1;
      }
      final result = await _pulseCapture!.readAsync(buffer, samples);
      if (result < 0) {
        _lastReadError = AudioCaptureError.readFailed;
        return -1;
      }
      _lastReadError = AudioCaptureError.none;
      return result;
    }
    return read(buffer, samples);
  }

  int read(Pointer<Float> buffer, int samples) {
    // 如果使用 PulseAudio
    if (_usePulse && _pulseCapture != null) {
      if (!_isCapturing) {
        _lastReadError = AudioCaptureError.readFailed;
        return -1;
      }
      final result = _pulseCapture!.read(buffer, samples);
      if (result < 0) {
        _lastReadError = AudioCaptureError.readFailed;
        return -1;
      }
      _lastReadError = AudioCaptureError.none;
      return result;
    }

    // PortAudio 路径
    if (!_isCapturing || _stream == null) {
      _lastReadError = AudioCaptureError.readFailed;
      return -1;
    }

    // 冷启动优化: 如果有预缓冲数据，先复制到目标缓冲区
    if (_hasPrebuffer && _prebufferSamples > 0 && _prebuffer != null) {
      // 复制预缓冲数据到目标缓冲区开头
      for (int i = 0; i < _prebufferSamples && i < samples; i++) {
        buffer[i] = _prebuffer![i];
      }

      final prebufferUsed = _prebufferSamples;
      _hasPrebuffer = false;
      _prebufferSamples = 0;

      // 如果预缓冲数据不够，从流中读取剩余数据
      if (prebufferUsed < samples) {
        final remainingSamples = samples - prebufferUsed;
        final offsetBuffer = buffer + prebufferUsed;
        final result = _bindings.readStream(_stream!, offsetBuffer, remainingSamples);

        if (result != paNoError && result != paInputOverflowed) {
          if (result == paDeviceUnavailable) {
            _lastReadError = AudioCaptureError.deviceUnavailable;
            return -1;
          }
          _lastReadError = AudioCaptureError.readFailed;
          return -1;
        }
      }

      _lastReadError = AudioCaptureError.none;
      return samples;
    }

    // 正常读取流程
    final result = _bindings.readStream(_stream!, buffer, samples);

    // paInputOverflowed 时继续读取 (不视为错误)
    if (result == paInputOverflowed) {
      _lastReadError = AudioCaptureError.none;
      return samples; // 数据仍然有效
    }

    // M2 修复: 检测设备不可用错误
    if (result == paDeviceUnavailable) {
      _lastReadError = AudioCaptureError.deviceUnavailable;
      return -1;
    }

    if (result != paNoError) {
      _lastReadError = AudioCaptureError.readFailed;
      return -1;
    }

    _lastReadError = AudioCaptureError.none;
    return samples;
  }

  /// 停止音频采集
  Future<void> stop() async {
    if (!_isCapturing) {
      return;
    }

    // 如果使用 PulseAudio
    if (_usePulse && _pulseCapture != null) {
      _pulseCapture!.stop();
      _isCapturing = false;
      return;
    }

    // PortAudio 路径
    if (_stream == null) {
      return;
    }

    _bindings.stopStream(_stream!);
    _isCapturing = false;

    // 重置预缓冲状态
    _hasPrebuffer = false;
    _prebufferSamples = 0;
  }

  /// 释放所有资源
  void dispose() {
    // 如果使用 PulseAudio
    if (_usePulse && _pulseCapture != null) {
      _pulseCapture!.dispose();
      _pulseCapture = null;
      _usePulse = false;
      _isCapturing = false;
      _isWarmedUp = false;
      _buffer = null;
      return;
    }

    // PortAudio 路径
    if (_isCapturing) {
      _bindings.stopStream(_stream!);
      _isCapturing = false;
    }

    if (_stream != null) {
      _bindings.closeStream(_stream!);
      _stream = null;
    }

    if (_isInitialized) {
      _bindings.terminate();
      _isInitialized = false;
    }

    _cleanup();
  }

  /// 清理分配的内存
  void _cleanup() {
    if (_buffer != null) {
      calloc.free(_buffer!);
      _buffer = null;
    }
    if (_prebuffer != null) {
      calloc.free(_prebuffer!);
      _prebuffer = null;
    }
    if (_inputParams != null) {
      calloc.free(_inputParams!);
      _inputParams = null;
    }
    if (_streamPtr != null) {
      calloc.free(_streamPtr!);
      _streamPtr = null;
    }
    _hasPrebuffer = false;
    _prebufferSamples = 0;
  }

  /// Story 2.3 使用此 getter 获取缓冲区指针 (零拷贝接口)
  /// 要求：缓冲区大小 >= 1600 samples (100ms @ 16kHz)
  Pointer<Float> get buffer {
    if (_buffer == null) {
      throw StateError('AudioCapture 未初始化，请先调用 start()');
    }
    return _buffer!;
  }

  /// 是否正在采集
  bool get isCapturing => _isCapturing;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 最近一次 read() 调用的错误类型 (M2 修复)
  /// 当 read() 返回 -1 时，检查此属性获取详细错误信息
  AudioCaptureError get lastReadError => _lastReadError;

  /// 详细错误信息 (用于诊断)
  /// 当 warmup() 或 start() 返回错误时，检查此属性获取详细信息
  String? get lastErrorDetail => _lastErrorDetail;

  /// Story 3-9 AC18: 最近一次设备解析是否回退到了默认设备
  /// 当配置的设备不存在时返回 true
  bool get lastDeviceFallback => _lastDeviceFallback;
}
