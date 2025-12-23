import 'dart:convert';
import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';

import '../ffi/sherpa_ffi.dart';
import '../ffi/sherpa_onnx_bindings.dart';

/// Sherpa 服务配置
class SherpaConfig {
  /// 模型目录路径
  final String modelDir;

  /// 线程数 (默认 2，建议不超过 CPU 核心数)
  final int numThreads;

  /// 采样率 (必须与 AudioConfig 一致: 16000)
  final int sampleRate;

  /// 特征维度 (默认 80)
  final int featureDim;

  /// 是否启用端点检测
  final bool enableEndpoint;

  /// 规则1: 短停顿阈值 (秒) - 解码前的最小尾部静音
  final double rule1MinTrailingSilence;

  /// 规则2: 长停顿阈值 (秒) - 解码后的最小尾部静音
  final double rule2MinTrailingSilence;

  /// 规则3: 最小语句长度 (秒) - 触发端点的最短语句时长
  final double rule3MinUtteranceLength;

  /// 解码方法 (greedy_search 或 modified_beam_search)
  final String decodingMethod;

  /// provider (cpu)
  final String provider;

  const SherpaConfig({
    required this.modelDir,
    this.numThreads = 2,
    this.sampleRate = 16000,
    this.featureDim = 80,
    this.enableEndpoint = true,
    this.rule1MinTrailingSilence = 2.4,
    this.rule2MinTrailingSilence = 1.2,
    this.rule3MinUtteranceLength = 20.0,
    this.decodingMethod = 'greedy_search',
    this.provider = 'cpu',
  });

  @override
  String toString() {
    return 'SherpaConfig(modelDir: $modelDir, numThreads: $numThreads, '
        'sampleRate: $sampleRate, enableEndpoint: $enableEndpoint)';
  }
}

/// Sherpa 服务错误类型
enum SherpaError {
  /// 无错误
  none,

  /// 库加载失败
  libraryLoadFailed,

  /// 模型目录不存在
  modelNotFound,

  /// tokens.txt 不存在
  tokensNotFound,

  /// encoder 模型不存在
  encoderNotFound,

  /// decoder 模型不存在
  decoderNotFound,

  /// joiner 模型不存在
  joinerNotFound,

  /// 创建识别器失败
  recognizerCreateFailed,

  /// 创建流失败
  streamCreateFailed,

  /// 服务未初始化
  notInitialized,
}

/// Sherpa 识别结果
class SherpaResult {
  /// 识别文本
  final String text;

  /// token 列表
  final List<String> tokens;

  /// 时间戳列表
  final List<double> timestamps;

  const SherpaResult({
    required this.text,
    required this.tokens,
    required this.timestamps,
  });

  factory SherpaResult.empty() => const SherpaResult(
        text: '',
        tokens: [],
        timestamps: [],
      );

  @override
  String toString() => 'SherpaResult(text: $text)';
}

/// Sherpa 语音识别服务
///
/// 使用 Sherpa-onnx 进行流式语音识别。
/// 支持零拷贝音频接口，直接接收 Pointer<Float>。
class SherpaService {
  Pointer<SherpaOnnxOnlineRecognizer>? _recognizer;
  Pointer<SherpaOnnxOnlineStream>? _stream;
  bool _isInitialized = false;
  SherpaError _lastError = SherpaError.none;
  DynamicLibrary? _lib;

  /// 是否启用调试日志
  final bool enableDebugLog;

  /// 创建 SherpaService 实例
  ///
  /// [enableDebugLog] 是否启用调试日志输出 (默认 false)
  SherpaService({this.enableDebugLog = false});

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 最近一次错误
  SherpaError get lastError => _lastError;

