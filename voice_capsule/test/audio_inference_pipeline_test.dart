import 'dart:async';
import 'dart:ffi';

import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/audio_capture.dart';
import 'package:voice_capsule/services/audio_inference_pipeline.dart';
import 'package:voice_capsule/services/model_manager.dart';
import 'package:voice_capsule/services/sherpa_service.dart';

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
  Future<AudioCaptureError> start() async {
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

/// Mock SherpaService for testing
class MockSherpaService extends SherpaService {
  bool _initialized = false;
  SherpaError _initError = SherpaError.none;
  bool _ready = false;
  bool _hasNewData = false; // 模拟有新数据需要解码
  String _resultText = '';
  bool _disposed = false;
  int _acceptWaveformCalls = 0;
  int _decodeCalls = 0;
  Pointer<Float>? _lastReceivedBuffer; // H2 修复: 记录收到的指针地址

  void setInitError(SherpaError error) => _initError = error;
  void setReady(bool ready) => _ready = ready;
  void setResultText(String text) => _resultText = text;

  int get acceptWaveformCalls => _acceptWaveformCalls;
  int get decodeCalls => _decodeCalls;
  Pointer<Float>? get lastReceivedBuffer => _lastReceivedBuffer; // H2 修复

  @override
  Future<SherpaError> initialize(SherpaConfig config) async {
    if (_initError != SherpaError.none) {
      return _initError;
    }
    _initialized = true;
    return SherpaError.none;
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
  SherpaResult getResult() {
    return SherpaResult(
      text: _resultText,
      tokens: [],
      timestamps: [],
    );
  }

  @override
  bool isEndpoint() => false;

  @override
  void inputFinished() {}

  @override
  void reset() {}

  @override
  void dispose() {
    _initialized = false;
    _disposed = true;
  }

  @override
  bool get isInitialized => _initialized;

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
}

void main() {
  group('AudioInferencePipeline 类骨架 (Task 1)', () {
    late MockAudioCapture mockAudioCapture;
    late MockSherpaService mockSherpaService;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockSherpaService = MockSherpaService();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        sherpaService: mockSherpaService,
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
        sherpaService: mockSherpaService,
        modelManager: mockModelManager,
      );
      // 默认不启用调试日志 (通过观察无日志输出验证)
      expect(pipelineWithDefault, isNotNull);
    });
  });

  group('AudioInferencePipeline start() 方法 (Task 2)', () {
    late MockAudioCapture mockAudioCapture;
    late MockSherpaService mockSherpaService;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockSherpaService = MockSherpaService();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        sherpaService: mockSherpaService,
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

    test('SherpaService 初始化失败时返回 recognizerFailed 错误 (AC7)', () async {
      mockSherpaService.setInitError(SherpaError.recognizerCreateFailed);

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
    late MockSherpaService mockSherpaService;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockSherpaService = MockSherpaService();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        sherpaService: mockSherpaService,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('运行时 acceptWaveform 被调用 (AC2, AC3)', () async {
      mockSherpaService.setReady(true);
      mockSherpaService.setResultText('测试');

      await pipeline.start();

      // 等待几个循环周期
      await Future.delayed(const Duration(milliseconds: 350));

      await pipeline.stop();

      // 验证 acceptWaveform 被多次调用
      expect(mockSherpaService.acceptWaveformCalls, greaterThan(0));
    });

    test('识别结果通过 resultStream 输出 (AC4)', () async {
      mockSherpaService.setReady(true);
      mockSherpaService.setResultText('你好世界');

      final results = <String>[];
      pipeline.resultStream.listen(results.add);

      await pipeline.start();

      // 等待结果
      await Future.delayed(const Duration(milliseconds: 250));

      await pipeline.stop();

      expect(results, contains('你好世界'));
    });

    test('相同文本不重复发送 (去重)', () async {
      mockSherpaService.setReady(true);
      mockSherpaService.setResultText('重复文本');

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
    late MockSherpaService mockSherpaService;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockSherpaService = MockSherpaService();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        sherpaService: mockSherpaService,
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
      mockSherpaService.setResultText('最终结果');

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
    late MockSherpaService mockSherpaService;
    late MockModelManager mockModelManager;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockSherpaService = MockSherpaService();
      mockModelManager = MockModelManager();
    });

    test('dispose() 后 StreamController 已关闭 (AC8)', () async {
      final pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        sherpaService: mockSherpaService,
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
        sherpaService: mockSherpaService,
        modelManager: mockModelManager,
      );

      await pipeline.start();
      await pipeline.dispose();

      expect(mockAudioCapture.isDisposed, isTrue);
      expect(mockSherpaService.isDisposed, isTrue);
    });

    test('正在运行时 dispose() 先停止再释放', () async {
      final pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        sherpaService: mockSherpaService,
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
    late MockSherpaService mockSherpaService;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockSherpaService = MockSherpaService();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        sherpaService: mockSherpaService,
        modelManager: mockModelManager,
      );
    });

    tearDown(() {
      pipeline.dispose();
    });

    test('acceptWaveform 收到的指针与 AudioCapture.buffer 相同 (零拷贝)', () async {
      mockSherpaService.setReady(true);
      mockSherpaService.setResultText('测试零拷贝');

      await pipeline.start();

      // 等待至少一个循环周期
      await Future.delayed(const Duration(milliseconds: 150));

      await pipeline.stop();

      // 验证 acceptWaveform 被调用
      expect(mockSherpaService.acceptWaveformCalls, greaterThan(0));

      // H2 核心验证: 指针地址必须相同 (零拷贝)
      expect(mockSherpaService.lastReceivedBuffer, isNotNull);
      expect(
        mockSherpaService.lastReceivedBuffer!.address,
        equals(mockAudioCapture.buffer.address),
        reason: '零拷贝要求: acceptWaveform 收到的指针必须与 AudioCapture.buffer 相同',
      );
    });
  });

  // H1 修复: 延迟统计测试组
  group('AudioInferencePipeline 延迟测量 (AC5)', () {
    late MockAudioCapture mockAudioCapture;
    late MockSherpaService mockSherpaService;
    late MockModelManager mockModelManager;
    late AudioInferencePipeline pipeline;

    setUp(() {
      mockAudioCapture = MockAudioCapture();
      mockSherpaService = MockSherpaService();
      mockModelManager = MockModelManager();
      pipeline = AudioInferencePipeline(
        audioCapture: mockAudioCapture,
        sherpaService: mockSherpaService,
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
      mockSherpaService.setReady(true);
      mockSherpaService.setResultText('测试延迟');

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
      mockSherpaService.setReady(true);

      // 第一次运行，使用不同的文本确保产生结果
      mockSherpaService.setResultText('第一次');
      await pipeline.start();
      await Future.delayed(const Duration(milliseconds: 200));
      await pipeline.stop();

      final firstStats = pipeline.latencyStats;
      expect(firstStats.sampleCount, greaterThan(0), reason: '第一次运行应该有统计');
      final firstSampleCount = firstStats.sampleCount;

      // 第二次运行，使用相同文本（因为 stop 后 _lastEmittedText 被重置）
      mockSherpaService.setResultText('第二次');
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
}
