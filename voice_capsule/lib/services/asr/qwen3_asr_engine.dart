import 'dart:ffi';
import 'dart:io';
import 'package:ffi/ffi.dart';
import '../../constants/qwen3_asr_constants.dart';
import '../../ffi/sherpa_ffi.dart';
import '../../ffi/sherpa_offline_bindings.dart';
import '../../ffi/sherpa_vad_bindings.dart';
import 'asr_engine.dart';

/// Silero VAD 分段后交给 Qwen3-ASR 识别，在发话结束时清空累积结果。
class Qwen3AsrEngine implements ASREngine {
  final bool enableDebugLog;
  Pointer<SherpaOnnxVoiceActivityDetector> _vad = nullptr;
  Pointer<SherpaOnnxOfflineRecognizer> _recognizer = nullptr;
  ASRError _lastError = ASRError.none;
  String _text = '';
  bool _hasEndpoint = false;
  Qwen3AsrEngine({this.enableDebugLog = false});
  @override
  ASREngineType get engineType => ASREngineType.qwen3Asr;
  @override
  bool get isInitialized => _vad != nullptr && _recognizer != nullptr;
  @override
  ASRError get lastError => _lastError;
  @override
  Future<ASRError> initialize(ASRConfig config) async {
    if (isInitialized) return ASRError.none;
    if (config is! Qwen3AsrConfig ||
        config.sampleRate != 16000 ||
        config.numThreads <= 0 ||
        config.numThreads > 256 ||
        config.maxNewTokens <= 0 ||
        config.maxNewTokens > 512 ||
        !config.vadThreshold.isFinite ||
        !config.minSilenceDuration.isFinite ||
        !config.minSpeechDuration.isFinite ||
        !config.maxSpeechDuration.isFinite ||
        config.vadThreshold <= 0 ||
        config.vadThreshold >= 1 ||
        config.minSilenceDuration <= 0 ||
        config.minSpeechDuration <= 0 ||
        config.maxSpeechDuration < config.minSpeechDuration) {
      return _lastError = ASRError.invalidConfig;
    }
    if (!Directory(config.modelDir).existsSync()) {
      return _lastError = ASRError.modelNotFound;
    }
    if (!Qwen3AsrConstants.hasRequiredFiles(config.modelDir)) {
      return _lastError = ASRError.modelFileMissing;
    }
    final vadFile = File(config.vadModelPath);
    if (!vadFile.existsSync() || vadFile.lengthSync() == 0) {
      return _lastError = ASRError.vadInitFailed;
    }
    try {
      final lib = loadSherpaLibrary();
      SherpaOnnxOfflineBindings.init(lib);
      SherpaOnnxVadBindings.init(lib);
    } catch (_) {
      return _lastError = ASRError.libraryLoadFailed;
    }
    try {
      // Arena 保证所有配置及 UTF-8 字符串在原生创建调用后统一释放。
      using((arena) {
        final vad = arena<SherpaOnnxVadModelConfig>();
        vad.ref.sileroVad.model =
            config.vadModelPath.toNativeUtf8(allocator: arena);
        vad.ref.sileroVad.threshold = config.vadThreshold;
        vad.ref.sileroVad.minSilenceDuration = config.minSilenceDuration;
        vad.ref.sileroVad.minSpeechDuration = config.minSpeechDuration;
        vad.ref.sileroVad.maxSpeechDuration = config.maxSpeechDuration;
        vad.ref.sileroVad.windowSize = 512;
        vad.ref.sampleRate = config.sampleRate;
        vad.ref.numThreads = config.numThreads;
        vad.ref.provider = 'cpu'.toNativeUtf8(allocator: arena);
        vad.ref.debug = enableDebugLog ? 1 : 0;
        _vad = SherpaOnnxVadBindings.createVoiceActivityDetector(vad, 30);
      });
      if (_vad == nullptr) return _lastError = ASRError.vadInitFailed;
      using((arena) {
        final c = arena<SherpaOnnxOfflineRecognizerConfig>();
        c.ref.featConfig.sampleRate = config.sampleRate;
        c.ref.featConfig.featureDim = 80;
        c.ref.modelConfig.numThreads = config.numThreads;
        c.ref.modelConfig.provider = 'cpu'.toNativeUtf8(allocator: arena);
        c.ref.modelConfig.debug = enableDebugLog ? 1 : 0;
        final qwen = c.ref.modelConfig.qwen3Asr;
        qwen.convFrontend =
            '${config.modelDir}/${Qwen3AsrConstants.convFrontend}'
                .toNativeUtf8(allocator: arena);
        qwen.encoder = '${config.modelDir}/${Qwen3AsrConstants.encoder}'
            .toNativeUtf8(allocator: arena);
        qwen.decoder = '${config.modelDir}/${Qwen3AsrConstants.decoder}'
            .toNativeUtf8(allocator: arena);
        qwen.tokenizer = '${config.modelDir}/${Qwen3AsrConstants.tokenizer}'
            .toNativeUtf8(allocator: arena);
        qwen.maxTotalLen = 512;
        qwen.maxNewTokens = config.maxNewTokens;
        // 使用官方默认的近零温度，推理按贪心选择，避免随机采样。
        qwen.temperature = 0.000001;
        qwen.topP = 0.8;
        qwen.seed = 42;
        qwen.hotwords = config.hotwords.toNativeUtf8(allocator: arena);
        c.ref.decodingMethod = 'greedy_search'.toNativeUtf8(allocator: arena);
        _recognizer = SherpaOnnxOfflineBindings.createOfflineRecognizer(c);
      });
      if (_recognizer == nullptr) {
        dispose();
        return _lastError = ASRError.recognizerCreateFailed;
      }
      return _lastError = ASRError.none;
    } catch (_) {
      final error = _vad == nullptr
          ? ASRError.vadInitFailed
          : ASRError.recognizerCreateFailed;
      dispose();
      return _lastError = error;
    }
  }

