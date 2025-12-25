// Copyright (c) 2024 Xiaomi Corporation
// Copyright (c) 2025 Nextalk Project
// Story 2-7: SenseVoice 离线识别 FFI 绑定

import 'dart:ffi';
import 'package:ffi/ffi.dart';

// ===== 离线识别结构体定义 =====

/// SenseVoice 模型配置
final class SherpaOnnxOfflineSenseVoiceModelConfig extends Struct {
  /// 模型文件路径 (model.onnx)
  external Pointer<Utf8> model;

  /// 语言: auto, zh, en, ja, ko, yue
  external Pointer<Utf8> language;

  /// 是否启用 ITN (Inverse Text Normalization)
  @Int32()
  external int useItn;
}

/// Transducer 模型配置 (离线)
final class SherpaOnnxOfflineTransducerModelConfig extends Struct {
  external Pointer<Utf8> encoder;
  external Pointer<Utf8> decoder;
  external Pointer<Utf8> joiner;
}

/// Paraformer 模型配置 (离线)
final class SherpaOnnxOfflineParaformerModelConfig extends Struct {
  external Pointer<Utf8> model;
}

/// NeMo CTC 模型配置 (离线)
final class SherpaOnnxOfflineNemoEncDecCtcModelConfig extends Struct {
  external Pointer<Utf8> model;
}

/// Whisper 模型配置 (离线)
final class SherpaOnnxOfflineWhisperModelConfig extends Struct {
  external Pointer<Utf8> encoder;
  external Pointer<Utf8> decoder;
  external Pointer<Utf8> language;
  external Pointer<Utf8> task;

  @Int32()
  external int tailPaddings;
}

/// Tdnn CTC 模型配置 (离线)
final class SherpaOnnxOfflineTdnnModelConfig extends Struct {
  external Pointer<Utf8> model;
}

/// 同音替换配置 (复用在线版本)
final class SherpaOnnxOfflineHomophoneReplacerConfig extends Struct {
  external Pointer<Utf8> lexicon;
  external Pointer<Utf8> ruleFsts;
}

/// 离线模型配置
final class SherpaOnnxOfflineModelConfig extends Struct {
  external SherpaOnnxOfflineTransducerModelConfig transducer;
  external SherpaOnnxOfflineParaformerModelConfig paraformer;
  external SherpaOnnxOfflineNemoEncDecCtcModelConfig nemoCtc;
  external SherpaOnnxOfflineWhisperModelConfig whisper;
  external SherpaOnnxOfflineTdnnModelConfig tdnn;

  external Pointer<Utf8> tokens;

  @Int32()
  external int numThreads;

  @Int32()
  external int debug;

  external Pointer<Utf8> provider;
  external Pointer<Utf8> modelType;
  external Pointer<Utf8> modelingUnit;
  external Pointer<Utf8> bpeVocab;
  external Pointer<Utf8> telespeechCtc;

  external SherpaOnnxOfflineSenseVoiceModelConfig senseVoice;

  external Pointer<Utf8> tokensBuf;

  @Int32()
  external int tokensBufSize;
}

/// 离线语言模型配置
final class SherpaOnnxOfflineLMConfig extends Struct {
  external Pointer<Utf8> model;

  @Float()
  external double scale;
}

/// 离线识别器配置
final class SherpaOnnxOfflineRecognizerConfig extends Struct {
  external SherpaOnnxFeatureConfigOffline featConfig;
  external SherpaOnnxOfflineModelConfig modelConfig;
  external SherpaOnnxOfflineLMConfig lmConfig;

  external Pointer<Utf8> decodingMethod;

  @Int32()
  external int maxActivePaths;

  external Pointer<Utf8> hotwordsFile;

  @Float()
  external double hotwordsScore;

  external Pointer<Utf8> ruleFsts;
  external Pointer<Utf8> ruleFars;

  @Float()
  external double blankPenalty;

  external SherpaOnnxOfflineHomophoneReplacerConfig hr;
}

/// 音频特征配置 (离线版)
final class SherpaOnnxFeatureConfigOffline extends Struct {
  @Int32()
  external int sampleRate;

  @Int32()
  external int featureDim;
}

/// 离线识别器 (不透明指针)
final class SherpaOnnxOfflineRecognizer extends Opaque {}

/// 离线流 (不透明指针)
final class SherpaOnnxOfflineStream extends Opaque {}

/// 离线识别结果
final class SherpaOnnxOfflineRecognizerResult extends Struct {
  /// 识别文本
  external Pointer<Utf8> text;

  /// 时间戳数组 (每个 token 的时间)
  external Pointer<Float> timestamps;

  /// token 数量
  @Int32()
  external int count;

  /// tokens (字符串形式，空格分隔)
  external Pointer<Utf8> tokens;

