import 'dart:async';
import 'dart:ffi';

import 'audio_capture.dart';
import 'model_manager.dart';
import 'sherpa_service.dart';

/// 流水线状态枚举
enum PipelineState {
  idle,
  initializing,
  running,
  stopping,
  error,
}

/// 流水线错误类型
enum PipelineError {
  none,
  audioInitFailed,
  modelNotReady,
  recognizerFailed,
  deviceUnavailable,
}

/// 延迟统计信息 (AC5: 端到端延迟 < 200ms)
class LatencyStats {
  final int sampleCount;
  final double avgLatencyMs;
  final double maxLatencyMs;
  final int overThresholdCount;

  const LatencyStats({
    required this.sampleCount,
    required this.avgLatencyMs,
    required this.maxLatencyMs,
    required this.overThresholdCount,
  });

  factory LatencyStats.empty() => const LatencyStats(
        sampleCount: 0,
        avgLatencyMs: 0,
        maxLatencyMs: 0,
        overThresholdCount: 0,
      );

  @override
  String toString() =>
      'LatencyStats(samples: $sampleCount, avg: ${avgLatencyMs.toStringAsFixed(1)}ms, '
      'max: ${maxLatencyMs.toStringAsFixed(1)}ms, over200ms: $overThresholdCount)';
}

/// 音频-推理流水线
///
/// 将音频采集和语音识别整合为一体的流水线服务。
/// 实现零拷贝数据流: PortAudio -> Sherpa-onnx (同一内存指针)
///
/// 使用示例:
/// ```dart
/// final pipeline = AudioInferencePipeline(
///   audioCapture: audioCapture,
///   sherpaService: sherpaService,
///   modelManager: modelManager,
/// );
///
/// pipeline.resultStream.listen((text) => print('识别: $text'));
/// await pipeline.start();
/// // ... 录音中 ...
/// final finalText = await pipeline.stop();
/// await pipeline.dispose();
/// ```
class AudioInferencePipeline {
  // === 依赖注入 (通过构造函数传入，便于测试) ===
  final AudioCapture _audioCapture;
  final SherpaService _sherpaService;
  final ModelManager _modelManager;

  // === 配置选项 ===
  final bool enableDebugLog;

  // === 状态管理 ===
  final StreamController<String> _resultController =
      StreamController.broadcast();
  final StreamController<PipelineState> _stateController =
      StreamController.broadcast();
  PipelineState _state = PipelineState.idle;
  PipelineError _lastError = PipelineError.none;
  bool _stopRequested = false;
  String _lastEmittedText = ''; // 用于去重
  Completer<void>? _loopCompleter; // 跟踪循环完成状态
  bool _isDisposed = false; // M1 修复: 防止在关闭后访问 StreamController

  // AC5 延迟测量 (H1 修复)
  static const int _latencyThresholdMs = 200;
  final List<double> _latencySamples = [];
  double _maxLatencyMs = 0;

  // === 构造函数 ===
  AudioInferencePipeline({
    required AudioCapture audioCapture,
    required SherpaService sherpaService,
    required ModelManager modelManager,
    this.enableDebugLog = false,
  })  : _audioCapture = audioCapture,
        _sherpaService = sherpaService,
        _modelManager = modelManager;

  // === 公开接口 ===

  /// 识别结果流 (去重后的文本)
  Stream<String> get resultStream => _resultController.stream;

  /// 状态变化流
  Stream<PipelineState> get stateStream => _stateController.stream;

  /// 是否正在运行
  bool get isRunning => _state == PipelineState.running;

  /// 当前状态
  PipelineState get state => _state;

  /// 最近一次错误
  PipelineError get lastError => _lastError;

  /// 获取延迟统计信息 (AC5: 端到端延迟 < 200ms)
  LatencyStats get latencyStats {
    if (_latencySamples.isEmpty) {
      return LatencyStats.empty();
    }
    final sum = _latencySamples.reduce((a, b) => a + b);
    final overCount =
        _latencySamples.where((l) => l > _latencyThresholdMs).length;
    return LatencyStats(
      sampleCount: _latencySamples.length,
      avgLatencyMs: sum / _latencySamples.length,
      maxLatencyMs: _maxLatencyMs,
      overThresholdCount: overCount,
    );
  }

