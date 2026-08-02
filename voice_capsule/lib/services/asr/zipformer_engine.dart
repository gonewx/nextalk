import 'dart:convert';
import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';

import '../../ffi/sherpa_ffi.dart';
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

  /// 初始化时使用的采样率 (供 finalizeUtterance 生成静音 padding 用)
  int _sampleRate = 16000;

  /// 标记上次 _recreateStream() 失败，需要在下一次发话前重试流创建
  bool _needsStreamRecovery = false;

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
    _sampleRate = config.sampleRate;
    final encoderPath = _findModelFile(config.modelDir, 'encoder',
        useInt8: config.useInt8Model);
    final decoderPath = _findModelFile(config.modelDir, 'decoder',
        useInt8: config.useInt8Model);
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
      c.ref.hr.dictDir = ''.toNativeUtf8(); // unused but required
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
    calloc.free(c.ref.hr.dictDir);
    calloc.free(c.ref.hr.lexicon);
    calloc.free(c.ref.hr.ruleFsts);
  }

  @override
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n) {
    if (!_isInitialized || _stream == null) return;
    SherpaOnnxBindings.onlineStreamAcceptWaveform(
        _stream!, sampleRate, samples, n);
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

  /// 收尾时补的静音时长 (秒)。
  ///
  /// 流式 transducer 的 `IsReady()` 判定是
  /// `已处理帧 + ChunkSize < 就绪帧`，不检查输入是否结束，所以末尾不足一个
  /// chunk 的尾帧永远进不了解码循环 —— 这正是"最后几个字不上屏"的根因。
  /// 补一段静音把真实尾音顶过 chunk 边界，尾帧才会被解码。
  ///
  /// 取值 0.6s：chunk 窗口约 32 帧 (约 320ms)，0.3s≈30 帧仍不足一窗，余量太小；
  /// 0.6s 经真机实测可稳定解出尾字。
  static const double _tailPaddingSeconds = 0.6;

  @override
  ASRResult finalizeUtterance() {
    if (!_isInitialized || _recognizer == null || _stream == null) {
      return ASRResult.empty();
    }

    // 1. 补静音 padding，把尾音顶过 chunk 边界后跑干解码
    final padCount = (_sampleRate * _tailPaddingSeconds).round();
    final pad = calloc<Float>(padCount);
    try {
      // calloc 已置零，直接作为静音使用
      SherpaOnnxBindings.onlineStreamAcceptWaveform(
          _stream!, _sampleRate, pad, padCount);
      while (isReady()) {
        decode();
      }
    } finally {
      calloc.free(pad);
    }

    // 2. 取最终结果 (此时尾帧已解码)
    final result = getResult();

    // 3. 重建 OnlineStream 隔离会话。
    //    不能依赖 reset(): 上游 Reset() 只推进 start_frame_index_，
    //    明确不清特征提取器，未消费的残留帧会被下一次发话当作开头解出来。
    _recreateStream();

    return result;
  }

  /// 销毁并重建 OnlineStream，确保下一次发话不携带上一次的残留帧。
  ///
  /// 重建失败时不把引擎留在"静默失效"状态：`initialize()` 会因
  /// `_isInitialized` 早退而不再重建流，若此处放任 `_stream` 为 null，
  /// 所有音频接口都会判空早退 —— 用户表现为按键无反应且无任何报错，
  /// 只能重启应用。因此失败时标记 `_needsStreamRecovery`，由
  /// [ensureStreamReady] 在下一次发话开始前重试。
  void _recreateStream() {
    if (_recognizer == null || _recognizer == nullptr) return;

    if (_stream != null && _stream != nullptr) {
      SherpaOnnxBindings.destroyOnlineStream(_stream!);
    }
    _stream = null;

    final fresh = SherpaOnnxBindings.createOnlineStream(_recognizer!);
    if (fresh == nullptr) {
      // 保持 _stream 为 null 避免野指针，但标记待恢复，下次发话前重试
      _lastError = ASRError.streamCreateFailed;
      _needsStreamRecovery = true;
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[ZipformerEngine] ❌ 重建 OnlineStream 失败，已标记待恢复');
      }
      return;
    }
    _needsStreamRecovery = false;
    _stream = fresh;
  }

  @override
  bool ensureStreamReady() {
    if (!_isInitialized || _recognizer == null || _recognizer == nullptr) {
      return false;
    }
    if (_stream != null && _stream != nullptr) {
      return true; // 流健康，无需恢复
    }

    // 上一次收尾时重建失败，这里重试一次
    final fresh = SherpaOnnxBindings.createOnlineStream(_recognizer!);
    if (fresh == nullptr) {
      _lastError = ASRError.streamCreateFailed;
      _needsStreamRecovery = true;
      return false;
    }
    _stream = fresh;
    _needsStreamRecovery = false;
    _lastError = ASRError.none;
    if (enableDebugLog) {
      // ignore: avoid_print
      print('[ZipformerEngine] ✅ OnlineStream 已恢复');
    }
    return true;
  }

  @Deprecated('收尾请使用 finalizeUtterance()，它对流式引擎才真正有效')
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
