import 'dart:ffi';
import 'package:ffi/ffi.dart';
import '../ffi/libpulse_simple_ffi.dart';

/// 音频采集配置
class PulseAudioConfig {
  static const int sampleRate = 16000;
  static const int channels = 1;
  static const int framesPerBuffer = 1600; // 100ms @ 16kHz
}

/// PulseAudio 录音错误类型
enum PulseAudioError {
  none,
  libraryNotFound,
  connectionFailed,
  readFailed,
  notInitialized,
}

/// 使用 libpulse-simple 的音频采集服务
///
/// 优点：
/// - 设备名与系统设置完全一致（如 alsa_input.xxx）
/// - 自动处理采样率转换
/// - 与 PipeWire/PulseAudio 完美集成
class PulseAudioCapture {
  LibPulseSimpleBindings? _bindings;
  Pointer<PaSimple>? _stream;
  Pointer<Float>? _buffer;
  Pointer<Int32>? _errorPtr;
  Pointer<PaSampleSpec>? _sampleSpec;

  bool _isInitialized = false;
  bool _isCapturing = false;
  String? _lastError;

  /// 检查 libpulse-simple 是否可用
  static bool isAvailable() {
    try {
      LibPulseSimpleBindings();
      return true;
    } catch (_) {
      return false;
    }
  }

  /// 初始化 PulseAudio 录音
  ///
  /// [deviceName] 设备名（如 "alsa_input.pci-0000_00_08.0.analog-stereo"），
  /// 传入 null 或 "default" 使用系统默认设备
  Future<PulseAudioError> initialize({String? deviceName}) async {
    if (_isInitialized) {
      return PulseAudioError.none;
    }

    // ignore: avoid_print
    print('[PulseAudioCapture] 📋 初始化 libpulse-simple...');

    try {
      _bindings = LibPulseSimpleBindings();
    } catch (e) {
      _lastError = '无法加载 libpulse-simple: $e';
      // ignore: avoid_print
      print('[PulseAudioCapture] ❌ $_lastError');
      return PulseAudioError.libraryNotFound;
    }

    // 分配内存
    _buffer = calloc<Float>(PulseAudioConfig.framesPerBuffer);
    _errorPtr = calloc<Int32>();
    _sampleSpec = calloc<PaSampleSpec>();

    // 配置采样格式
    _sampleSpec!.ref.format = PA_SAMPLE_FLOAT32NE;
    _sampleSpec!.ref.rate = PulseAudioConfig.sampleRate;
    _sampleSpec!.ref.channels = PulseAudioConfig.channels;

    // 创建录音流
    final appName = 'Nextalk'.toNativeUtf8();
    final streamName = 'Voice Input'.toNativeUtf8();
    final devicePtr = (deviceName != null && deviceName != 'default')
        ? deviceName.toNativeUtf8()
        : nullptr;

    // ignore: avoid_print
    print('[PulseAudioCapture] 📋 连接设备: ${deviceName ?? "default"}');

    _stream = _bindings!.simpleNew(
      nullptr, // 默认服务器
      appName,
      PA_STREAM_RECORD,
      devicePtr.cast(),
      streamName,
      _sampleSpec!,
      nullptr, // 默认 channel map
      nullptr, // 默认缓冲属性
      _errorPtr!,
    );

    // 释放临时字符串
    calloc.free(appName);
    calloc.free(streamName);
    if (devicePtr.address != 0) {
      calloc.free(devicePtr);
    }

    if (_stream == null || _stream!.address == 0) {
      final errorCode = _errorPtr!.value;
      final errorMsg = _bindings!.strerror(errorCode).toDartString();
      _lastError = 'pa_simple_new 失败: $errorMsg (code=$errorCode)';
      // ignore: avoid_print
      print('[PulseAudioCapture] ❌ $_lastError');
      _cleanup();
      return PulseAudioError.connectionFailed;
    }

    _isInitialized = true;
    // ignore: avoid_print
    print('[PulseAudioCapture] ✓ 初始化成功');
    return PulseAudioError.none;
  }

  /// 开始录音
  PulseAudioError start() {
    if (!_isInitialized) {
      return PulseAudioError.notInitialized;
    }
    _isCapturing = true;
    // ignore: avoid_print
    print('[PulseAudioCapture] ▶️ 开始录音');
    return PulseAudioError.none;
  }

  /// 停止录音
  void stop() {
    _isCapturing = false;
    // ignore: avoid_print
    print('[PulseAudioCapture] ⏹️ 停止录音');
  }

  /// 读取音频数据
  ///
  /// 返回实际读取的样本数，失败返回 -1
  int read(Pointer<Float> buffer, int samples) {
    if (!_isInitialized || !_isCapturing || _stream == null) {
      return -1;
    }

    final bytesToRead = samples * sizeOf<Float>();
    final result = _bindings!.simpleRead(
      _stream!,
      buffer.cast(),
      bytesToRead,
      _errorPtr!,
    );

    if (result < 0) {
      final errorCode = _errorPtr!.value;
      final errorMsg = _bindings!.strerror(errorCode).toDartString();
      _lastError = 'pa_simple_read 失败: $errorMsg';
      // ignore: avoid_print
      print('[PulseAudioCapture] ❌ $_lastError');
      return -1;
    }

    return samples;
  }

  /// 获取内部缓冲区（零拷贝接口）
  Pointer<Float>? get buffer => _buffer;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 是否正在录音
  bool get isCapturing => _isCapturing;

  /// 最后的错误信息
  String? get lastError => _lastError;

  /// 释放资源
  void dispose() {
    // ignore: avoid_print
    print('[PulseAudioCapture] 🗑️ 释放资源');
    stop();
    _cleanup();
  }

  void _cleanup() {
    if (_stream != null && _stream!.address != 0) {
      _bindings?.simpleFree(_stream!);
      _stream = null;
    }
    if (_buffer != null) {
      calloc.free(_buffer!);
      _buffer = null;
    }
    if (_errorPtr != null) {
      calloc.free(_errorPtr!);
      _errorPtr = null;
    }
    if (_sampleSpec != null) {
      calloc.free(_sampleSpec!);
      _sampleSpec = null;
    }
    _isInitialized = false;
    _isCapturing = false;
  }
}
