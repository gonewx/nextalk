// Copyright (c) 2024 Xiaomi Corporation
// Copyright (c) 2025 Nextalk Project
// 基于官方 sherpa-onnx Flutter 绑定精简，仅保留在线流式识别功能

import 'dart:ffi';
import 'package:ffi/ffi.dart';

// ===== FFI 结构体定义 =====

/// 音频特征配置
final class SherpaOnnxFeatureConfig extends Struct {
  @Int32()
  external int sampleRate;

  @Int32()
  external int featureDim;
}

/// Transducer 模型配置
final class SherpaOnnxOnlineTransducerModelConfig extends Struct {
  external Pointer<Utf8> encoder;
  external Pointer<Utf8> decoder;
  external Pointer<Utf8> joiner;
}

/// Paraformer 模型配置
final class SherpaOnnxOnlineParaformerModelConfig extends Struct {
  external Pointer<Utf8> encoder;
  external Pointer<Utf8> decoder;
}

/// Zipformer2 CTC 模型配置
final class SherpaOnnxOnlineZipformer2CtcModelConfig extends Struct {
  external Pointer<Utf8> model;
}

/// Nemo CTC 模型配置
final class SherpaOnnxOnlineNemoCtcModelConfig extends Struct {
  external Pointer<Utf8> model;
}

/// Tone CTC 模型配置
final class SherpaOnnxOnlineToneCtcModelConfig extends Struct {
  external Pointer<Utf8> model;
}

/// CTC FST 解码器配置
final class SherpaOnnxOnlineCtcFstDecoderConfig extends Struct {
  external Pointer<Utf8> graph;

  @Int32()
  external int maxActive;
}

/// 同音替换配置
/// 注意: dict_dir 字段虽然标记为 unused，但必须存在以匹配 C 结构体布局
final class SherpaOnnxHomophoneReplacerConfig extends Struct {
  external Pointer<Utf8> dictDir; // unused but required for struct alignment
  external Pointer<Utf8> lexicon;
  external Pointer<Utf8> ruleFsts;
}

/// 在线模型配置
final class SherpaOnnxOnlineModelConfig extends Struct {
  external SherpaOnnxOnlineTransducerModelConfig transducer;
  external SherpaOnnxOnlineParaformerModelConfig paraformer;
  external SherpaOnnxOnlineZipformer2CtcModelConfig zipformer2Ctc;

  external Pointer<Utf8> tokens;

  @Int32()
  external int numThreads;

  external Pointer<Utf8> provider;

  @Int32()
  external int debug;

  external Pointer<Utf8> modelType;
  external Pointer<Utf8> modelingUnit;
  external Pointer<Utf8> bpeVocab;
  external Pointer<Utf8> tokensBuf;

  @Int32()
  external int tokensBufSize;

  external SherpaOnnxOnlineNemoCtcModelConfig nemoCtc;
  external SherpaOnnxOnlineToneCtcModelConfig toneCtc;
}

/// 在线识别器配置
final class SherpaOnnxOnlineRecognizerConfig extends Struct {
  external SherpaOnnxFeatureConfig feat;
  external SherpaOnnxOnlineModelConfig model;
  external Pointer<Utf8> decodingMethod;

  @Int32()
  external int maxActivePaths;

  @Int32()
  external int enableEndpoint;

  @Float()
  external double rule1MinTrailingSilence;

  @Float()
  external double rule2MinTrailingSilence;

  @Float()
  external double rule3MinUtteranceLength;

  external Pointer<Utf8> hotwordsFile;

  @Float()
  external double hotwordsScore;

  external SherpaOnnxOnlineCtcFstDecoderConfig ctcFstDecoderConfig;

  external Pointer<Utf8> ruleFsts;
  external Pointer<Utf8> ruleFars;

  @Float()
  external double blankPenalty;

  external Pointer<Utf8> hotwordsBuf;

  @Int32()
  external int hotwordsBufSize;

  external SherpaOnnxHomophoneReplacerConfig hr;
}

/// 在线识别器 (不透明指针)
final class SherpaOnnxOnlineRecognizer extends Opaque {}

/// 在线流 (不透明指针)
final class SherpaOnnxOnlineStream extends Opaque {}

// ===== FFI 函数类型定义 (Native) =====

typedef CreateOnlineRecognizerNative = Pointer<SherpaOnnxOnlineRecognizer>
    Function(Pointer<SherpaOnnxOnlineRecognizerConfig>);

