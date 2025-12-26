import 'dart:async';

import '../constants/settings_constants.dart';
import 'asr/asr_engine.dart';
import 'asr/asr_engine_factory.dart';
import 'asr/zipformer_engine.dart';
import 'audio_capture.dart';
import 'model_manager.dart';
import 'settings_service.dart';

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

/// VAD 端点事件 (Story 2-6)
class EndpointEvent {
  /// 最终识别文本
  final String finalText;

  /// 是否由 VAD 自动触发 (true: VAD, false: 手动 stop)
  final bool isVadTriggered;

  /// 端点触发前的识别时长 (毫秒)
  final int durationMs;

  /// 延迟统计
  final LatencyStats latencyStats;

  /// Story 3-7: 是否由设备断开触发
  final bool isDeviceLost;

  const EndpointEvent({
    required this.finalText,
    required this.isVadTriggered,
    required this.durationMs,
    required this.latencyStats,
    this.isDeviceLost = false,
  });

  @override
  String toString() =>
      'EndpointEvent(text: "$finalText", vad: $isVadTriggered, duration: ${durationMs}ms, deviceLost: $isDeviceLost)';
}

/// VAD 配置 (Story 2-6)
class VadConfig {
  /// 是否启用 VAD 自动停止
  final bool autoStopOnEndpoint;

  /// 端点触发后是否自动重置流状态 (用于连续识别)
  final bool autoReset;

  /// 自定义 Rule 2 静音阈值 (秒)，null 表示使用 SherpaConfig 默认值
  /// 注意: 此值在 start() 时传递给 Sherpa，运行时修改需重启 Pipeline
  final double? silenceThresholdSec;

  const VadConfig({
    this.autoStopOnEndpoint = true,
    this.autoReset = false,
    this.silenceThresholdSec,
  });

  /// 默认配置: 自动停止，不自动重置
  factory VadConfig.defaultConfig() => const VadConfig();

  /// 连续识别配置: 不停止，自动重置
  factory VadConfig.continuous() => const VadConfig(
        autoStopOnEndpoint: false,
        autoReset: true,
      );
}

