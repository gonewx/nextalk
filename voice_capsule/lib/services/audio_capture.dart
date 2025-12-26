import 'dart:ffi';
import 'package:ffi/ffi.dart';
import '../ffi/portaudio_ffi.dart';

/// 音频采集配置
class AudioConfig {
  static const int sampleRate = 16000;
  static const int channels = 1;
  static const int framesPerBuffer = 1600; // 100ms @ 16kHz
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
/// 使用 PortAudio 进行音频采集，支持零拷贝接口。
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

  AudioCapture() : _bindings = PortAudioBindings();

  /// 预热音频设备
  ///
  /// 在应用启动时调用，提前初始化 PortAudio 并打开音频流，
  /// 避免用户第一次录音时因设备初始化延迟导致丢失语音。
  ///
  /// 返回值:
  /// - [AudioCaptureError.none] 预热成功
  /// - 其他错误码表示预热失败（但不影响后续使用）
  Future<AudioCaptureError> warmup() async {
    if (_isWarmedUp) {
      return AudioCaptureError.none;
    }

    // ignore: avoid_print
    print('[AudioCapture] 开始预热音频设备...');

    // 1. 初始化 PortAudio (这会触发 ALSA 警告)
    final initResult = _bindings.initialize();
    if (initResult != paNoError) {
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ PortAudio 初始化失败: $initResult');
      return AudioCaptureError.initializationFailed;
    }
    _isInitialized = true;

    // 2. 获取默认输入设备
    final deviceIndex = _bindings.getDefaultInputDevice();
    if (deviceIndex == paNoDevice) {
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ 无可用输入设备');
      // 不终止 PortAudio，保持初始化状态
      _isWarmedUp = true;
      return AudioCaptureError.noInputDevice;
    }

    // 3. 获取设备信息
    final deviceInfo = _bindings.getDeviceInfo(deviceIndex);
    if (deviceInfo == nullptr) {
      _isWarmedUp = true;
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

    // 6. 打开音频流 (预热)
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
      // ignore: avoid_print
      print('[AudioCapture] ⚠️ 打开音频流失败: $openResult');
      _isWarmedUp = true;
      return AudioCaptureError.streamOpenFailed;
    }

    _stream = _streamPtr!.value;

    // 7. 启动音频流，读取一帧数据让硬件准备好
    final startResult = _bindings.startStream(_stream!);
    if (startResult == paNoError) {
      // 读取一帧数据丢弃 (让硬件准备好)
      _bindings.readStream(_stream!, _buffer!, AudioConfig.framesPerBuffer);

      // 停止流 (预热完成，等待真正使用)
      _bindings.stopStream(_stream!);
    }

    _isWarmedUp = true;
    _isCapturing = false;

    // ignore: avoid_print
    print('[AudioCapture] ✅ 音频设备预热完成');
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
  /// 返回值:
  /// - [AudioCaptureError.none] 成功
  /// - [AudioCaptureError.initializationFailed] PortAudio 初始化失败
  /// - [AudioCaptureError.noInputDevice] 无可用输入设备
  /// - [AudioCaptureError.streamOpenFailed] 无法打开音频流
  /// - [AudioCaptureError.streamStartFailed] 无法启动音频流
  Future<AudioCaptureError> start() async {
    if (_isCapturing) {
      return AudioCaptureError.none;
    }

    // 如果已经预热，直接启动流
    if (_isWarmedUp && _stream != null) {
      final startResult = _bindings.startStream(_stream!);
      if (startResult != paNoError) {
        return AudioCaptureError.streamStartFailed;
      }
      _isCapturing = true;
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

    // 2. 获取默认输入设备
    final deviceIndex = _bindings.getDefaultInputDevice();
    if (deviceIndex == paNoDevice) {
      _bindings.terminate();
      _isInitialized = false;
      return AudioCaptureError.noInputDevice;
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
    return AudioCaptureError.none;
  }

  /// 读取音频数据
  ///
  /// [buffer] 目标缓冲区
  /// [samples] 要读取的样本数
  ///
  /// 返回值:
  /// - > 0: 实际读取的样本数
  /// - -1: 读取失败 (检查 [lastReadError] 获取详细错误类型)
  int read(Pointer<Float> buffer, int samples) {
    if (!_isCapturing || _stream == null) {
      _lastReadError = AudioCaptureError.readFailed;
      return -1;
    }

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
    if (!_isCapturing || _stream == null) {
      return;
    }

    _bindings.stopStream(_stream!);
    _isCapturing = false;
  }

  /// 释放所有资源
  void dispose() {
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
    if (_inputParams != null) {
      calloc.free(_inputParams!);
      _inputParams = null;
    }
    if (_streamPtr != null) {
      calloc.free(_streamPtr!);
      _streamPtr = null;
    }
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
}