  /// tokens 数组
  external Pointer<Pointer<Utf8>> tokensArr;

  /// JSON 格式结果
  external Pointer<Utf8> json;

  /// 语言标识 (SenseVoice: zh/en/ja/ko/yue)
  external Pointer<Utf8> lang;

  /// 情感标识 (SenseVoice: NEUTRAL/HAPPY/SAD/ANGRY)
  external Pointer<Utf8> emotion;

  /// 事件标识 (SenseVoice: 可选)
  external Pointer<Utf8> event;

  /// 持续时间数组
  external Pointer<Float> durations;
}

// ===== FFI 函数类型定义 (Native) =====

typedef CreateOfflineRecognizerNative = Pointer<SherpaOnnxOfflineRecognizer>
    Function(Pointer<SherpaOnnxOfflineRecognizerConfig>);

typedef DestroyOfflineRecognizerNative = Void Function(
    Pointer<SherpaOnnxOfflineRecognizer>);

typedef CreateOfflineStreamNative = Pointer<SherpaOnnxOfflineStream> Function(
    Pointer<SherpaOnnxOfflineRecognizer>);

typedef DestroyOfflineStreamNative = Void Function(
    Pointer<SherpaOnnxOfflineStream>);

typedef AcceptWaveformOfflineNative = Void Function(
    Pointer<SherpaOnnxOfflineStream>, Int32, Pointer<Float>, Int32);

typedef DecodeOfflineStreamNative = Void Function(
    Pointer<SherpaOnnxOfflineRecognizer>, Pointer<SherpaOnnxOfflineStream>);

typedef GetOfflineStreamResultNative = Pointer<SherpaOnnxOfflineRecognizerResult>
    Function(Pointer<SherpaOnnxOfflineStream>);

typedef DestroyOfflineRecognizerResultNative = Void Function(
    Pointer<SherpaOnnxOfflineRecognizerResult>);

typedef GetOfflineStreamResultAsJsonNative = Pointer<Utf8> Function(
    Pointer<SherpaOnnxOfflineStream>);

typedef DestroyOfflineStreamResultJsonNative = Void Function(Pointer<Utf8>);

// ===== FFI 函数类型定义 (Dart) =====

typedef CreateOfflineRecognizerDart = Pointer<SherpaOnnxOfflineRecognizer>
    Function(Pointer<SherpaOnnxOfflineRecognizerConfig>);

typedef DestroyOfflineRecognizerDart = void Function(
    Pointer<SherpaOnnxOfflineRecognizer>);

typedef CreateOfflineStreamDart = Pointer<SherpaOnnxOfflineStream> Function(
    Pointer<SherpaOnnxOfflineRecognizer>);

typedef DestroyOfflineStreamDart = void Function(
    Pointer<SherpaOnnxOfflineStream>);

typedef AcceptWaveformOfflineDart = void Function(
    Pointer<SherpaOnnxOfflineStream>, int, Pointer<Float>, int);

typedef DecodeOfflineStreamDart = void Function(
    Pointer<SherpaOnnxOfflineRecognizer>, Pointer<SherpaOnnxOfflineStream>);

typedef GetOfflineStreamResultDart = Pointer<SherpaOnnxOfflineRecognizerResult>
    Function(Pointer<SherpaOnnxOfflineStream>);

typedef DestroyOfflineRecognizerResultDart = void Function(
    Pointer<SherpaOnnxOfflineRecognizerResult>);

typedef GetOfflineStreamResultAsJsonDart = Pointer<Utf8> Function(
    Pointer<SherpaOnnxOfflineStream>);

typedef DestroyOfflineStreamResultJsonDart = void Function(Pointer<Utf8>);

// ===== Sherpa-onnx 离线绑定类 =====

/// Sherpa-onnx 离线识别 FFI 绑定
///
/// 提供对 libsherpa-onnx-c-api.so 离线识别函数的绑定。
/// 用于 SenseVoice 等非流式模型。
class SherpaOnnxOfflineBindings {
  static CreateOfflineRecognizerDart? _createOfflineRecognizer;
  static DestroyOfflineRecognizerDart? _destroyOfflineRecognizer;
  static CreateOfflineStreamDart? _createOfflineStream;
  static DestroyOfflineStreamDart? _destroyOfflineStream;
  static AcceptWaveformOfflineDart? _acceptWaveformOffline;
  static DecodeOfflineStreamDart? _decodeOfflineStream;
  static GetOfflineStreamResultDart? _getOfflineStreamResult;
  static DestroyOfflineRecognizerResultDart? _destroyOfflineRecognizerResult;
  static GetOfflineStreamResultAsJsonDart? _getOfflineStreamResultAsJson;
  static DestroyOfflineStreamResultJsonDart? _destroyOfflineStreamResultJson;

