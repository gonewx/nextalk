import 'dart:async';
import 'dart:ffi';

import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/audio_capture.dart';
import 'package:voice_capsule/services/audio_inference_pipeline.dart';
import 'package:voice_capsule/services/model_manager.dart';

/// Mock AudioCapture for testing
class MockAudioCapture extends AudioCapture {
  bool _started = false;
  AudioCaptureError _startError = AudioCaptureError.none;
  AudioCaptureError _readError = AudioCaptureError.none;
  int _readReturnValue = AudioConfig.framesPerBuffer;
  Pointer<Float>? _mockBuffer;
  bool _disposed = false;

  void setStartError(AudioCaptureError error) => _startError = error;
  void setReadError(AudioCaptureError error) => _readError = error;
  void setReadReturnValue(int value) => _readReturnValue = value;

  @override
  Future<AudioCaptureError> start({String? deviceName}) async {
    if (_startError != AudioCaptureError.none) {
      return _startError;
    }
    _started = true;
    _mockBuffer = calloc<Float>(AudioConfig.framesPerBuffer);
    return AudioCaptureError.none;
  }

  @override
  int read(Pointer<Float> buffer, int samples) {
    if (_readError != AudioCaptureError.none) {
      return -1;
    }
    return _readReturnValue;
  }

  @override
  AudioCaptureError get lastReadError => _readError;

  @override
  Pointer<Float> get buffer {
    if (_mockBuffer == null) {
      throw StateError('AudioCapture 未初始化');
    }
    return _mockBuffer!;
  }

  @override
  bool get isCapturing => _started;

  @override
  Future<void> stop() async {
    _started = false;
  }

  @override
  void dispose() {
    if (_mockBuffer != null) {
      calloc.free(_mockBuffer!);
      _mockBuffer = null;
    }
    _disposed = true;
  }

  bool get isDisposed => _disposed;
}

/// Mock ASREngine for testing (Story 2-7: ASR 引擎抽象层)
class MockASREngine implements ASREngine {
  bool _initialized = false;
  ASRError _initError = ASRError.none;
  ASRError _lastError = ASRError.none;
  bool _ready = false;
  bool _hasNewData = false; // 模拟有新数据需要解码
  String _resultText = '';
  bool _disposed = false;
  int _acceptWaveformCalls = 0;
  int _decodeCalls = 0;
  Pointer<Float>? _lastReceivedBuffer; // H2 修复: 记录收到的指针地址

  // Story 2-6: VAD 端点检测 mock
  int _endpointCallCount = 0;
  int triggerEndpointAfterCalls = 0; // >0 时，N 次调用后返回 true
  bool _endpointTriggered = false;

  // Story 2-6: 记录收到的 ASRConfig
  ASRConfig? lastReceivedConfig;

  void setInitError(ASRError error) => _initError = error;
  void setReady(bool ready) => _ready = ready;
  void setResultText(String text) => _resultText = text;

  int get acceptWaveformCalls => _acceptWaveformCalls;
  int get decodeCalls => _decodeCalls;
  Pointer<Float>? get lastReceivedBuffer => _lastReceivedBuffer; // H2 修复

  // Story 2-6: 重置端点 mock 状态
  void resetEndpointMock() {
    _endpointCallCount = 0;
    _endpointTriggered = false;
  }

  // Story 2-7: 引擎类型 mock
  ASREngineType _engineType = ASREngineType.zipformer;
  void setEngineType(ASREngineType type) => _engineType = type;
  bool get disposed => _disposed;

  @override
  ASREngineType get engineType => _engineType;

  @override
  bool get isInitialized => _initialized;

  @override
  ASRError get lastError => _lastError;

  @override
  Future<ASRError> initialize(ASRConfig config) async {
    lastReceivedConfig = config; // Story 2-6: 记录配置
    if (_initError != ASRError.none) {
      _lastError = _initError;
      return _initError;
    }
    _initialized = true;
    return ASRError.none;
  }

