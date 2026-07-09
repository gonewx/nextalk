import 'dart:ffi';
import 'dart:isolate';
import 'package:ffi/ffi.dart';
import '../ffi/libpulse_simple_ffi.dart';

/// 音频采集配置
class PulseAudioConfig {
  static const int sampleRate = 16000;
  static const int channels = 1;
  static const int framesPerBuffer = 1600; // 100ms @ 16kHz

  /// 录音流 fragsize (字节)：与单次 read() 的量同源 (100ms Float32)，
  /// 保证服务端投递粒度与采集循环节拍对齐
  static final int fragsizeBytes = framesPerBuffer * sizeOf<Float>();
}

/// 在后台 isolate 中执行阻塞的 pa_simple_read
///
/// pa_simple_read 会阻塞到请求字节数凑齐 (~fragsize 周期)，放在主 isolate
/// 会饿死事件循环（部分识别结果无法渲染、动画冻结）。跨 isolate 只传地址
/// 与长度 (int)，在目标 isolate 内重建绑定；音频写入进程共享内存，
/// await 返回后主 isolate 直接可见。
///
/// 返回 0 表示成功，非 0 为 pa 错误码（-1 表示失败但未取到错误码）。
int _blockingRead((int streamAddr, int bufferAddr, int bytes) args) {
  final bindings = LibPulseSimpleBindings();
  final errPtr = calloc<Int32>();
  try {
    final result = bindings.simpleRead(
      Pointer<PaSimple>.fromAddress(args.$1),
      Pointer<Void>.fromAddress(args.$2),
      args.$3,
      errPtr,
    );
    if (result < 0) {
      return errPtr.value != 0 ? errPtr.value : -1;
    }
    return 0;
  } finally {
    calloc.free(errPtr);
  }
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
  Pointer<PaBufferAttr>? _bufferAttr;

  bool _isInitialized = false;
  bool _isCapturing = false;
  String? _lastError;

  /// 在飞的后台读取（dispose 时须等它完成才能释放 stream）
  Future<int>? _pendingRead;

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

    // 配置缓冲属性: 显式设置 fragsize 降低单次投递延迟 (100ms)，
    // 否则服务端默认碎片可达秒级，pa_simple_read 会成批迟到。
    // 注意 fragsize 不限制停录期间的积压上限，陈旧音频靠 start() 的 flush() 丢弃
    _bufferAttr = calloc<PaBufferAttr>();
    _bufferAttr!.ref.maxlength = 0xFFFFFFFF; // -1: 服务端默认
    _bufferAttr!.ref.tlength = 0xFFFFFFFF; // 以下三项为 playback 字段，录音流忽略
    _bufferAttr!.ref.prebuf = 0xFFFFFFFF;
    _bufferAttr!.ref.minreq = 0xFFFFFFFF;
    _bufferAttr!.ref.fragsize = PulseAudioConfig.fragsizeBytes; // 6400

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
      _bufferAttr!, // 缓冲属性 (fragsize=100ms)
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
  ///
  /// 关键：录音流在 warmup 时创建后常开，停止期间无人 read，
  /// 服务端缓冲会持续积压陈旧音频。此处必须 flush 丢弃积压，
  /// 否则本次录音的前若干块读到的是"几秒前"的声音，
  /// 且主循环按 1x 实时速率消化，转录会恒定滞后积压时长。
  PulseAudioError start() {
    if (!_isInitialized) {
      return PulseAudioError.notInitialized;
    }
    flush();
    _isCapturing = true;
    // ignore: avoid_print
    print('[PulseAudioCapture] ▶️ 开始录音');
    return PulseAudioError.none;
  }

  /// 丢弃服务端缓冲中积压的音频数据
  void flush() {
    if (!_isInitialized || _stream == null || _stream!.address == 0) return;
    final result = _bindings!.simpleFlush(_stream!, _errorPtr!);
    if (result < 0) {
      final errorMsg = _bindings!.strerror(_errorPtr!.value).toDartString();
      // ignore: avoid_print
      print('[PulseAudioCapture] ⚠️ pa_simple_flush 失败: $errorMsg');
    } else {
      // ignore: avoid_print
      print('[PulseAudioCapture] 🚿 已清空积压音频缓冲');
    }
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

  /// 异步读取音频数据（阻塞发生在后台 isolate，主事件循环保持自由）
  ///
  /// 返回实际读取的样本数，失败返回 -1
  Future<int> readAsync(Pointer<Float> buffer, int samples) async {
    if (!_isInitialized || !_isCapturing || _stream == null) {
      return -1;
    }

    final args = (_stream!.address, buffer.address, samples * sizeOf<Float>());
    final pending = Isolate.run(() => _blockingRead(args));
    _pendingRead = pending;
    final errorCode = await pending;
    if (identical(_pendingRead, pending)) {
      _pendingRead = null;
    }

    if (errorCode != 0) {
      _lastError = 'pa_simple_read 失败 (code=$errorCode)';
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
    // 后台读取在飞时不能立刻 free stream，等它返回后再清理
    final pending = _pendingRead;
    if (pending != null) {
      pending.whenComplete(_cleanup);
    } else {
      _cleanup();
    }
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
    if (_bufferAttr != null) {
      calloc.free(_bufferAttr!);
      _bufferAttr = null;
    }
    _isInitialized = false;
    _isCapturing = false;
  }
}
