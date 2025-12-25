// Copyright (c) 2025 Nextalk Project
// Story 2-7: SenseVoice 离线 ASR 引擎实现
//
// SenseVoiceEngine 使用 VAD + 离线识别的伪流式方案：
// 1. Silero VAD 检测语音活动
// 2. VAD 检测到语音段后送入 SenseVoice 识别
// 3. 识别结果通过同步接口返回

import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';

import '../../ffi/sherpa_ffi.dart';
import '../../ffi/sherpa_offline_bindings.dart';
import '../../ffi/sherpa_vad_bindings.dart';
import 'asr_engine.dart';

/// SenseVoice 离线 ASR 引擎
///
/// 使用 Silero VAD + SenseVoice 离线模型实现伪流式语音识别。
///
/// 工作流程:
/// 1. 音频数据送入 VAD 检测
/// 2. VAD 检测到语音段结束时，提取语音段
/// 3. 对语音段进行离线识别
/// 4. 返回识别结果 (含 text, lang, emotion)
///
/// 特点:
/// - 按段落输出文字，用户体验接近流式
/// - 支持语言自动检测 (zh/en/ja/ko/yue)
/// - 支持情感识别 (NEUTRAL/HAPPY/SAD/ANGRY)
/// - 支持 ITN (Inverse Text Normalization) 自动标点
class SenseVoiceEngine implements ASREngine {
  Pointer<SherpaOnnxVoiceActivityDetector>? _vad;
  Pointer<SherpaOnnxOfflineRecognizer>? _recognizer;
  bool _isInitialized = false;
  ASRError _lastError = ASRError.none;
  DynamicLibrary? _lib;

  /// 最近一次识别结果
  ASRResult _lastResult = ASRResult.empty();

  /// 是否检测到端点 (语音段结束)
  bool _hasEndpoint = false;

  /// 配置缓存
  SenseVoiceConfig? _config;

  /// 是否启用调试日志
  final bool enableDebugLog;

  /// 创建 SenseVoiceEngine 实例
  ///
  /// [enableDebugLog] 是否启用调试日志输出 (默认 false)
  SenseVoiceEngine({this.enableDebugLog = false});

  @override
  ASREngineType get engineType => ASREngineType.sensevoice;

  @override
  bool get isInitialized => _isInitialized;

  @override
  ASRError get lastError => _lastError;

  @override
  Future<ASRError> initialize(ASRConfig config) async {
    if (_isInitialized) {
      return ASRError.none;
    }

    if (config is! SenseVoiceConfig) {
      _lastError = ASRError.invalidConfig;
      return _lastError;
    }

    _config = config;

    // 1. 检查模型目录存在
    final modelDir = Directory(config.modelDir);
    if (!modelDir.existsSync()) {
      _lastError = ASRError.modelNotFound;
      return _lastError;
    }

    // 2. 检查 VAD 模型存在
    final vadModelFile = File(config.vadModelPath);
    if (!vadModelFile.existsSync()) {
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ VAD 模型不存在: ${config.vadModelPath}');
      }
      _lastError = ASRError.vadInitFailed;
      return _lastError;
    }

    // 3. 查找 SenseVoice 模型文件
    final modelPath = _findSenseVoiceModel(config.modelDir);
    final tokensPath = '${config.modelDir}/tokens.txt';