  static bool _initialized = false;

  /// 是否已初始化
  static bool get isInitialized => _initialized;

  /// 获取函数绑定，如未初始化则抛出 StateError
  static CreateOfflineRecognizerDart get createOfflineRecognizer {
    _checkInitialized();
    return _createOfflineRecognizer!;
  }

  static DestroyOfflineRecognizerDart get destroyOfflineRecognizer {
    _checkInitialized();
    return _destroyOfflineRecognizer!;
  }

  static CreateOfflineStreamDart get createOfflineStream {
    _checkInitialized();
    return _createOfflineStream!;
  }

  static DestroyOfflineStreamDart get destroyOfflineStream {
    _checkInitialized();
    return _destroyOfflineStream!;
  }

  static AcceptWaveformOfflineDart get acceptWaveformOffline {
    _checkInitialized();
    return _acceptWaveformOffline!;
  }

  static DecodeOfflineStreamDart get decodeOfflineStream {
    _checkInitialized();
    return _decodeOfflineStream!;
  }

  static GetOfflineStreamResultDart get getOfflineStreamResult {
    _checkInitialized();
    return _getOfflineStreamResult!;
  }

  static DestroyOfflineRecognizerResultDart get destroyOfflineRecognizerResult {
    _checkInitialized();
    return _destroyOfflineRecognizerResult!;
  }

  static GetOfflineStreamResultAsJsonDart get getOfflineStreamResultAsJson {
    _checkInitialized();
    return _getOfflineStreamResultAsJson!;
  }

  static DestroyOfflineStreamResultJsonDart get destroyOfflineStreamResultJson {
    _checkInitialized();
    return _destroyOfflineStreamResultJson!;
  }

  static void _checkInitialized() {
    if (!_initialized) {
      throw StateError('SherpaOnnxOfflineBindings 未初始化，请先调用 init()');
    }
  }

  /// 初始化绑定
  ///
  /// [lib] 已加载的动态库
  static void init(DynamicLibrary lib) {
    if (_initialized) return;

    _createOfflineRecognizer = lib.lookupFunction<CreateOfflineRecognizerNative,
        CreateOfflineRecognizerDart>('SherpaOnnxCreateOfflineRecognizer');

    _destroyOfflineRecognizer = lib.lookupFunction<
        DestroyOfflineRecognizerNative,
        DestroyOfflineRecognizerDart>('SherpaOnnxDestroyOfflineRecognizer');

    _createOfflineStream =
        lib.lookupFunction<CreateOfflineStreamNative, CreateOfflineStreamDart>(
            'SherpaOnnxCreateOfflineStream');

    _destroyOfflineStream = lib.lookupFunction<DestroyOfflineStreamNative,
        DestroyOfflineStreamDart>('SherpaOnnxDestroyOfflineStream');

    _acceptWaveformOffline = lib.lookupFunction<AcceptWaveformOfflineNative,
        AcceptWaveformOfflineDart>('SherpaOnnxAcceptWaveformOffline');

    _decodeOfflineStream =
        lib.lookupFunction<DecodeOfflineStreamNative, DecodeOfflineStreamDart>(
            'SherpaOnnxDecodeOfflineStream');

    _getOfflineStreamResult = lib.lookupFunction<GetOfflineStreamResultNative,
        GetOfflineStreamResultDart>('SherpaOnnxGetOfflineStreamResult');

    _destroyOfflineRecognizerResult = lib.lookupFunction<
            DestroyOfflineRecognizerResultNative,
            DestroyOfflineRecognizerResultDart>(
        'SherpaOnnxDestroyOfflineRecognizerResult');

    _getOfflineStreamResultAsJson = lib.lookupFunction<
            GetOfflineStreamResultAsJsonNative,
            GetOfflineStreamResultAsJsonDart>(
        'SherpaOnnxGetOfflineStreamResultAsJson');

    _destroyOfflineStreamResultJson = lib.lookupFunction<
            DestroyOfflineStreamResultJsonNative,
            DestroyOfflineStreamResultJsonDart>(
        'SherpaOnnxDestroyOfflineStreamResultJson');

    _initialized = true;
  }

  /// 重置绑定状态 (仅用于测试)
  static void resetForTesting() {
    _initialized = false;
    _createOfflineRecognizer = null;
    _destroyOfflineRecognizer = null;
    _createOfflineStream = null;
    _destroyOfflineStream = null;
    _acceptWaveformOffline = null;
    _decodeOfflineStream = null;
    _getOfflineStreamResult = null;
    _destroyOfflineRecognizerResult = null;
    _getOfflineStreamResultAsJson = null;
    _destroyOfflineStreamResultJson = null;
  }
}

