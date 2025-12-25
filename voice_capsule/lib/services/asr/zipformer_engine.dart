import 'dart:convert';
import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';

import '../../ffi/sherpa_ffi.dart';
import '../../ffi/sherpa_onnx_bindings.dart';
import 'asr_engine.dart';

/// Zipformer 流式 ASR 引擎
///
/// 使用 Sherpa-onnx Zipformer 模型进行流式语音识别。
/// 支持零拷贝音频接口，直接接收 Pointer<Float>。
///
/// 特点:
/// - 边听边识别，实时输出
/// - 极低延迟 (<200ms)
/// - 内置 VAD 端点检测
class ZipformerEngine implements ASREngine {
  Pointer<SherpaOnnxOnlineRecognizer>? _recognizer;
  Pointer<SherpaOnnxOnlineStream>? _stream;
  bool _isInitialized = false;
  ASRError _lastError = ASRError.none;
  DynamicLibrary? _lib;

  /// 当前使用的模型类型 (用于热切换判断)
  bool _useInt8Model = true;

  /// 是否启用调试日志
  final bool enableDebugLog;

  /// 创建 ZipformerEngine 实例
  ///
  /// [enableDebugLog] 是否启用调试日志输出 (默认 false)
  ZipformerEngine({this.enableDebugLog = false});

  @override
  ASREngineType get engineType => ASREngineType.zipformer;

  @override
  bool get isInitialized => _isInitialized;

  @override
  ASRError get lastError => _lastError;

  /// 当前使用的是否为 int8 模型
  bool get useInt8Model => _useInt8Model;

  /// 在模型目录中查找指定类型的模型文件
  String? _findModelFile(String modelDir, String prefix,
      {required bool useInt8}) {
    final dir = Directory(modelDir);
    try {
      for (final entity in dir.listSync()) {
        if (entity is File) {
          final name = entity.path.split('/').last;
          if (name.startsWith(prefix) && name.endsWith('.onnx')) {
            final isInt8File = name.contains('.int8.');
            if (useInt8 == isInt8File) {
              return entity.path;
            }
          }
        }
      }
      // 如果未找到指定版本，尝试回退到任意版本
      for (final entity in dir.listSync()) {
        if (entity is File) {
          final name = entity.path.split('/').last;
          if (name.startsWith(prefix) && name.endsWith('.onnx')) {
            if (enableDebugLog) {
              // ignore: avoid_print
              print(
                  '[ZipformerEngine] ⚠️ 未找到 ${useInt8 ? "int8" : "标准"} 版本的 $prefix，使用: $name');
            }
            return entity.path;
          }
        }
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  @override
  Future<ASRError> initialize(ASRConfig config) async {
    if (_isInitialized) {
      return ASRError.none;
    }

    if (config is! ZipformerConfig) {
      _lastError = ASRError.invalidConfig;
      return _lastError;
    }

    // 1. 检查模型目录存在
    final modelDir = Directory(config.modelDir);
    if (!modelDir.existsSync()) {
      _lastError = ASRError.modelNotFound;
      return _lastError;
    }

    // 2. 查找模型文件
    _useInt8Model = config.useInt8Model;
    final encoderPath =
        _findModelFile(config.modelDir, 'encoder', useInt8: config.useInt8Model);
    final decoderPath =
        _findModelFile(config.modelDir, 'decoder', useInt8: config.useInt8Model);
    final joinerPath =
        _findModelFile(config.modelDir, 'joiner', useInt8: config.useInt8Model);
    final tokensPath = '${config.modelDir}/tokens.txt';

    if (enableDebugLog) {
      // ignore: avoid_print
      print('[ZipformerEngine] 使用模型版本: ${config.useInt8Model ? "int8" : "标准"}');
      // ignore: avoid_print
      print('[ZipformerEngine] encoder: $encoderPath');
      // ignore: avoid_print
      print('[ZipformerEngine] decoder: $decoderPath');
      // ignore: avoid_print
      print('[ZipformerEngine] joiner: $joinerPath');
    }

    if (encoderPath == null || decoderPath == null || joinerPath == null) {
      _lastError = ASRError.modelFileMissing;
      return _lastError;
    }
    if (!File(tokensPath).existsSync()) {
      _lastError = ASRError.modelFileMissing;
      return _lastError;
    }

    // 3. 加载动态库
    try {
      _lib = loadSherpaLibrary();
      SherpaOnnxBindings.init(_lib!);
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[ZipformerEngine] ✅ 动态库加载并初始化成功');
      }
    } catch (e) {
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[ZipformerEngine] ❌ 动态库加载失败: $e');
      }
      _lastError = ASRError.libraryLoadFailed;
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
        _lastError = ASRError.recognizerCreateFailed;
        return _lastError;
      }

      // 6. 创建流
      _stream = SherpaOnnxBindings.createOnlineStream(_recognizer!);

      if (_stream == null || _stream == nullptr) {
        SherpaOnnxBindings.destroyOnlineRecognizer(_recognizer!);
        _recognizer = null;
        _lastError = ASRError.streamCreateFailed;
        return _lastError;
      }

      _isInitialized = true;
      _lastError = ASRError.none;
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[ZipformerEngine] ✅ 识别器初始化成功');
      }
      return ASRError.none;
    } catch (e) {
      _freeConfigStrings(c);
      calloc.free(c);
      _lastError = ASRError.recognizerCreateFailed;
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

  @override
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n) {
    if (!_isInitialized || _stream == null) return;
    SherpaOnnxBindings.onlineStreamAcceptWaveform(_stream!, sampleRate, samples, n);
  }

  @override
  void decode() {
    if (!_isInitialized || _recognizer == null || _stream == null) return;
    SherpaOnnxBindings.decodeOnlineStream(_recognizer!, _stream!);
  }

  @override
  bool isReady() {
    if (!_isInitialized || _recognizer == null || _stream == null) return false;
    final result =
        SherpaOnnxBindings.isOnlineStreamReady(_recognizer!, _stream!);
    return result == 1;
  }

  @override
  ASRResult getResult() {
    if (!_isInitialized || _recognizer == null || _stream == null) {
      return ASRResult.empty();
    }

    final jsonPtr =
        SherpaOnnxBindings.getOnlineStreamResultAsJson(_recognizer!, _stream!);

    if (jsonPtr == nullptr) {
      return ASRResult.empty();
    }

    try {
      final jsonStr = jsonPtr.toDartString();
      SherpaOnnxBindings.destroyOnlineStreamResultJson(jsonPtr);

      final parsed = jsonDecode(jsonStr) as Map<String, dynamic>;
      return ASRResult(
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
      return ASRResult.empty();
    }
  }

  @override
  bool isEndpoint() {
    if (!_isInitialized || _recognizer == null || _stream == null) return false;
    final result = SherpaOnnxBindings.isEndpoint(_recognizer!, _stream!);
    return result == 1;
  }

  @override
  void reset() {
    if (!_isInitialized || _recognizer == null || _stream == null) return;
    SherpaOnnxBindings.reset(_recognizer!, _stream!);
  }

  @override
  void inputFinished() {
    if (!_isInitialized || _stream == null) return;
    SherpaOnnxBindings.onlineStreamInputFinished(_stream!);
  }

  @override
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