    if (modelPath == null) {
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ 未找到 SenseVoice 模型文件');
      }
      _lastError = ASRError.modelFileMissing;
      return _lastError;
    }

    if (!File(tokensPath).existsSync()) {
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ tokens.txt 不存在: $tokensPath');
      }
      _lastError = ASRError.modelFileMissing;
      return _lastError;
    }

    // 4. 加载动态库
    try {
      _lib = loadSherpaLibrary();
      SherpaOnnxOfflineBindings.init(_lib!);
      SherpaOnnxVadBindings.init(_lib!);
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ✅ 动态库加载并初始化成功');
      }
    } catch (e) {
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ 动态库加载失败: $e');
      }
      _lastError = ASRError.libraryLoadFailed;
      return _lastError;
    }

    // 5. 初始化 VAD
    final vadError = _initializeVad(config);
    if (vadError != ASRError.none) {
      return vadError;
    }

    // 6. 初始化离线识别器
    final recognizerError = _initializeRecognizer(config, modelPath, tokensPath);
    if (recognizerError != ASRError.none) {
      _destroyVad();
      return recognizerError;
    }

    _isInitialized = true;
    _lastError = ASRError.none;

    if (enableDebugLog) {
      // ignore: avoid_print
      print('[SenseVoiceEngine] ✅ SenseVoice 引擎初始化成功');
      // ignore: avoid_print
      print('[SenseVoiceEngine] 模型: $modelPath');
      // ignore: avoid_print
      print('[SenseVoiceEngine] VAD: ${config.vadModelPath}');
    }

    return ASRError.none;
  }

  /// 查找 SenseVoice 模型文件
  String? _findSenseVoiceModel(String modelDir) {
    final dir = Directory(modelDir);
    try {
      for (final entity in dir.listSync()) {
        if (entity is File) {
          final name = entity.path.split('/').last;
          // SenseVoice 模型通常名为 model.onnx 或 model.int8.onnx
          if (name == 'model.onnx' ||
              name == 'model.int8.onnx' ||
              name.contains('sense') && name.endsWith('.onnx')) {
            return entity.path;
          }
        }
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  /// 初始化 VAD
  ASRError _initializeVad(SenseVoiceConfig config) {
    final vadConfig = calloc<SherpaOnnxVadModelConfig>();

    try {
      // Silero VAD 配置
      vadConfig.ref.sileroVad.model = config.vadModelPath.toNativeUtf8();
      vadConfig.ref.sileroVad.threshold = config.vadThreshold;
      vadConfig.ref.sileroVad.minSilenceDuration = config.minSilenceDuration;
      vadConfig.ref.sileroVad.minSpeechDuration = config.minSpeechDuration;
      vadConfig.ref.sileroVad.maxSpeechDuration = config.maxSpeechDuration;
      vadConfig.ref.sileroVad.windowSize = config.vadWindowSize;

      // 通用配置
      vadConfig.ref.sampleRate = config.sampleRate;
      vadConfig.ref.numThreads = config.numThreads;
      vadConfig.ref.provider = config.provider.toNativeUtf8();
      vadConfig.ref.debug = enableDebugLog ? 1 : 0;

      // 创建 VAD (bufferSizeInSeconds = 30.0)
      _vad = SherpaOnnxVadBindings.createVoiceActivityDetector(vadConfig, 30.0);

      // 释放配置字符串
      calloc.free(vadConfig.ref.sileroVad.model);
      calloc.free(vadConfig.ref.provider);
      calloc.free(vadConfig);

      if (_vad == null || _vad == nullptr) {
        if (enableDebugLog) {
          // ignore: avoid_print
          print('[SenseVoiceEngine] ❌ VAD 创建失败');
        }
        _lastError = ASRError.vadInitFailed;
        return _lastError;
      }

      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ✅ VAD 初始化成功');
        // ignore: avoid_print
        print(
            '[SenseVoiceEngine] VAD 配置: windowSize=${config.vadWindowSize}, threshold=${config.vadThreshold}');
      }

      return ASRError.none;
    } catch (e) {
      calloc.free(vadConfig);
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ VAD 初始化异常: $e');
      }
      _lastError = ASRError.vadInitFailed;
      return _lastError;
    }
  }

  /// 初始化离线识别器
  ASRError _initializeRecognizer(
      SenseVoiceConfig config, String modelPath, String tokensPath) {
    final recognizerConfig = calloc<SherpaOnnxOfflineRecognizerConfig>();

    try {
      // 特征配置
      recognizerConfig.ref.featConfig.sampleRate = config.sampleRate;
      recognizerConfig.ref.featConfig.featureDim = 80;

      // SenseVoice 模型配置
      recognizerConfig.ref.modelConfig.senseVoice.model =
          modelPath.toNativeUtf8();
      recognizerConfig.ref.modelConfig.senseVoice.language =
          config.language.toNativeUtf8();
      recognizerConfig.ref.modelConfig.senseVoice.useItn = config.useItn ? 1 : 0;

      // 其他模型配置 (空字符串)
      recognizerConfig.ref.modelConfig.transducer.encoder = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.transducer.decoder = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.transducer.joiner = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.paraformer.model = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.nemoCtc.model = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.whisper.encoder = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.whisper.decoder = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.whisper.language = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.whisper.task = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.whisper.tailPaddings = 0;
      recognizerConfig.ref.modelConfig.tdnn.model = ''.toNativeUtf8();

      // 通用模型配置
      recognizerConfig.ref.modelConfig.tokens = tokensPath.toNativeUtf8();
      recognizerConfig.ref.modelConfig.numThreads = config.numThreads;
      recognizerConfig.ref.modelConfig.debug = enableDebugLog ? 1 : 0;
      recognizerConfig.ref.modelConfig.provider = config.provider.toNativeUtf8();
      recognizerConfig.ref.modelConfig.modelType = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.modelingUnit = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.bpeVocab = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.telespeechCtc = ''.toNativeUtf8();
      recognizerConfig.ref.modelConfig.tokensBuf = nullptr;
      recognizerConfig.ref.modelConfig.tokensBufSize = 0;

      // LM 配置
      recognizerConfig.ref.lmConfig.model = ''.toNativeUtf8();
      recognizerConfig.ref.lmConfig.scale = 1.0;

      // 解码配置
      recognizerConfig.ref.decodingMethod = 'greedy_search'.toNativeUtf8();
      recognizerConfig.ref.maxActivePaths = 4;
      recognizerConfig.ref.hotwordsFile = ''.toNativeUtf8();
      recognizerConfig.ref.hotwordsScore = 1.5;
      recognizerConfig.ref.ruleFsts = ''.toNativeUtf8();
      recognizerConfig.ref.ruleFars = ''.toNativeUtf8();
      recognizerConfig.ref.blankPenalty = 0.0;

      // 同音替换配置
      recognizerConfig.ref.hr.lexicon = ''.toNativeUtf8();
      recognizerConfig.ref.hr.ruleFsts = ''.toNativeUtf8();

      // 创建识别器
      _recognizer =
          SherpaOnnxOfflineBindings.createOfflineRecognizer(recognizerConfig);

      // 释放配置字符串
      _freeRecognizerConfigStrings(recognizerConfig);
      calloc.free(recognizerConfig);

      if (_recognizer == null || _recognizer == nullptr) {
        if (enableDebugLog) {
          // ignore: avoid_print
          print('[SenseVoiceEngine] ❌ 离线识别器创建失败');
        }
        _lastError = ASRError.recognizerCreateFailed;
        return _lastError;
      }

      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ✅ 离线识别器初始化成功');
      }

      return ASRError.none;
    } catch (e) {
      calloc.free(recognizerConfig);
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ 离线识别器初始化异常: $e');
      }
      _lastError = ASRError.recognizerCreateFailed;
      return _lastError;
    }
  }

  /// 释放识别器配置中分配的字符串内存
  void _freeRecognizerConfigStrings(
      Pointer<SherpaOnnxOfflineRecognizerConfig> c) {
    calloc.free(c.ref.modelConfig.senseVoice.model);
    calloc.free(c.ref.modelConfig.senseVoice.language);
    calloc.free(c.ref.modelConfig.transducer.encoder);
    calloc.free(c.ref.modelConfig.transducer.decoder);
    calloc.free(c.ref.modelConfig.transducer.joiner);
    calloc.free(c.ref.modelConfig.paraformer.model);
    calloc.free(c.ref.modelConfig.nemoCtc.model);
    calloc.free(c.ref.modelConfig.whisper.encoder);
    calloc.free(c.ref.modelConfig.whisper.decoder);
    calloc.free(c.ref.modelConfig.whisper.language);
    calloc.free(c.ref.modelConfig.whisper.task);
    calloc.free(c.ref.modelConfig.tdnn.model);
    calloc.free(c.ref.modelConfig.tokens);
    calloc.free(c.ref.modelConfig.provider);
    calloc.free(c.ref.modelConfig.modelType);
    calloc.free(c.ref.modelConfig.modelingUnit);
    calloc.free(c.ref.modelConfig.bpeVocab);
    calloc.free(c.ref.modelConfig.telespeechCtc);
    calloc.free(c.ref.lmConfig.model);
    calloc.free(c.ref.decodingMethod);
    calloc.free(c.ref.hotwordsFile);
    calloc.free(c.ref.ruleFsts);
    calloc.free(c.ref.ruleFars);
    calloc.free(c.ref.hr.lexicon);
    calloc.free(c.ref.hr.ruleFsts);
  }

  @override
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n) {
    if (!_isInitialized || _vad == null) return;

    // 将音频数据送入 VAD
    SherpaOnnxVadBindings.voiceActivityDetectorAcceptWaveform(_vad!, samples, n);

    // 检查是否有检测到的语音段
    _processVadSegments();
  }

  /// 处理 VAD 检测到的语音段
  void _processVadSegments() {
    // 检查 VAD 队列是否为空
    while (SherpaOnnxVadBindings.voiceActivityDetectorEmpty(_vad!) == 0) {
      _hasEndpoint = true;

      // 获取语音段
      final segment = SherpaOnnxVadBindings.voiceActivityDetectorFront(_vad!);

      if (segment != nullptr) {
        // 对语音段进行识别
        final result = _recognizeSegment(segment);
        if (result.isNotEmpty) {
          _lastResult = result;
        }

        // 销毁语音段
        SherpaOnnxVadBindings.destroySpeechSegment(segment);
      }

      // 弹出已处理的段
      SherpaOnnxVadBindings.voiceActivityDetectorPop(_vad!);
    }
  }

  /// 对语音段进行离线识别
  ASRResult _recognizeSegment(Pointer<SherpaOnnxSpeechSegment> segment) {
    if (_recognizer == null || segment == nullptr) {
      return ASRResult.empty();
    }

    // 获取语音段数据
    final samples = segment.ref.samples;
    final sampleCount = segment.ref.n;

    if (samples == nullptr || sampleCount <= 0) {
      return ASRResult.empty();
    }

    // 创建离线流
    final stream = SherpaOnnxOfflineBindings.createOfflineStream(_recognizer!);
    if (stream == nullptr) {
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ 创建离线流失败');
      }
      return ASRResult.empty();
    }

    try {
      // 送入语音段音频
      SherpaOnnxOfflineBindings.acceptWaveformOffline(
        stream,
        _config?.sampleRate ?? 16000,
        samples,
        sampleCount,
      );

      // 解码
      SherpaOnnxOfflineBindings.decodeOfflineStream(_recognizer!, stream);

      // 获取结果
      final result = _getStreamResult(stream);

      // 销毁流
      SherpaOnnxOfflineBindings.destroyOfflineStream(stream);

      if (enableDebugLog && result.isNotEmpty) {
        // ignore: avoid_print
        print(
            '[SenseVoiceEngine] 识别结果: "${result.text}" (lang=${result.lang}, emotion=${result.emotion})');
      }

      return result;
    } catch (e) {
      SherpaOnnxOfflineBindings.destroyOfflineStream(stream);
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ 识别异常: $e');
      }
      return ASRResult.empty();
    }
  }

  /// 从离线流获取识别结果
  ASRResult _getStreamResult(Pointer<SherpaOnnxOfflineStream> stream) {
    // 获取结构化结果
    final resultPtr = SherpaOnnxOfflineBindings.getOfflineStreamResult(stream);

    if (resultPtr == nullptr) {
      return ASRResult.empty();
    }

    try {
      final text = resultPtr.ref.text != nullptr
          ? resultPtr.ref.text.toDartString()
          : '';
      final lang = resultPtr.ref.lang != nullptr
          ? resultPtr.ref.lang.toDartString()
          : null;
      final emotion = resultPtr.ref.emotion != nullptr
          ? resultPtr.ref.emotion.toDartString()
          : null;

      // 解析 tokens 和 timestamps
      List<String> tokens = [];
      List<double> timestamps = [];

      final count = resultPtr.ref.count;
      if (count > 0) {
        // 从 tokensArr 获取 tokens
        if (resultPtr.ref.tokensArr != nullptr) {
          for (int i = 0; i < count; i++) {
            final tokenPtr = resultPtr.ref.tokensArr[i];
            if (tokenPtr != nullptr) {
              tokens.add(tokenPtr.toDartString());
            }
          }
        }

        // 从 timestamps 数组获取时间戳
        if (resultPtr.ref.timestamps != nullptr) {
          for (int i = 0; i < count; i++) {
            timestamps.add(resultPtr.ref.timestamps[i]);
          }
        }
      }

      // 销毁结果
      SherpaOnnxOfflineBindings.destroyOfflineRecognizerResult(resultPtr);

      return ASRResult(
        text: text.trim(),
        lang: lang?.isNotEmpty == true ? lang : null,
        emotion: emotion?.isNotEmpty == true ? emotion : null,
        tokens: tokens,
        timestamps: timestamps,
      );
    } catch (e) {
      SherpaOnnxOfflineBindings.destroyOfflineRecognizerResult(resultPtr);
      if (enableDebugLog) {
        // ignore: avoid_print
        print('[SenseVoiceEngine] ❌ 结果解析异常: $e');
      }
      return ASRResult.empty();
    }
  }

  @override
  void decode() {
    // SenseVoice 是离线引擎，解码在 acceptWaveform 时自动完成
    // 此方法为空实现，保持接口一致性
  }

  @override
  bool isReady() {
    // SenseVoice 引擎始终返回 false
    // 因为它不使用流式解码的 isReady 机制
    return false;
  }

  @override
  ASRResult getResult() {
    return _lastResult;
  }

  @override
  bool isEndpoint() {
    final result = _hasEndpoint;
    // 重置标志 (调用一次后清除)
    _hasEndpoint = false;
    return result;
  }

  @override
  void reset() {
    if (!_isInitialized || _vad == null) return;

    // 重置 VAD
    SherpaOnnxVadBindings.voiceActivityDetectorReset(_vad!);

    // 清空结果
    _lastResult = ASRResult.empty();
    _hasEndpoint = false;
  }

  @override
  void inputFinished() {
    if (!_isInitialized || _vad == null) return;

    // 刷新 VAD，处理剩余缓冲区数据
    SherpaOnnxVadBindings.voiceActivityDetectorFlush(_vad!);

    // 处理可能的最后一个语音段
    _processVadSegments();
  }

  /// 销毁 VAD
  void _destroyVad() {
    if (_vad != null && _vad != nullptr) {
      SherpaOnnxVadBindings.destroyVoiceActivityDetector(_vad!);
      _vad = null;
    }
  }

  @override
  void dispose() {
    // 销毁 VAD
    _destroyVad();

    // 销毁离线识别器
    if (_recognizer != null && _recognizer != nullptr) {
      SherpaOnnxOfflineBindings.destroyOfflineRecognizer(_recognizer!);
      _recognizer = null;
    }

    _isInitialized = false;
    _lib = null;
    _config = null;
    _lastResult = ASRResult.empty();
    _hasEndpoint = false;
  }
}