  /// 在模型目录中查找指定类型的模型文件
  ///
  /// [modelDir] 模型目录路径
  /// [prefix] 文件前缀 (encoder, decoder, joiner)
  ///
  /// 返回找到的文件路径，未找到返回 null
  String? _findModelFile(String modelDir, String prefix) {
    final dir = Directory(modelDir);
    try {
      for (final entity in dir.listSync()) {
        if (entity is File) {
          final name = entity.path.split('/').last;
          if (name.startsWith(prefix) && name.endsWith('.onnx')) {
            return entity.path;
          }
        }
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  /// 初始化识别器
  ///
  /// [config] 识别器配置
  ///
  /// 返回错误类型，[SherpaError.none] 表示成功
  Future<SherpaError> initialize(SherpaConfig config) async {
    if (_isInitialized) {
      return SherpaError.none;
    }

    // 1. 检查模型目录存在
    final modelDir = Directory(config.modelDir);
    if (!modelDir.existsSync()) {
      _lastError = SherpaError.modelNotFound;
      return _lastError;
    }

    // 2. 查找模型文件 (支持不同版本的模型)
    final encoderPath = _findModelFile(config.modelDir, 'encoder');
    final decoderPath = _findModelFile(config.modelDir, 'decoder');
    final joinerPath = _findModelFile(config.modelDir, 'joiner');
    final tokensPath = '${config.modelDir}/tokens.txt';

    if (encoderPath == null) {
      _lastError = SherpaError.encoderNotFound;
      return _lastError;
    }
    if (decoderPath == null) {
      _lastError = SherpaError.decoderNotFound;
      return _lastError;
    }
    if (joinerPath == null) {
      _lastError = SherpaError.joinerNotFound;
      return _lastError;
    }
    if (!File(tokensPath).existsSync()) {
      _lastError = SherpaError.tokensNotFound;
      return _lastError;
    }

    // 3. 加载动态库
    try {
      _lib = loadSherpaLibrary();
      SherpaOnnxBindings.init(_lib!);
      // ignore: avoid_print
      print('[SherpaService] ✅ 动态库加载并初始化成功');
    } catch (e) {
      // ignore: avoid_print
      print('[SherpaService] ❌ 动态库加载失败: $e');
      _lastError = SherpaError.libraryLoadFailed;
      return _lastError;
    }

    // 4. 创建识别器配置
    final c = calloc<SherpaOnnxOnlineRecognizerConfig>();

    try {
      // 特征配置
      c.ref.feat.sampleRate = config.sampleRate;
      c.ref.feat.featureDim = config.featureDim;

      // Transducer 模型配置
      c.ref.model.transducer.encoder = encoderPath.toNativeUtf8();
      c.ref.model.transducer.decoder = decoderPath.toNativeUtf8();
      c.ref.model.transducer.joiner = joinerPath.toNativeUtf8();

      // 其他模型配置 (空字符串)
      c.ref.model.paraformer.encoder = ''.toNativeUtf8();
      c.ref.model.paraformer.decoder = ''.toNativeUtf8();
      c.ref.model.zipformer2Ctc.model = ''.toNativeUtf8();
      c.ref.model.nemoCtc.model = ''.toNativeUtf8();
      c.ref.model.toneCtc.model = ''.toNativeUtf8();

      // 通用模型配置
      c.ref.model.tokens = tokensPath.toNativeUtf8();
      c.ref.model.numThreads = config.numThreads;
      c.ref.model.provider = config.provider.toNativeUtf8();
      c.ref.model.debug = 0;
      c.ref.model.modelType = ''.toNativeUtf8();
      c.ref.model.modelingUnit = ''.toNativeUtf8();
      c.ref.model.bpeVocab = ''.toNativeUtf8();
      c.ref.model.tokensBuf = nullptr;
      c.ref.model.tokensBufSize = 0;

      // 解码配置
      c.ref.decodingMethod = config.decodingMethod.toNativeUtf8();
      c.ref.maxActivePaths = 4;
      c.ref.enableEndpoint = config.enableEndpoint ? 1 : 0;
      c.ref.rule1MinTrailingSilence = config.rule1MinTrailingSilence;
      c.ref.rule2MinTrailingSilence = config.rule2MinTrailingSilence;
      c.ref.rule3MinUtteranceLength = config.rule3MinUtteranceLength;

      // Hotwords 配置
      c.ref.hotwordsFile = ''.toNativeUtf8();
      c.ref.hotwordsScore = 1.5;
      c.ref.hotwordsBuf = nullptr;
      c.ref.hotwordsBufSize = 0;

      // CTC FST 解码器配置
      c.ref.ctcFstDecoderConfig.graph = ''.toNativeUtf8();
      c.ref.ctcFstDecoderConfig.maxActive = 3000;

      // 其他配置
      c.ref.ruleFsts = ''.toNativeUtf8();
      c.ref.ruleFars = ''.toNativeUtf8();
      c.ref.blankPenalty = 0.0;

      // 同音替换配置
      c.ref.hr.lexicon = ''.toNativeUtf8();
      c.ref.hr.ruleFsts = ''.toNativeUtf8();

      // 5. 创建识别器
      _recognizer = SherpaOnnxBindings.createOnlineRecognizer(c);

      // 释放配置中分配的字符串内存
      _freeConfigStrings(c);
      calloc.free(c);

      if (_recognizer == null || _recognizer == nullptr) {
        _lastError = SherpaError.recognizerCreateFailed;
        return _lastError;
      }

      // 6. 创建流
      _stream = SherpaOnnxBindings.createOnlineStream(_recognizer!);

      if (_stream == null || _stream == nullptr) {
        SherpaOnnxBindings.destroyOnlineRecognizer(_recognizer!);
        _recognizer = null;
        _lastError = SherpaError.streamCreateFailed;
        return _lastError;
      }

      _isInitialized = true;
      _lastError = SherpaError.none;
      if (enableDebugLog) {
        // ignore: avoid_print
        print('Sherpa recognizer initialized');
      }
      return SherpaError.none;
    } catch (e) {
      _freeConfigStrings(c);
      calloc.free(c);
      _lastError = SherpaError.recognizerCreateFailed;
      return _lastError;
    }
  }

  /// 释放配置中分配的字符串内存
  void _freeConfigStrings(Pointer<SherpaOnnxOnlineRecognizerConfig> c) {
    calloc.free(c.ref.model.transducer.encoder);
    calloc.free(c.ref.model.transducer.decoder);
    calloc.free(c.ref.model.transducer.joiner);
    calloc.free(c.ref.model.paraformer.encoder);
    calloc.free(c.ref.model.paraformer.decoder);
    calloc.free(c.ref.model.zipformer2Ctc.model);
    calloc.free(c.ref.model.nemoCtc.model);
    calloc.free(c.ref.model.toneCtc.model);
    calloc.free(c.ref.model.tokens);
    calloc.free(c.ref.model.provider);
    calloc.free(c.ref.model.modelType);
    calloc.free(c.ref.model.modelingUnit);
    calloc.free(c.ref.model.bpeVocab);
    calloc.free(c.ref.decodingMethod);
    calloc.free(c.ref.hotwordsFile);
    calloc.free(c.ref.ctcFstDecoderConfig.graph);
    calloc.free(c.ref.ruleFsts);
    calloc.free(c.ref.ruleFars);
    calloc.free(c.ref.hr.lexicon);
    calloc.free(c.ref.hr.ruleFsts);
  }

  /// 送入音频数据 (零拷贝)
  ///
  /// [sampleRate] 采样率 (应为 16000)
  /// [samples] 音频样本指针 (Float32, 值域 [-1.0, 1.0])
  /// [n] 样本数量
  ///
  /// 注意: 此方法直接使用传入的指针，不进行内存分配或拷贝。
  /// 调用者需确保指针在调用期间有效。
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n) {
    if (!_isInitialized || _stream == null) return;
    SherpaOnnxBindings.onlineStreamAcceptWaveform(_stream!, sampleRate, samples, n);
  }

  /// 执行解码
  void decode() {
    if (!_isInitialized || _recognizer == null || _stream == null) return;
    SherpaOnnxBindings.decodeOnlineStream(_recognizer!, _stream!);
  }

  /// 检查是否准备好解码
  bool isReady() {
    if (!_isInitialized || _recognizer == null || _stream == null) return false;
    final result = SherpaOnnxBindings.isOnlineStreamReady(_recognizer!, _stream!);
    return result == 1;
  }

  /// 获取当前识别结果
  SherpaResult getResult() {
    if (!_isInitialized || _recognizer == null || _stream == null) {
      return SherpaResult.empty();
    }

    final jsonPtr = SherpaOnnxBindings.getOnlineStreamResultAsJson(_recognizer!, _stream!);

    if (jsonPtr == nullptr) {
      return SherpaResult.empty();
    }

    try {
      final jsonStr = jsonPtr.toDartString();
      SherpaOnnxBindings.destroyOnlineStreamResultJson(jsonPtr);

      final parsed = jsonDecode(jsonStr) as Map<String, dynamic>;
      return SherpaResult(
        text: parsed['text'] as String? ?? '',
        tokens: (parsed['tokens'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList() ??
            [],
        timestamps: (parsed['timestamps'] as List<dynamic>?)
                ?.map((e) => (e as num).toDouble())
                .toList() ??
            [],
      );
    } catch (e) {
      return SherpaResult.empty();
    }
  }

  /// 检查是否检测到端点
  bool isEndpoint() {
    if (!_isInitialized || _recognizer == null || _stream == null) return false;
    final result = SherpaOnnxBindings.isEndpoint(_recognizer!, _stream!);
    return result == 1;
  }

  /// 重置识别状态 (清空缓冲区，保留模型)
  void reset() {
    if (!_isInitialized || _recognizer == null || _stream == null) return;
    SherpaOnnxBindings.reset(_recognizer!, _stream!);
  }

  /// 标记输入结束
  void inputFinished() {
    if (!_isInitialized || _stream == null) return;
    SherpaOnnxBindings.onlineStreamInputFinished(_stream!);
  }

  /// 释放资源
  void dispose() {
    if (_stream != null && _stream != nullptr) {
      SherpaOnnxBindings.destroyOnlineStream(_stream!);
      _stream = null;
    }

    if (_recognizer != null && _recognizer != nullptr) {
      SherpaOnnxBindings.destroyOnlineRecognizer(_recognizer!);
      _recognizer = null;
    }

    _isInitialized = false;
    _lib = null;
  }
}