typedef DestroyOnlineRecognizerNative = Void Function(
    Pointer<SherpaOnnxOnlineRecognizer>);

typedef CreateOnlineStreamNative = Pointer<SherpaOnnxOnlineStream> Function(
    Pointer<SherpaOnnxOnlineRecognizer>);

typedef DestroyOnlineStreamNative = Void Function(
    Pointer<SherpaOnnxOnlineStream>);

typedef OnlineStreamAcceptWaveformNative = Void Function(
    Pointer<SherpaOnnxOnlineStream>, Int32, Pointer<Float>, Int32);

typedef IsOnlineStreamReadyNative = Int32 Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef DecodeOnlineStreamNative = Void Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef GetOnlineStreamResultAsJsonNative = Pointer<Utf8> Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef DestroyOnlineStreamResultJsonNative = Void Function(Pointer<Utf8>);

typedef ResetOnlineStreamNative = Void Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef IsEndpointNative = Int32 Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef OnlineStreamInputFinishedNative = Void Function(
    Pointer<SherpaOnnxOnlineStream>);

// ===== FFI 函数类型定义 (Dart) =====

typedef CreateOnlineRecognizerDart = Pointer<SherpaOnnxOnlineRecognizer>
    Function(Pointer<SherpaOnnxOnlineRecognizerConfig>);

typedef DestroyOnlineRecognizerDart = void Function(
    Pointer<SherpaOnnxOnlineRecognizer>);

typedef CreateOnlineStreamDart = Pointer<SherpaOnnxOnlineStream> Function(
    Pointer<SherpaOnnxOnlineRecognizer>);

typedef DestroyOnlineStreamDart = void Function(
    Pointer<SherpaOnnxOnlineStream>);

typedef OnlineStreamAcceptWaveformDart = void Function(
    Pointer<SherpaOnnxOnlineStream>, int, Pointer<Float>, int);

typedef IsOnlineStreamReadyDart = int Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef DecodeOnlineStreamDart = void Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef GetOnlineStreamResultAsJsonDart = Pointer<Utf8> Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef DestroyOnlineStreamResultJsonDart = void Function(Pointer<Utf8>);

typedef ResetOnlineStreamDart = void Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef IsEndpointDart = int Function(
    Pointer<SherpaOnnxOnlineRecognizer>, Pointer<SherpaOnnxOnlineStream>);

typedef OnlineStreamInputFinishedDart = void Function(
    Pointer<SherpaOnnxOnlineStream>);

// ===== Sherpa-onnx 绑定类 =====

/// Sherpa-onnx FFI 绑定
///
/// 提供对 libsherpa-onnx-c-api.so 的函数绑定
class SherpaOnnxBindings {
  static CreateOnlineRecognizerDart? _createOnlineRecognizer;
  static DestroyOnlineRecognizerDart? _destroyOnlineRecognizer;
  static CreateOnlineStreamDart? _createOnlineStream;
  static DestroyOnlineStreamDart? _destroyOnlineStream;
  static OnlineStreamAcceptWaveformDart? _onlineStreamAcceptWaveform;
  static IsOnlineStreamReadyDart? _isOnlineStreamReady;
  static DecodeOnlineStreamDart? _decodeOnlineStream;
  static GetOnlineStreamResultAsJsonDart? _getOnlineStreamResultAsJson;
  static DestroyOnlineStreamResultJsonDart? _destroyOnlineStreamResultJson;
  static ResetOnlineStreamDart? _reset;
  static IsEndpointDart? _isEndpoint;
  static OnlineStreamInputFinishedDart? _onlineStreamInputFinished;

  static bool _initialized = false;

  /// 是否已初始化
  static bool get isInitialized => _initialized;

  /// 获取函数绑定，如未初始化则抛出 StateError
  static CreateOnlineRecognizerDart get createOnlineRecognizer {
    _checkInitialized();
    return _createOnlineRecognizer!;
  }

  static DestroyOnlineRecognizerDart get destroyOnlineRecognizer {
    _checkInitialized();
    return _destroyOnlineRecognizer!;
  }

  static CreateOnlineStreamDart get createOnlineStream {
    _checkInitialized();
    return _createOnlineStream!;
  }

  static DestroyOnlineStreamDart get destroyOnlineStream {
    _checkInitialized();
    return _destroyOnlineStream!;
  }

  static OnlineStreamAcceptWaveformDart get onlineStreamAcceptWaveform {
    _checkInitialized();
    return _onlineStreamAcceptWaveform!;
  }