  /// 启动流水线
  ///
  /// 初始化音频采集和识别引擎，然后开始采集循环。
  ///
  /// 返回错误类型:
  /// - [PipelineError.none] 成功
  /// - [PipelineError.modelNotReady] 模型未就绪
  /// - [PipelineError.recognizerFailed] Sherpa 初始化失败
  /// - [PipelineError.audioInitFailed] 音频设备初始化失败
  Future<PipelineError> start() async {
    if (_state == PipelineState.running) {
      return PipelineError.none;
    }

    _setState(PipelineState.initializing);

    // AC5: 重置延迟统计
    _latencySamples.clear();
    _maxLatencyMs = 0;

    // 1. 检查模型就绪状态
    if (!_modelManager.isModelReady) {
      _setError(PipelineError.modelNotReady);
      return _lastError;
    }

    // 2. 初始化 SherpaService
    final config = SherpaConfig(
      modelDir: _modelManager.modelPath,
      numThreads: 2,
      sampleRate: 16000,
      enableEndpoint: true, // 为 Story 2-6 VAD 准备
      rule1MinTrailingSilence: 2.4,
      rule2MinTrailingSilence: 1.2,
      rule3MinUtteranceLength: 20.0,
    );
    final sherpaError = await _sherpaService.initialize(config);
    if (sherpaError != SherpaError.none) {
      _setError(PipelineError.recognizerFailed);
      return _lastError;
    }

    // 3. 启动 AudioCapture
    final audioError = await _audioCapture.start();
    if (audioError != AudioCaptureError.none) {
      _setError(PipelineError.audioInitFailed);
      return _lastError;
    }

    // 4. 更新状态并启动采集循环
    _setState(PipelineState.running);
    _startCaptureLoop(); // 不 await，后台运行
    return PipelineError.none;
  }

  /// 停止流水线
  ///
  /// 停止采集，处理剩余数据，返回最终识别结果。
  Future<String> stop() async {
    if (_state != PipelineState.running) {
      return _lastEmittedText;
    }

    _setState(PipelineState.stopping);
    _stopRequested = true;

    // M3 优化: 使用更短的轮询间隔等待循环退出
    if (_loopCompleter != null && !_loopCompleter!.isCompleted) {
      const maxWaitMs = 300;
      const pollIntervalMs = 20;
      var waitedMs = 0;
      while (!_loopCompleter!.isCompleted && waitedMs < maxWaitMs) {
        await Future.delayed(const Duration(milliseconds: pollIntervalMs));
        waitedMs += pollIntervalMs;
      }
    }

    // 获取最终识别结果
    _sherpaService.inputFinished();
    while (_sherpaService.isReady()) {
      _sherpaService.decode();
    }
    final finalResult = _sherpaService.getResult();

    // 停止音频采集
    await _audioCapture.stop();

    // 重置 Sherpa 流状态 (保留模型，只清空缓冲区)
    _sherpaService.reset();

    // 重置状态
    _stopRequested = false;
    _lastEmittedText = '';
    _loopCompleter = null;
    _setState(PipelineState.idle);

    return finalResult.text;
  }

  /// 释放所有资源
  Future<void> dispose() async {
    // M1 修复: 标记已释放，防止后续访问 StreamController
    _isDisposed = true;

    // 1. 如果正在运行或正在停止，先确保停止
    if (_state == PipelineState.running || _state == PipelineState.stopping) {
      _stopRequested = true;
      // M3 优化: 使用更短的轮询间隔
      if (_loopCompleter != null && !_loopCompleter!.isCompleted) {
        const maxWaitMs = 300;
        const pollIntervalMs = 20;
        var waitedMs = 0;
        while (!_loopCompleter!.isCompleted && waitedMs < maxWaitMs) {
          await Future.delayed(const Duration(milliseconds: pollIntervalMs));
          waitedMs += pollIntervalMs;
        }
      }
      await _audioCapture.stop();
    }

    // 2. 关闭 StreamController
    await _resultController.close();
    await _stateController.close();

    // 3. 释放原生资源
    _audioCapture.dispose();
    _sherpaService.dispose();

    // 4. 清理状态
    _state = PipelineState.idle;
    _loopCompleter = null;
    _latencySamples.clear();
    _maxLatencyMs = 0;
  }