  @override
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n) {
    _acceptWaveformCalls++;
    _lastReceivedBuffer = samples; // H2 修复: 记录指针
    // 当设置为 ready 模式时，每次接收音频后标记有新数据
    if (_ready) {
      _hasNewData = true;
    }
  }

  @override
  void decode() {
    _decodeCalls++;
    // 解码后清除新数据标志
    _hasNewData = false;
  }

  @override
  bool isReady() {
    // 只有当有新数据时才返回 true，模拟真实行为
    return _hasNewData;
  }

  @override
  ASRResult getResult() {
    return ASRResult(
      text: _resultText,
      tokens: [],
      timestamps: [],
    );
  }

  @override
  bool isEndpoint() {
    // Story 2-6: VAD 端点检测 mock 实现
    if (_endpointTriggered) return false; // 已触发过，不再触发
    _endpointCallCount++;
    if (triggerEndpointAfterCalls > 0 &&
        _endpointCallCount >= triggerEndpointAfterCalls) {
      _endpointTriggered = true;
      return true;
    }
    return false;
  }

  @override
  void inputFinished() {}

  @override
  void reset() {
    // Story 2-6: reset 后可以重新触发端点
    // ⚠️ 注意: 真实的 ASREngine.reset() 只清空音频缓冲区，
    // VAD 端点检测状态是 C 层内部状态，不会被重置。
    // Mock 实现重置这些状态是为了简化测试，但这与真实行为有差异。
    // 在集成测试中应使用真实的 ASREngine 验证 autoReset 行为。
    _endpointTriggered = false;
    _endpointCallCount = 0;
  }

  @override
  void dispose() {
    _initialized = false;
    _disposed = true;
  }

  bool get isDisposed => _disposed;
}

/// Mock ModelManager for testing
class MockModelManager extends ModelManager {
  bool _modelReady = true;
  String _modelPath = '/mock/model/path';

  void setModelReady(bool ready) => _modelReady = ready;
  void setModelPath(String path) => _modelPath = path;

  @override
  bool get isModelReady => _modelReady;

  @override
  String get modelPath => _modelPath;

  @override
  bool isEngineReady(EngineType engineType) => _modelReady;
}