/// 音频-推理流水线
///
/// 将音频采集和语音识别整合为一体的流水线服务。
/// 实现零拷贝数据流: PortAudio -> ASREngine (同一内存指针)
///
/// 使用示例:
/// ```dart
/// final pipeline = AudioInferencePipeline(
///   audioCapture: audioCapture,
///   asrEngine: ZipformerEngine(),
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
  // === 常量定义 ===
  /// 默认 Rule2 静音阈值 (秒) - 与 ZipformerConfig 默认值保持一致
  static const double kDefaultRule2Silence = 1.2;
  // === 依赖注入 (通过构造函数传入，便于测试) ===
  final AudioCapture _audioCapture;
  ASREngine _asrEngine; // 改为 ASREngine 抽象接口
  final ModelManager _modelManager;

  // === 配置选项 ===
  final bool enableDebugLog;

  // === 状态管理 ===
  final StreamController<String> _resultController =
      StreamController.broadcast();
  final StreamController<PipelineState> _stateController =
      StreamController.broadcast();
  final StreamController<EndpointEvent> _endpointController =
      StreamController.broadcast(); // Story 2-6: VAD 端点事件流
  PipelineState _state = PipelineState.idle;
  PipelineError _lastError = PipelineError.none;
  bool _stopRequested = false;
  String _lastEmittedText = ''; // 用于去重
  Completer<void>? _loopCompleter; // 跟踪循环完成状态
  bool _isDisposed = false; // M1 修复: 防止在关闭后访问 StreamController

  // Story 2-6: VAD 相关状态
  VadConfig _vadConfig = VadConfig.defaultConfig();
  DateTime? _recordingStartTime;
  bool _vadTriggeredStop = false; // 防止 VAD 和 stop() 发送重复事件

  // AC5 延迟测量 (H1 修复)
  static const int _latencyThresholdMs = 200;
  final List<double> _latencySamples = [];
  double _maxLatencyMs = 0;

  // === 构造函数 ===
  AudioInferencePipeline({
    required AudioCapture audioCapture,
    required ASREngine asrEngine,
    required ModelManager modelManager,
    this.enableDebugLog = false,
    VadConfig? vadConfig, // Story 2-6: 可选 VAD 配置
  })  : _audioCapture = audioCapture,
        _asrEngine = asrEngine,
        _modelManager = modelManager {
    if (vadConfig != null) {
      _vadConfig = vadConfig;
    }
  }

  // === 公开接口 ===

  /// 识别结果流 (去重后的文本)
  Stream<String> get resultStream => _resultController.stream;

  /// 状态变化流
  Stream<PipelineState> get stateStream => _stateController.stream;

  /// Story 2-6: VAD 端点事件流
  Stream<EndpointEvent> get endpointStream => _endpointController.stream;

  /// 是否正在运行
  bool get isRunning => _state == PipelineState.running;

  /// 当前状态
  PipelineState get state => _state;

  /// 最近一次错误
  PipelineError get lastError => _lastError;

  /// Story 3-7: 获取更详细的 ASR 错误 (AC9: 显示具体原因)
  ASRError get lastASRError => _asrEngine.lastError;

  /// Story 2-6: 当前 VAD 配置
  VadConfig get vadConfig => _vadConfig;

  /// Story 2-6: 设置 VAD 配置 (仅在 idle 状态有效)
  ///
  /// 返回 true 表示设置成功，返回 false 表示当前状态不允许修改。
  /// 注意: 如果 Pipeline 正在运行，配置将不会生效，需要先调用 stop()。
  bool setVadConfig(VadConfig config) {
    if (_state != PipelineState.idle) {
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[Pipeline] ⚠️ setVadConfig 失败: 当前状态为 $_state，需要 idle 状态');
      }
      return false;
    }
    _vadConfig = config;
    return true;
  }

  /// 热切换模型版本 (Zipformer int8/standard)
  ///
  /// 注意：由于 onnxruntime 的限制，运行时切换模型需要重启应用。
  /// 此方法仅保存配置，不进行实际切换。
  ///
  /// 返回 true 表示配置已保存（需要重启生效），false 表示失败
  Future<bool> switchModelType(ModelType modelType) async {
    // 配置已在 SettingsService 中保存，这里只返回成功
    // 实际切换会在下次应用启动时生效
    return true;
  }

  /// Story 2-7: 切换 ASR 引擎 (Zipformer ↔ SenseVoice)
  ///
  /// 注意：由于 onnxruntime 的限制，切换引擎需要销毁并重建 Pipeline。
  /// 此操作会停止当前录音，释放旧引擎资源，然后创建新引擎。
  ///
  /// [newEngine] 新的 ASR 引擎实例
  ///
  /// 返回 [PipelineError.none] 表示成功
  Future<PipelineError> switchEngine(ASREngine newEngine) async {
    // 1. 如果正在运行，先停止
    if (_state == PipelineState.running) {
      await stop();
    }

    // 2. 释放旧引擎资源 (但不关闭 StreamController)
    _asrEngine.dispose();

    // 3. 替换为新引擎
    _asrEngine = newEngine;

    // 4. 重置状态
    _lastError = PipelineError.none;
    _lastEmittedText = '';

    if (enableDebugLog) {
      // ignore: avoid_print
      print('[Pipeline] 🔄 引擎已切换为: ${newEngine.engineType}');
    }

    return PipelineError.none;
  }

  /// Story 2-7: 获取当前引擎类型
  ASREngineType get currentEngineType => _asrEngine.engineType;

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

    // Story 2-6: 重置 VAD 状态
    _recordingStartTime = DateTime.now();
    _vadTriggeredStop = false;

    // 1. 检查当前引擎的模型就绪状态
    final engineType = _asrEngine.engineType == ASREngineType.zipformer
        ? EngineType.zipformer
        : EngineType.sensevoice;
    if (!_modelManager.isEngineReady(engineType)) {
      _setError(PipelineError.modelNotReady);
      return _lastError;
    }

    // 2. 初始化 ASREngine (使用 VadConfig 中的静音阈值和 SettingsService 中的模型类型)
    final silenceThreshold =
        _vadConfig.silenceThresholdSec ?? kDefaultRule2Silence;
    final useInt8 = SettingsService.instance.isInitialized
        ? SettingsService.instance.modelType == ModelType.int8
        : true; // 默认使用 int8

    // 根据引擎类型创建配置
    final ASRConfig config;
    if (_asrEngine.engineType == ASREngineType.zipformer) {
      config = ZipformerConfig(
        modelDir: _modelManager.getModelPathForEngine(EngineType.zipformer),
        useInt8Model: useInt8,
        numThreads: 2,
        sampleRate: 16000,
        enableEndpoint: true, // Story 2-6: VAD 端点检测
        rule1MinTrailingSilence: 2.4,
        rule2MinTrailingSilence: silenceThreshold,
        rule3MinUtteranceLength: 20.0,
      );
    } else {
      // SenseVoice 配置
      config = SenseVoiceConfig(
        modelDir: _modelManager.getModelPathForEngine(EngineType.sensevoice),
        vadModelPath: _modelManager.vadModelFilePath,
      );
    }

    final asrError = await _asrEngine.initialize(config);
    if (asrError != ASRError.none) {
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
    _asrEngine.inputFinished();
    while (_asrEngine.isReady()) {
      _asrEngine.decode();
    }
    final finalResult = _asrEngine.getResult();

    // Story 2-6: 发送手动停止事件 (仅当不是 VAD 触发时)
    if (!_vadTriggeredStop && !_isDisposed && !_endpointController.isClosed) {
      final durationMs = _recordingStartTime != null
          ? DateTime.now().difference(_recordingStartTime!).inMilliseconds
          : 0;
      final event = EndpointEvent(
        finalText: finalResult.text,
        isVadTriggered: false,
        durationMs: durationMs,
        latencyStats: latencyStats,
      );
      _endpointController.add(event);
    }

    // 停止音频采集
    await _audioCapture.stop();

    // 重置 ASR 流状态 (保留模型，只清空缓冲区)
    _asrEngine.reset();

    // 重置状态
    _stopRequested = false;
    _lastEmittedText = '';
    _loopCompleter = null;
    _vadTriggeredStop = false; // Story 2-6: 重置标志
    _recordingStartTime = null; // Story 2-6: 清空录音开始时间
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
    await _endpointController.close(); // Story 2-6: 关闭端点事件流

    // 3. 释放原生资源
    _audioCapture.dispose();
    _asrEngine.dispose();

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

    // Story 2-6: VAD 自动停止时的清理逻辑
    if (_vadTriggeredStop && _state == PipelineState.running) {
      await _audioCapture.stop();
      _asrEngine.reset();
      _stopRequested = false;
      _lastEmittedText = '';
      _vadTriggeredStop = false;
      _recordingStartTime = null;
      _setState(PipelineState.idle);
    }
  }

  /// 可中断的延迟，每 10ms 检查一次停止标志
  Future<void> _interruptibleDelay(int totalMs) async {
    const checkIntervalMs = 10;
    var remainingMs = totalMs;

    while (
        remainingMs > 0 && !_stopRequested && _state == PipelineState.running) {
      final delayMs =
          remainingMs > checkIntervalMs ? checkIntervalMs : remainingMs;
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
        // Story 3-7: 设备丢失时发送 EndpointEvent 并保存已识别文本
        _handleDeviceLost();
        _setError(PipelineError.deviceUnavailable);
        _stopRequested = true; // 触发循环退出
      }
      return;
    }

    if (samplesRead > 0) {
      // 同一指针传给 ASREngine (零拷贝)
      _asrEngine.acceptWaveform(
          AudioConfig.sampleRate, buffer, samplesRead);

      // 解码并获取结果 (仅当有足够数据时)
      while (_asrEngine.isReady()) {
        _asrEngine.decode();
      }

      final result = _asrEngine.getResult();

      // 去重: 只在文本变化时发送事件
      if (result.text.isNotEmpty && result.text != _lastEmittedText) {
        // AC5 延迟测量: 计算端到端延迟 (音频采集到结果输出)
        final latencyMs =
            DateTime.now().difference(chunkStartTime).inMilliseconds.toDouble();
        _latencySamples.add(latencyMs);
        if (latencyMs > _maxLatencyMs) {
          _maxLatencyMs = latencyMs;
        }
        if (enableDebugLog && latencyMs > _latencyThresholdMs) {
          // ignore: avoid_print
          print(
              '[Pipeline] ⚠️ 延迟超标: ${latencyMs.toStringAsFixed(1)}ms > ${_latencyThresholdMs}ms');
        }

        _lastEmittedText = result.text;
        // M1 修复: 检查 StreamController 是否已关闭
        if (!_isDisposed && !_resultController.isClosed) {
          _resultController.add(result.text);
        }
      }

      // Story 2-6: VAD 端点检测
      final isEndpointDetected = _asrEngine.isEndpoint();
      // 调试：只在有识别结果或端点检测时打印
      if (enableDebugLog && (result.text.isNotEmpty || isEndpointDetected)) {
        // ignore: avoid_print
        print('[Pipeline] 识别: "${result.text}", endpoint: $isEndpointDetected');
      }
      if (isEndpointDetected && !_vadTriggeredStop) {
        await _handleEndpoint();
      }
    }
  }

  /// Story 3-7: 处理设备丢失事件
  /// 当 PortAudio 检测到设备不可用时调用
  /// 发送带有 isDeviceLost=true 的 EndpointEvent，保存当前识别的文本
  void _handleDeviceLost() {
    if (_isDisposed || _endpointController.isClosed) return;

    // 1. 尝试获取当前已识别的文本
    String preservedText = _lastEmittedText;

    // 尝试从 ASREngine 获取最新结果
    try {
      _asrEngine.inputFinished();
      while (_asrEngine.isReady()) {
        _asrEngine.decode();
      }
      final result = _asrEngine.getResult();
      if (result.text.isNotEmpty) {
        preservedText = result.text;
      }
    } catch (e) {
      // 忽略解码错误，使用已有的文本
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[Pipeline] ⚠️ _handleDeviceLost 获取文本失败: $e');
      }
    }

    // 2. 计算录音时长
    final durationMs = _recordingStartTime != null
        ? DateTime.now().difference(_recordingStartTime!).inMilliseconds
        : 0;

    // 3. 发送设备丢失事件 (AC13: 保存已识别文本)
    final event = EndpointEvent(
      finalText: preservedText,
      isVadTriggered: false,
      durationMs: durationMs,
      latencyStats: latencyStats,
      isDeviceLost: true,
    );
    _endpointController.add(event);

    if (enableDebugLog) {
      // ignore: avoid_print
      print('[Pipeline] 🔌 设备丢失，已保存文本: "$preservedText"');
    }
  }

  /// Story 2-6: 处理 VAD 端点检测
  Future<void> _handleEndpoint() async {
    try {
      // PTT 累积模式：不调用 inputFinished()，只获取当前结果
      // inputFinished() 会使引擎进入"结束"状态，导致后续音频无法累积
      final isPttAccumulateMode =
          !_vadConfig.autoStopOnEndpoint && !_vadConfig.autoReset;

      if (!isPttAccumulateMode) {
        // 非 PTT 累积模式：调用 inputFinished() 确保最终解码
        _asrEngine.inputFinished();
        while (_asrEngine.isReady()) {
          _asrEngine.decode();
        }
      }

      final finalResult = _asrEngine.getResult();

      // 2. 计算录音时长
      final durationMs = _recordingStartTime != null
          ? DateTime.now().difference(_recordingStartTime!).inMilliseconds
          : 0;

      // 3. 创建并发送端点事件
      final event = EndpointEvent(
        finalText: finalResult.text,
        isVadTriggered: true,
        durationMs: durationMs,
        latencyStats: latencyStats,
      );
      if (!_isDisposed && !_endpointController.isClosed) {
        _endpointController.add(event);
      }

      if (enableDebugLog) {
        // ignore: avoid_print
        print('[Pipeline] 🎯 VAD 端点 (PTT累积=$isPttAccumulateMode): "${finalResult.text}"');
      }

      // 4. 根据配置决定后续行为
      if (_vadConfig.autoStopOnEndpoint) {
        _vadTriggeredStop = true; // 标记 VAD 触发，防止 stop() 重复发送事件
        _stopRequested = true;
      } else if (_vadConfig.autoReset) {
        _asrEngine.reset();
        _lastEmittedText = '';
        _recordingStartTime = DateTime.now();
      }
      // PTT 累积模式 (!autoStopOnEndpoint && !autoReset)：什么都不做，继续累积
    } catch (e) {
      // FFI 层或其他异常处理
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[Pipeline] ⚠️ _handleEndpoint 异常: $e');
      }
      // 即使出错也尝试停止，避免用户无感知
      _stopRequested = true;
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