  // === 私有方法 ===

  /// 启动采集-推理循环
  Future<void> _startCaptureLoop() async {
    _loopCompleter = Completer<void>();
    final stopwatch = Stopwatch();
    const targetDurationMs = 100;

    while (!_stopRequested && _state == PipelineState.running) {
      stopwatch.reset();
      stopwatch.start();

      await _processSingleChunk();

      // 提前检查停止标志
      if (_stopRequested || _state != PipelineState.running) break;

      stopwatch.stop();

      // 性能监控: 记录超过阈值的情况
      if (enableDebugLog && stopwatch.elapsedMilliseconds > 20) {
        // ignore: avoid_print
        print('[Pipeline] 处理耗时: ${stopwatch.elapsedMilliseconds}ms');
      }

      // 可中断的延迟: 每 10ms 检查一次停止标志
      final elapsedMs = stopwatch.elapsedMilliseconds;
      if (elapsedMs < targetDurationMs) {
        final remainingMs = targetDurationMs - elapsedMs;
        await _interruptibleDelay(remainingMs);
      }
    }

    // 循环结束，标记完成
    if (!_loopCompleter!.isCompleted) {
      _loopCompleter!.complete();
    }
  }

  /// 可中断的延迟，每 10ms 检查一次停止标志
  Future<void> _interruptibleDelay(int totalMs) async {
    const checkIntervalMs = 10;
    var remainingMs = totalMs;

    while (remainingMs > 0 && !_stopRequested && _state == PipelineState.running) {
      final delayMs = remainingMs > checkIntervalMs ? checkIntervalMs : remainingMs;
      await Future.delayed(Duration(milliseconds: delayMs));
      remainingMs -= delayMs;
    }
  }

  /// 处理单个音频块
  Future<void> _processSingleChunk() async {
    // M1 修复: 如果已释放，直接返回
    if (_isDisposed) return;

    // AC5 延迟测量: 记录音频采集开始时间
    final chunkStartTime = DateTime.now();

    // 零拷贝: 直接使用 AudioCapture 的内部缓冲区
    final buffer = _audioCapture.buffer;
    final samplesRead = _audioCapture.read(buffer, AudioConfig.framesPerBuffer);

    // 错误检查: read() 返回 -1 表示错误
    if (samplesRead == -1) {
      final error = _audioCapture.lastReadError;
      if (error == AudioCaptureError.deviceUnavailable) {
        _setError(PipelineError.deviceUnavailable);
        _stopRequested = true; // 触发循环退出
      }
      return;
    }

    if (samplesRead > 0) {
      // 同一指针传给 Sherpa (零拷贝)
      _sherpaService.acceptWaveform(
          AudioConfig.sampleRate, buffer, samplesRead);

      // 解码并获取结果 (仅当有足够数据时)
      while (_sherpaService.isReady()) {
        _sherpaService.decode();
      }

      final result = _sherpaService.getResult();

      // 去重: 只在文本变化时发送事件
      if (result.text.isNotEmpty && result.text != _lastEmittedText) {
        // AC5 延迟测量: 计算端到端延迟 (音频采集到结果输出)
        final latencyMs = DateTime.now().difference(chunkStartTime).inMilliseconds.toDouble();
        _latencySamples.add(latencyMs);
        if (latencyMs > _maxLatencyMs) {
          _maxLatencyMs = latencyMs;
        }
        if (enableDebugLog && latencyMs > _latencyThresholdMs) {
          // ignore: avoid_print
          print('[Pipeline] ⚠️ 延迟超标: ${latencyMs.toStringAsFixed(1)}ms > ${_latencyThresholdMs}ms');
        }

        _lastEmittedText = result.text;
        // M1 修复: 检查 StreamController 是否已关闭
        if (!_isDisposed && !_resultController.isClosed) {
          _resultController.add(result.text);
        }
      }
    }
  }

  /// 更新状态并发送事件
  void _setState(PipelineState newState) {
    if (_state != newState) {
      _state = newState;
      // M1 修复: 检查 StreamController 是否已关闭
      if (!_isDisposed && !_stateController.isClosed) {
        _stateController.add(newState);
      }
    }
  }

  /// 设置错误状态
  void _setError(PipelineError error) {
    _lastError = error;
    _setState(PipelineState.error);
  }
}