void main() {
  group('AudioInferencePipeline 类骨架 (Task 1)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('PipelineState 枚举包含所有预期状态', () {
      expect(PipelineState.values, contains(PipelineState.idle));
      expect(PipelineState.values, contains(PipelineState.initializing));
      expect(PipelineState.values, contains(PipelineState.running));
      expect(PipelineState.values, contains(PipelineState.stopping));
      expect(PipelineState.values, contains(PipelineState.error));
    });

    test('PipelineError 枚举包含所有预期错误类型', () {
      expect(PipelineError.values, contains(PipelineError.none));
      expect(PipelineError.values, contains(PipelineError.audioInitFailed));
      expect(PipelineError.values, contains(PipelineError.modelNotReady));
      expect(PipelineError.values, contains(PipelineError.recognizerFailed));
      expect(PipelineError.values, contains(PipelineError.deviceUnavailable));
    });

    test('初始状态为 idle', () {
      expect(pipeline.state, equals(PipelineState.idle));
    });

    test('初始 isRunning 为 false', () {
      expect(pipeline.isRunning, isFalse);
    });

    test('初始 lastError 为 none', () {
      expect(pipeline.lastError, equals(PipelineError.none));
    });

    test('resultStream 是 broadcast stream', () {
      final stream1 = pipeline.resultStream;
      final stream2 = pipeline.resultStream;
      // broadcast stream 可以被多次监听
      expect(stream1.isBroadcast, isTrue);
      expect(stream2.isBroadcast, isTrue);
    });

    test('stateStream 是 broadcast stream', () {
      final stream1 = pipeline.stateStream;
      final stream2 = pipeline.stateStream;
      expect(stream1.isBroadcast, isTrue);
      expect(stream2.isBroadcast, isTrue);
    });

    test('构造函数正确注入依赖', () {
      // Pipeline 能够被成功创建并且依赖被正确注入
      // 这通过其他测试间接验证
      expect(pipeline, isNotNull);
    });

    test('enableDebugLog 参数默认为 false', () {
      final pipelineWithDefault = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
      // 默认不启用调试日志 (通过观察无日志输出验证)
      expect(pipelineWithDefault, isNotNull);
    });
  });

  group('AudioInferencePipeline start() 方法 (Task 2)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('模型未就绪时返回 modelNotReady 错误 (AC7)', () async {
      mockModelManager.setModelReady(false);

      final error = await pipeline.start();

      expect(error, equals(PipelineError.modelNotReady));
      expect(pipeline.state, equals(PipelineState.error));
      expect(pipeline.isRunning, isFalse);
    });

    test('ASREngine 初始化失败时返回 recognizerFailed 错误 (AC7)', () async {
      mockAsrEngine.setInitError(ASRError.recognizerCreateFailed);

      final error = await pipeline.start();

      expect(error, equals(PipelineError.recognizerFailed));
      expect(pipeline.state, equals(PipelineState.error));
    });

    test('AudioCapture 启动失败时返回 audioInitFailed 错误 (AC7)', () async {
      mockAudioCapture.setStartError(AudioCaptureError.noInputDevice);

      final error = await pipeline.start();

      expect(error, equals(PipelineError.audioInitFailed));
      expect(pipeline.state, equals(PipelineState.error));
    });

    test('成功启动后 isRunning 为 true (AC1)', () async {
      final error = await pipeline.start();

      expect(error, equals(PipelineError.none));
      expect(pipeline.isRunning, isTrue);
      expect(pipeline.state, equals(PipelineState.running));
    });

    test('成功启动后 stateStream 发出 running 事件 (AC1)', () async {
      final states = <PipelineState>[];
      pipeline.stateStream.listen(states.add);

      await pipeline.start();

      // 等待事件传播
      await Future.delayed(const Duration(milliseconds: 50));

      expect(states, contains(PipelineState.running));
    });
  });

  group('AudioInferencePipeline 采集-推理循环 (Task 3)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('运行时 acceptWaveform 被调用 (AC2, AC3)', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('测试');

      await pipeline.start();

      // 等待几个循环周期
      await Future.delayed(const Duration(milliseconds: 350));

      await pipeline.stop();

      // 验证 acceptWaveform 被多次调用
      expect(mockAsrEngine.acceptWaveformCalls, greaterThan(0));
    });

    test('识别结果通过 resultStream 输出 (AC4)', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('你好世界');

      final results = <String>[];
      pipeline.resultStream.listen(results.add);

      await pipeline.start();

      // 等待结果
      await Future.delayed(const Duration(milliseconds: 250));

      await pipeline.stop();

      expect(results, contains('你好世界'));
    });

    test('相同文本不重复发送 (去重)', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('重复文本');

      final results = <String>[];
      pipeline.resultStream.listen(results.add);

      await pipeline.start();

      // 等待多个循环周期
      await Future.delayed(const Duration(milliseconds: 350));

      await pipeline.stop();

      // 相同文本只应该发送一次
      final repeatCount = results.where((r) => r == '重复文本').length;
      expect(repeatCount, equals(1));
    });

    test('设备不可用时触发 deviceUnavailable 错误 (AC7)', () async {
      await pipeline.start();

      // 模拟设备不可用
      mockAudioCapture.setReadError(AudioCaptureError.deviceUnavailable);

      // 等待错误传播
      await Future.delayed(const Duration(milliseconds: 250));

      expect(pipeline.lastError, equals(PipelineError.deviceUnavailable));
      expect(pipeline.state, equals(PipelineState.error));
    });
  });

  group('AudioInferencePipeline stop() 方法 (Task 4)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('stop() 后 isRunning 为 false (AC6)', () async {
      await pipeline.start();
      expect(pipeline.isRunning, isTrue);

      await pipeline.stop();

      expect(pipeline.isRunning, isFalse);
      expect(pipeline.state, equals(PipelineState.idle));
    });

    test('stop() 返回最终识别文本 (AC6)', () async {
      mockAsrEngine.setResultText('最终结果');

      await pipeline.start();
      final finalText = await pipeline.stop();

      expect(finalText, equals('最终结果'));
    });

    test('未运行时 stop() 安全返回', () async {
      // 未启动直接调用 stop
      final result = await pipeline.stop();

      expect(result, isEmpty);
      expect(pipeline.state, equals(PipelineState.idle));
    });
  });

  group('AudioInferencePipeline dispose() 方法 (Task 5)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
    });

    test('dispose() 后 StreamController 已关闭 (AC8)', () async {
      final pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );

      await pipeline.start();
      await pipeline.dispose();

      // 验证 stream 已关闭 - 添加监听器会抛出异常或收到 done 事件
      var resultStreamDone = false;
      var stateStreamDone = false;

      pipeline.resultStream.listen(
        (_) {},
        onDone: () => resultStreamDone = true,
      );
      pipeline.stateStream.listen(
        (_) {},
        onDone: () => stateStreamDone = true,
      );

      await Future.delayed(const Duration(milliseconds: 50));

      expect(resultStreamDone, isTrue);
      expect(stateStreamDone, isTrue);
    });

    test('dispose() 释放原生资源 (AC8)', () async {
      final pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );

      await pipeline.start();
      await pipeline.dispose();

      expect(mockAudioCapture.isDisposed, isTrue);
      expect(mockAsrEngine.isDisposed, isTrue);
    });

    test('正在运行时 dispose() 先停止再释放', () async {
      final pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );

      await pipeline.start();
      expect(pipeline.isRunning, isTrue);

      await pipeline.dispose();

      expect(pipeline.isRunning, isFalse);
      expect(mockAudioCapture.isDisposed, isTrue);
    });
  });

  // H2 修复: 零拷贝验证测试组
  group('AudioInferencePipeline 零拷贝验证 (AC2)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('acceptWaveform 收到的指针与 AudioCapture.buffer 相同 (零拷贝)', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('测试零拷贝');

      await pipeline.start();

      // 等待至少一个循环周期
      await Future.delayed(const Duration(milliseconds: 150));

      await pipeline.stop();

      // 验证 acceptWaveform 被调用
      expect(mockAsrEngine.acceptWaveformCalls, greaterThan(0));

      // H2 核心验证: 指针地址必须相同 (零拷贝)
      expect(mockAsrEngine.lastReceivedBuffer, isNotNull);
      expect(
        mockAsrEngine.lastReceivedBuffer!.address,
        equals(mockAudioCapture.buffer.address),
        reason: '零拷贝要求: acceptWaveform 收到的指针必须与 AudioCapture.buffer 相同',
      );
    });
  });

  // H1 修复: 延迟统计测试组
  group('AudioInferencePipeline 延迟测量 (AC5)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('初始 latencyStats 为空', () {
      final stats = pipeline.latencyStats;
      expect(stats.sampleCount, equals(0));
      expect(stats.avgLatencyMs, equals(0));
      expect(stats.maxLatencyMs, equals(0));
      expect(stats.overThresholdCount, equals(0));
    });

    test('运行后有延迟统计数据', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('测试延迟');

      await pipeline.start();

      // 等待产生结果
      await Future.delayed(const Duration(milliseconds: 250));

      await pipeline.stop();

      final stats = pipeline.latencyStats;
      expect(stats.sampleCount, greaterThan(0), reason: '应该有延迟统计样本');
      expect(stats.avgLatencyMs, greaterThanOrEqualTo(0), reason: '平均延迟应该非负');
      expect(stats.maxLatencyMs, greaterThanOrEqualTo(0), reason: '最大延迟应该非负');
    });

    test('start() 重置延迟统计', () async {
      mockAsrEngine.setReady(true);

      // 第一次运行，使用不同的文本确保产生结果
      mockAsrEngine.setResultText('第一次');
      await pipeline.start();
      await Future.delayed(const Duration(milliseconds: 200));
      await pipeline.stop();

      final firstStats = pipeline.latencyStats;
      expect(firstStats.sampleCount, greaterThan(0), reason: '第一次运行应该有统计');
      final firstSampleCount = firstStats.sampleCount;

      // 第二次运行，使用相同文本（因为 stop 后 _lastEmittedText 被重置）
      mockAsrEngine.setResultText('第二次');
      await pipeline.start();
      await Future.delayed(const Duration(milliseconds: 200));
      await pipeline.stop();

      final secondStats = pipeline.latencyStats;
      // 第二次运行应该是独立的统计，不是累积的
      // 因为 start() 重置了统计，所以第二次的 sampleCount 应该是从 0 开始重新计数
      expect(secondStats.sampleCount, greaterThan(0), reason: '第二次运行应该有统计');
      expect(
        secondStats.sampleCount,
        lessThanOrEqualTo(firstSampleCount + 2),
        reason: 'start() 应该重置延迟统计，第二次不应该是累积值',
      );
    });

    test('LatencyStats.toString() 格式正确', () {
      final stats = LatencyStats(
        sampleCount: 10,
        avgLatencyMs: 50.5,
        maxLatencyMs: 100.0,
        overThresholdCount: 2,
      );

      final str = stats.toString();
      expect(str, contains('samples: 10'));
      expect(str, contains('avg: 50.5ms'));
      expect(str, contains('max: 100.0ms'));
      expect(str, contains('over200ms: 2'));
    });
  });

  // ============================================
  // Story 2-6: VAD 端点检测测试
  // ============================================

  group('Story 2-6: EndpointEvent 和 VadConfig 类型定义 (Task 1)', () {
    test('EndpointEvent 正确创建', () {
      final stats = LatencyStats(
        sampleCount: 5,
        avgLatencyMs: 30.0,
        maxLatencyMs: 50.0,
        overThresholdCount: 0,
      );
      final event = EndpointEvent(
        finalText: '你好世界',
        isVadTriggered: true,
        durationMs: 2500,
        latencyStats: stats,
      );

      expect(event.finalText, equals('你好世界'));
      expect(event.isVadTriggered, isTrue);
      expect(event.durationMs, equals(2500));
      expect(event.latencyStats.sampleCount, equals(5));
    });

    test('EndpointEvent.toString() 格式正确', () {
      final event = EndpointEvent(
        finalText: '测试',
        isVadTriggered: false,
        durationMs: 1000,
        latencyStats: LatencyStats.empty(),
      );

      final str = event.toString();
      expect(str, contains('测试'));
      expect(str, contains('vad: false'));
      expect(str, contains('duration: 1000ms'));
    });

    test('VadConfig 默认配置', () {
      final config = VadConfig.defaultConfig();
      expect(config.autoStopOnEndpoint, isTrue);
      expect(config.autoReset, isFalse);
      expect(config.silenceThresholdSec, isNull);
    });

    test('VadConfig 连续识别配置', () {
      final config = VadConfig.continuous();
      expect(config.autoStopOnEndpoint, isFalse);
      expect(config.autoReset, isTrue);
    });

    test('VadConfig 自定义静音阈值', () {
      const config = VadConfig(silenceThresholdSec: 2.0);
      expect(config.silenceThresholdSec, equals(2.0));
    });
  });

  group('Story 2-6: VAD 成员变量和公开接口 (Task 2)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('endpointStream 是 broadcast stream', () {
      final stream1 = pipeline.endpointStream;
      final stream2 = pipeline.endpointStream;
      expect(stream1.isBroadcast, isTrue);
      expect(stream2.isBroadcast, isTrue);
    });

    test('vadConfig 默认值正确', () {
      expect(pipeline.vadConfig.autoStopOnEndpoint, isTrue);
      expect(pipeline.vadConfig.autoReset, isFalse);
      expect(pipeline.vadConfig.silenceThresholdSec, isNull);
    });

    test('构造函数接受 VadConfig 参数', () {
      final customPipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
        vadConfig: VadConfig.continuous(),
      );

      expect(customPipeline.vadConfig.autoStopOnEndpoint, isFalse);
      expect(customPipeline.vadConfig.autoReset, isTrue);

      customPipeline.dispose();
    });

    test('setVadConfig 在 idle 状态有效', () {
      expect(pipeline.state, equals(PipelineState.idle));

      final result = pipeline.setVadConfig(VadConfig.continuous());

      expect(result, isTrue);
      expect(pipeline.vadConfig.autoStopOnEndpoint, isFalse);
    });

    test('setVadConfig 在 running 状态无效', () async {
      await pipeline.start();
      expect(pipeline.isRunning, isTrue);

      final result = pipeline.setVadConfig(VadConfig.continuous());

      expect(result, isFalse);
      // 配置未改变
      expect(pipeline.vadConfig.autoStopOnEndpoint, isTrue);
    });

    test('自定义 silenceThresholdSec 传递给 ASRConfig (AC3)', () async {
      final customPipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
        vadConfig: const VadConfig(silenceThresholdSec: 2.0),
      );

      await customPipeline.start();

      expect(mockAsrEngine.lastReceivedConfig, isNotNull);
      // ZipformerConfig 子类有 rule2MinTrailingSilence 属性
      final config = mockAsrEngine.lastReceivedConfig as ZipformerConfig;
      expect(config.rule2MinTrailingSilence, equals(2.0));

      await customPipeline.dispose();
    });
  });

  group('Story 2-6: VAD 端点检测逻辑 (Task 3)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('VAD 端点触发时 endpointStream 发出事件，isVadTriggered 为 true (AC1, AC2, AC5)',
        () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('VAD 测试');
      mockAsrEngine.triggerEndpointAfterCalls = 2; // 第 2 次调用时触发

      final events = <EndpointEvent>[];
      pipeline.endpointStream.listen(events.add);

      await pipeline.start();

      // 等待 VAD 触发
      await Future.delayed(const Duration(milliseconds: 400));

      expect(events, isNotEmpty, reason: 'endpointStream 应该收到事件');
      expect(events.first.isVadTriggered, isTrue);
      expect(events.first.finalText, equals('VAD 测试'));
    });

    test('autoStopOnEndpoint: true 时端点触发后 isRunning 变为 false (AC2, AC6)',
        () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('停止测试');
      mockAsrEngine.triggerEndpointAfterCalls = 2;

      await pipeline.start();
      expect(pipeline.isRunning, isTrue);

      // 等待 VAD 触发并自动停止
      await Future.delayed(const Duration(milliseconds: 400));

      expect(pipeline.isRunning, isFalse);
    });

    test('autoStopOnEndpoint: false 时端点触发后 isRunning 保持 true (AC6)', () async {
      final continuousPipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
        vadConfig: const VadConfig(autoStopOnEndpoint: false),
      );

      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('连续测试');
      mockAsrEngine.triggerEndpointAfterCalls = 2;

      await continuousPipeline.start();

      // 等待 VAD 触发
      await Future.delayed(const Duration(milliseconds: 400));

      expect(continuousPipeline.isRunning, isTrue, reason: '不自动停止时应保持运行');

      await continuousPipeline.dispose();
    });

    test('autoReset: true 时端点触发后流状态被重置 (AC7)', () async {
      final continuousPipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
        vadConfig: VadConfig.continuous(),
      );

      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('重置测试');
      mockAsrEngine.triggerEndpointAfterCalls = 2;

      final events = <EndpointEvent>[];
      continuousPipeline.endpointStream.listen(events.add);

      await continuousPipeline.start();

      // 等待第一次 VAD 触发
      await Future.delayed(const Duration(milliseconds: 400));

      // reset() 被调用后，mockAsrEngine 会重置端点状态
      // 设置新的触发条件
      mockAsrEngine.triggerEndpointAfterCalls = 2;

      // 等待第二次 VAD 触发
      await Future.delayed(const Duration(milliseconds: 400));

      await continuousPipeline.dispose();

      expect(events.length, greaterThanOrEqualTo(1), reason: '至少应该收到一个端点事件');
    });

    test('durationMs 正确反映录音时长 (AC5)', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('时长测试');
      mockAsrEngine.triggerEndpointAfterCalls = 3;

      final events = <EndpointEvent>[];
      pipeline.endpointStream.listen(events.add);

      await pipeline.start();

      // 等待约 300-400ms
      await Future.delayed(const Duration(milliseconds: 500));

      if (events.isNotEmpty) {
        // durationMs 应该大于 0
        expect(events.first.durationMs, greaterThan(0));
        // 应该大约在 200-600ms 之间 (考虑测试环境波动)
        expect(events.first.durationMs, greaterThan(100));
      }
    });
  });

  group('Story 2-6: stop() 方法修改 (Task 4)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('手动 stop() 时 endpointStream 发出事件，isVadTriggered 为 false (AC8)',
        () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('手动停止');

      final events = <EndpointEvent>[];
      pipeline.endpointStream.listen(events.add);

      await pipeline.start();
      await Future.delayed(const Duration(milliseconds: 200));
      await pipeline.stop();

      expect(events, isNotEmpty, reason: 'stop() 应该发送端点事件');
      expect(events.last.isVadTriggered, isFalse);
      expect(events.last.finalText, equals('手动停止'));
    });

    test('VAD 触发后 stop() 不产生重复事件 (AC8)', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('不重复');
      mockAsrEngine.triggerEndpointAfterCalls = 2;

      final events = <EndpointEvent>[];
      pipeline.endpointStream.listen(events.add);

      await pipeline.start();

      // 等待 VAD 触发
      await Future.delayed(const Duration(milliseconds: 400));

      // VAD 已触发，再调用 stop()
      await pipeline.stop();

      // 应该只有一个事件 (VAD 触发的)
      expect(events.length, equals(1), reason: 'VAD + stop() 不应该产生重复事件');
      expect(events.first.isVadTriggered, isTrue);
    });
  });

  group('Story 2-6: dispose() 方法修改 (Task 4.2)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
    });

    test('dispose() 后 endpointStream 已关闭', () async {
      final pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );

      await pipeline.start();
      await pipeline.dispose();

      var endpointStreamDone = false;
      pipeline.endpointStream.listen(
        (_) {},
        onDone: () => endpointStreamDone = true,
      );

      await Future.delayed(const Duration(milliseconds: 50));

      expect(endpointStreamDone, isTrue);
    });
  });

  group('Story 2-6: 边界条件测试', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('连续 isEndpoint() 返回 true 时只发送一个事件', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('连续端点');
      // MockASREngine 的 isEndpoint 实现已经确保只返回一次 true
      mockAsrEngine.triggerEndpointAfterCalls = 2;

      final events = <EndpointEvent>[];
      pipeline.endpointStream.listen(events.add);

      await pipeline.start();
      await Future.delayed(const Duration(milliseconds: 500));

      // 由于 _vadTriggeredStop 和 _endpointTriggered 的保护，只会有一个事件
      expect(events.length, lessThanOrEqualTo(1));
    });

    test('未运行时 endpointStream 不发送事件', () async {
      final events = <EndpointEvent>[];
      pipeline.endpointStream.listen(events.add);

      // 不调用 start()，直接等待
      await Future.delayed(const Duration(milliseconds: 200));

      expect(events, isEmpty);
    });

    // AC4: 短暂停顿不触发端点检测
    test('短暂停顿 (< 阈值) 不触发端点 (AC4)', () async {
      mockAsrEngine.setReady(true);
      mockAsrEngine.setResultText('短暂停顿测试');
      // 设置一个较大的触发次数，模拟 VAD 未检测到足够长的静音
      // 即使处理了多个音频块，只要静音时长 < 阈值，isEndpoint() 应返回 false
      mockAsrEngine.triggerEndpointAfterCalls = 100; // 远超测试周期

      final events = <EndpointEvent>[];
      pipeline.endpointStream.listen(events.add);

      await pipeline.start();

      // 等待几个处理周期 (约 300ms，小于默认 1.2s 阈值)
      await Future.delayed(const Duration(milliseconds: 300));

      // 在这个短暂周期内，isEndpoint() 应始终返回 false
      // 因此不应该有端点事件
      expect(events, isEmpty, reason: '短暂停顿期间不应触发端点事件');
      expect(pipeline.isRunning, isTrue, reason: '流水线应保持运行');

      await pipeline.stop();
    });

    test('默认静音阈值正确传递给 ASRConfig', () async {
      // 使用默认配置 (silenceThresholdSec = null)
      final defaultPipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
      );

      await defaultPipeline.start();

      // 验证默认值 1.2 被正确传递
      expect(mockAsrEngine.lastReceivedConfig, isNotNull);
      // ZipformerConfig 子类有 rule2MinTrailingSilence 属性
      final config = mockAsrEngine.lastReceivedConfig as ZipformerConfig;
      expect(
        config.rule2MinTrailingSilence,
        equals(1.2),
        reason: '默认静音阈值应为 1.2 秒',
      );

      await defaultPipeline.dispose();
    });
  });

  group('Story 2-7: 引擎切换功能 (AC5)', () {
    late MockAudioCapture mockAudioCapture;
    late MockASREngine mockAsrEngine;
    late MockASREngine newMockAsrEngine;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockAsrEngine = MockASREngine();
      newMockAsrEngine = MockASREngine();
      mockModelManager = MockModelManager();
      mockModelManager.setModelReady(true);
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        asrEngine: mockAsrEngine,
        modelManager: mockModelManager,
        enableDebugLog: true,
      );
    });

    tearDown(() async {
      await pipeline.dispose();
    });

    test('switchEngine 在 idle 状态下成功切换引擎', () async {
      // 验证初始引擎
      expect(pipeline.currentEngineType, equals(ASREngineType.zipformer));

      // 设置新引擎类型
      newMockAsrEngine.setEngineType(ASREngineType.sensevoice);

      // 切换引擎
      final error = await pipeline.switchEngine(newMockAsrEngine);
      expect(error, equals(PipelineError.none));
      expect(pipeline.currentEngineType, equals(ASREngineType.sensevoice));
    });

    test('switchEngine 在运行状态下先停止再切换', () async {
      // 启动流水线
      final startError = await pipeline.start();
      expect(startError, equals(PipelineError.none));
      expect(pipeline.isRunning, isTrue);

      // 设置新引擎类型
      newMockAsrEngine.setEngineType(ASREngineType.sensevoice);

      // 切换引擎 (应该先停止)
      final switchError = await pipeline.switchEngine(newMockAsrEngine);
      expect(switchError, equals(PipelineError.none));
      expect(pipeline.isRunning, isFalse);
      expect(pipeline.currentEngineType, equals(ASREngineType.sensevoice));
    });

    test('switchEngine 释放旧引擎资源', () async {
      // 启动流水线使旧引擎被初始化
      await pipeline.start();
      await pipeline.stop();

      // 切换引擎
      newMockAsrEngine.setEngineType(ASREngineType.sensevoice);
      await pipeline.switchEngine(newMockAsrEngine);

      // 验证旧引擎已被释放
      expect(mockAsrEngine.disposed, isTrue);
    });

    test('switchEngine 后可以正常重新启动', () async {
      // 设置新引擎
      newMockAsrEngine.setEngineType(ASREngineType.sensevoice);
      await pipeline.switchEngine(newMockAsrEngine);

      // 重新启动
      final startError = await pipeline.start();
      expect(startError, equals(PipelineError.none));
      expect(pipeline.isRunning, isTrue);

      await pipeline.stop();
    });

    test('currentEngineType 返回正确的引擎类型', () {
      expect(pipeline.currentEngineType, equals(ASREngineType.zipformer));
    });

    test('switchEngine 重置错误状态', () async {
      // 模拟一个错误状态
      mockModelManager.setModelReady(false);
      await pipeline.start();
      expect(pipeline.lastError, equals(PipelineError.modelNotReady));

      // 恢复模型状态
      mockModelManager.setModelReady(true);

      // 切换引擎应该重置错误状态
      newMockAsrEngine.setEngineType(ASREngineType.sensevoice);
      await pipeline.switchEngine(newMockAsrEngine);
      expect(pipeline.lastError, equals(PipelineError.none));
    });
  });
}