  static IsOnlineStreamReadyDart get isOnlineStreamReady {
    _checkInitialized();
    return _isOnlineStreamReady!;
  }

  static DecodeOnlineStreamDart get decodeOnlineStream {
    _checkInitialized();
    return _decodeOnlineStream!;
  }

  static GetOnlineStreamResultAsJsonDart get getOnlineStreamResultAsJson {
    _checkInitialized();
    return _getOnlineStreamResultAsJson!;
  }

  static DestroyOnlineStreamResultJsonDart get destroyOnlineStreamResultJson {
    _checkInitialized();
    return _destroyOnlineStreamResultJson!;
  }

  static ResetOnlineStreamDart get reset {
    _checkInitialized();
    return _reset!;
  }

  static IsEndpointDart get isEndpoint {
    _checkInitialized();
    return _isEndpoint!;
  }

  static OnlineStreamInputFinishedDart get onlineStreamInputFinished {
    _checkInitialized();
    return _onlineStreamInputFinished!;
  }

  static void _checkInitialized() {
    if (!_initialized) {
      throw StateError('SherpaOnnxBindings 未初始化，请先调用 init()');
    }
  }

  /// 初始化绑定
  ///
  /// [lib] 已加载的动态库
  static void init(DynamicLibrary lib) {
    if (_initialized) return;

    _createOnlineRecognizer = lib.lookupFunction<CreateOnlineRecognizerNative,
        CreateOnlineRecognizerDart>('SherpaOnnxCreateOnlineRecognizer');

    _destroyOnlineRecognizer = lib.lookupFunction<DestroyOnlineRecognizerNative,
        DestroyOnlineRecognizerDart>('SherpaOnnxDestroyOnlineRecognizer');

    _createOnlineStream =
        lib.lookupFunction<CreateOnlineStreamNative, CreateOnlineStreamDart>(
            'SherpaOnnxCreateOnlineStream');

    _destroyOnlineStream =
        lib.lookupFunction<DestroyOnlineStreamNative, DestroyOnlineStreamDart>(
            'SherpaOnnxDestroyOnlineStream');

    _onlineStreamAcceptWaveform = lib.lookupFunction<
        OnlineStreamAcceptWaveformNative,
        OnlineStreamAcceptWaveformDart>('SherpaOnnxOnlineStreamAcceptWaveform');

    _isOnlineStreamReady =
        lib.lookupFunction<IsOnlineStreamReadyNative, IsOnlineStreamReadyDart>(
            'SherpaOnnxIsOnlineStreamReady');

    _decodeOnlineStream =
        lib.lookupFunction<DecodeOnlineStreamNative, DecodeOnlineStreamDart>(
            'SherpaOnnxDecodeOnlineStream');

    _getOnlineStreamResultAsJson = lib.lookupFunction<
            GetOnlineStreamResultAsJsonNative, GetOnlineStreamResultAsJsonDart>(
        'SherpaOnnxGetOnlineStreamResultAsJson');

    _destroyOnlineStreamResultJson = lib.lookupFunction<
            DestroyOnlineStreamResultJsonNative,
            DestroyOnlineStreamResultJsonDart>(
        'SherpaOnnxDestroyOnlineStreamResultJson');

    _reset = lib.lookupFunction<ResetOnlineStreamNative, ResetOnlineStreamDart>(
        'SherpaOnnxOnlineStreamReset');

    _isEndpoint = lib.lookupFunction<IsEndpointNative, IsEndpointDart>(
        'SherpaOnnxOnlineStreamIsEndpoint');

    _onlineStreamInputFinished = lib.lookupFunction<
        OnlineStreamInputFinishedNative,
        OnlineStreamInputFinishedDart>('SherpaOnnxOnlineStreamInputFinished');

    _initialized = true;
  }

  /// 重置绑定状态 (仅用于测试)
  // ignore: use_setters_to_change_properties
  static void resetForTesting() {
    _initialized = false;
    _createOnlineRecognizer = null;
    _destroyOnlineRecognizer = null;
    _createOnlineStream = null;
    _destroyOnlineStream = null;
    _onlineStreamAcceptWaveform = null;
    _isOnlineStreamReady = null;
    _decodeOnlineStream = null;
    _getOnlineStreamResultAsJson = null;
    _destroyOnlineStreamResultJson = null;
    _reset = null;
    _isEndpoint = null;
    _onlineStreamInputFinished = null;
  }
}