  @override
  void acceptWaveform(int sampleRate, Pointer<Float> samples, int n) {
    if (!isInitialized) return;
    if (sampleRate != 16000 || samples == nullptr || n <= 0) {
      throw ArgumentError('Qwen3-ASR 需要非空的 16 kHz 音频');
    }
    SherpaOnnxVadBindings.voiceActivityDetectorAcceptWaveform(_vad, samples, n);
    _processSegments();
  }

  void _processSegments() {
    while (SherpaOnnxVadBindings.voiceActivityDetectorEmpty(_vad) == 0) {
      final segment = SherpaOnnxVadBindings.voiceActivityDetectorFront(_vad);
      try {
        if (segment != nullptr && segment.ref.n > 0) {
          final text = _recognize(segment.ref.samples, segment.ref.n);
          if (text.isNotEmpty) _text += text;
        }
        _hasEndpoint = true;
      } finally {
        if (segment != nullptr) {
          SherpaOnnxVadBindings.destroySpeechSegment(segment);
        }
        SherpaOnnxVadBindings.voiceActivityDetectorPop(_vad);
      }
    }
  }

  String _recognize(Pointer<Float> samples, int n) {
    final stream = SherpaOnnxOfflineBindings.createOfflineStream(_recognizer);
    if (stream == nullptr) {
      _lastError = ASRError.streamCreateFailed;
      return '';
    }
    try {
      SherpaOnnxOfflineBindings.acceptWaveformOffline(
          stream, 16000, samples, n);
      SherpaOnnxOfflineBindings.decodeOfflineStream(_recognizer, stream);
      final result = SherpaOnnxOfflineBindings.getOfflineStreamResult(stream);
      if (result == nullptr) return '';
      try {
        return result.ref.text == nullptr
            ? ''
            : result.ref.text.toDartString().trim();
      } finally {
        SherpaOnnxOfflineBindings.destroyOfflineRecognizerResult(result);
      }
    } finally {
      SherpaOnnxOfflineBindings.destroyOfflineStream(stream);
    }
  }

  @override
  void decode() {}
  @override
  bool isReady() => false;
  @override
  ASRResult getResult() => ASRResult(text: _text);
  @override
  bool isEndpoint() {
    final endpoint = _hasEndpoint;
    _hasEndpoint = false;
    return endpoint;
  }

  @override
  bool ensureStreamReady() => isInitialized;
  @override
  void reset() {
    if (_vad != nullptr) SherpaOnnxVadBindings.voiceActivityDetectorReset(_vad);
    _text = '';
    _hasEndpoint = false;
  }

  @override
  ASRResult finalizeUtterance() {
    if (!isInitialized) return ASRResult.empty();
    try {
      _flush();
      return getResult();
    } finally {
      // 必须先识别尾段再重置，避免丢尾字和跨发话文本累积。
      reset();
    }
  }

  void _flush() {
    if (!isInitialized) return;
    SherpaOnnxVadBindings.voiceActivityDetectorFlush(_vad);
    _processSegments();
  }

  @Deprecated('收尾请使用 finalizeUtterance()，以清理会话状态')
  @override
  void inputFinished() => _flush();
  @override
  void dispose() {
    if (_vad != nullptr) {
      SherpaOnnxVadBindings.destroyVoiceActivityDetector(_vad);
      _vad = nullptr;
    }
    if (_recognizer != nullptr) {
      SherpaOnnxOfflineBindings.destroyOfflineRecognizer(_recognizer);
      _recognizer = nullptr;
    }
    _text = '';
    _hasEndpoint = false;
  }
}
