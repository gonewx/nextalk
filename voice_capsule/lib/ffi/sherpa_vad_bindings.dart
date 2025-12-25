// Copyright (c) 2024 Xiaomi Corporation
// Copyright (c) 2025 Nextalk Project
// Story 2-7: Silero VAD FFI 绑定

import 'dart:ffi';
import 'package:ffi/ffi.dart';

// ===== VAD 结构体定义 =====

/// Silero VAD 模型配置
final class SherpaOnnxSileroVadModelConfig extends Struct {
  /// VAD 模型文件路径 (silero_vad.onnx)
  external Pointer<Utf8> model;

  /// 语音检测阈值 (推荐: 0.25 ~ 0.5)
  @Float()
  external double threshold;

  /// 最小静音时长 (秒), 用于判断语音结束
  @Float()
  external double minSilenceDuration;

  /// 最小语音时长 (秒), 短于此值的语音段被丢弃
  @Float()
  external double minSpeechDuration;

  /// 窗口大小 (采样点数)
  /// 对于 Silero VAD v4/v5, 必须为 512 (32ms @ 16kHz)
  @Int32()
  external int windowSize;

  /// 最大语音时长 (秒), 超过此值强制分段
  @Float()
  external double maxSpeechDuration;
}

/// Ten VAD 模型配置 (v1.12.20+ 新增)
final class SherpaOnnxTenVadModelConfig extends Struct {
  /// VAD 模型文件路径
  external Pointer<Utf8> model;

  /// 语音检测阈值
  @Float()
  external double threshold;

  /// 最小静音时长 (秒)
  @Float()
  external double minSilenceDuration;

  /// 最小语音时长 (秒)
  @Float()
  external double minSpeechDuration;

  /// 窗口大小 (采样点数)
  @Int32()
  external int windowSize;

  /// 最大语音时长 (秒)
  @Float()
  external double maxSpeechDuration;
}

/// VAD 模型配置
final class SherpaOnnxVadModelConfig extends Struct {
  /// Silero VAD 配置
  external SherpaOnnxSileroVadModelConfig sileroVad;

  /// 采样率 (必须为 16000)
  @Int32()
  external int sampleRate;

  /// 线程数
  @Int32()
  external int numThreads;

  /// provider (cpu, cuda)
  external Pointer<Utf8> provider;

  /// 调试模式
  @Int32()
  external int debug;

  /// Ten VAD 配置 (v1.12.20+ 新增)
  external SherpaOnnxTenVadModelConfig tenVad;
}

/// VAD 检测器 (不透明指针)
final class SherpaOnnxVoiceActivityDetector extends Opaque {}

/// 语音段
final class SherpaOnnxSpeechSegment extends Struct {
  /// 语音段起始采样点
  @Int32()
  external int start;

  /// 语音段音频采样
  external Pointer<Float> samples;

  /// 采样点数量
  @Int32()
  external int n;
}

// ===== FFI 函数类型定义 (Native) =====

typedef CreateVoiceActivityDetectorNative
    = Pointer<SherpaOnnxVoiceActivityDetector> Function(
        Pointer<SherpaOnnxVadModelConfig>, Float);

typedef DestroyVoiceActivityDetectorNative = Void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorAcceptWaveformNative = Void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>, Pointer<Float>, Int32);

typedef VoiceActivityDetectorEmptyNative = Int32 Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorDetectedNative = Int32 Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorPopNative = Void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorClearNative = Void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorFlushNative = Void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorFrontNative = Pointer<SherpaOnnxSpeechSegment>
    Function(Pointer<SherpaOnnxVoiceActivityDetector>);

typedef DestroySpeechSegmentNative = Void Function(
    Pointer<SherpaOnnxSpeechSegment>);

typedef VoiceActivityDetectorResetNative = Void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

// ===== FFI 函数类型定义 (Dart) =====

typedef CreateVoiceActivityDetectorDart
    = Pointer<SherpaOnnxVoiceActivityDetector> Function(
        Pointer<SherpaOnnxVadModelConfig>, double);

typedef DestroyVoiceActivityDetectorDart = void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorAcceptWaveformDart = void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>, Pointer<Float>, int);

typedef VoiceActivityDetectorEmptyDart = int Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorDetectedDart = int Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorPopDart = void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorClearDart = void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorFlushDart = void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

typedef VoiceActivityDetectorFrontDart = Pointer<SherpaOnnxSpeechSegment>
    Function(Pointer<SherpaOnnxVoiceActivityDetector>);

typedef DestroySpeechSegmentDart = void Function(
    Pointer<SherpaOnnxSpeechSegment>);

typedef VoiceActivityDetectorResetDart = void Function(
    Pointer<SherpaOnnxVoiceActivityDetector>);

// ===== Sherpa-onnx VAD 绑定类 =====

/// Sherpa-onnx VAD FFI 绑定
///
/// 提供对 libsherpa-onnx-c-api.so VAD 函数的绑定。
/// 用于 Silero VAD 语音活动检测。
///
/// 典型使用流程:
/// 1. 创建 VAD: createVoiceActivityDetector()
/// 2. 送入音频: voiceActivityDetectorAcceptWaveform()
/// 3. 检查是否有语音段: voiceActivityDetectorDetected()
/// 4. 获取语音段: voiceActivityDetectorFront()
/// 5. 弹出已处理段: voiceActivityDetectorPop()
/// 6. 销毁: destroyVoiceActivityDetector()
class SherpaOnnxVadBindings {
  static CreateVoiceActivityDetectorDart? _createVoiceActivityDetector;
  static DestroyVoiceActivityDetectorDart? _destroyVoiceActivityDetector;
  static VoiceActivityDetectorAcceptWaveformDart?
      _voiceActivityDetectorAcceptWaveform;
  static VoiceActivityDetectorEmptyDart? _voiceActivityDetectorEmpty;
  static VoiceActivityDetectorDetectedDart? _voiceActivityDetectorDetected;
  static VoiceActivityDetectorPopDart? _voiceActivityDetectorPop;
  static VoiceActivityDetectorClearDart? _voiceActivityDetectorClear;
  static VoiceActivityDetectorFlushDart? _voiceActivityDetectorFlush;
  static VoiceActivityDetectorFrontDart? _voiceActivityDetectorFront;
  static DestroySpeechSegmentDart? _destroySpeechSegment;
  static VoiceActivityDetectorResetDart? _voiceActivityDetectorReset;

  static bool _initialized = false;

  /// 是否已初始化
  static bool get isInitialized => _initialized;

  /// 创建 VAD 检测器
  ///
  /// [config] VAD 配置
  /// [bufferSizeInSeconds] 内部缓冲区大小 (秒)
  static CreateVoiceActivityDetectorDart get createVoiceActivityDetector {
    _checkInitialized();
    return _createVoiceActivityDetector!;
  }

  /// 销毁 VAD 检测器
  static DestroyVoiceActivityDetectorDart get destroyVoiceActivityDetector {
    _checkInitialized();
    return _destroyVoiceActivityDetector!;
  }

  /// 送入音频数据
  ///
  /// [vad] VAD 检测器
  /// [samples] 音频采样 (Float32, 值域 [-1.0, 1.0])
  /// [n] 采样数量
  ///
  /// 注意: 每次应送入 windowSize 个采样 (512 for Silero)
  static VoiceActivityDetectorAcceptWaveformDart
      get voiceActivityDetectorAcceptWaveform {
    _checkInitialized();
    return _voiceActivityDetectorAcceptWaveform!;
  }

  /// 检查语音段队列是否为空
  ///
  /// 返回 1 表示空，0 表示有语音段待处理
  static VoiceActivityDetectorEmptyDart get voiceActivityDetectorEmpty {
    _checkInitialized();
    return _voiceActivityDetectorEmpty!;
  }

  /// 检查是否检测到语音段
  ///
  /// 返回 1 表示检测到，0 表示未检测到
  /// 注意: 需要在 acceptWaveform 后调用
  static VoiceActivityDetectorDetectedDart get voiceActivityDetectorDetected {
    _checkInitialized();
    return _voiceActivityDetectorDetected!;
  }

  /// 弹出一个已处理的语音段
  ///
  /// 在调用 front() 获取语音段后，需要调用此函数移除
  static VoiceActivityDetectorPopDart get voiceActivityDetectorPop {
    _checkInitialized();
    return _voiceActivityDetectorPop!;
  }

  /// 清空所有缓冲区和待处理语音段
  static VoiceActivityDetectorClearDart get voiceActivityDetectorClear {
    _checkInitialized();
    return _voiceActivityDetectorClear!;
  }

  /// 刷新 VAD，处理剩余缓冲区数据
  ///
  /// 在输入结束时调用，确保处理所有剩余音频
  static VoiceActivityDetectorFlushDart get voiceActivityDetectorFlush {
    _checkInitialized();
    return _voiceActivityDetectorFlush!;
  }

  /// 获取队列中的第一个语音段
  ///
  /// 返回 SherpaOnnxSpeechSegment 指针
  /// 使用完毕后需调用 destroySpeechSegment() 释放
  static VoiceActivityDetectorFrontDart get voiceActivityDetectorFront {
    _checkInitialized();
    return _voiceActivityDetectorFront!;
  }

  /// 销毁语音段
  static DestroySpeechSegmentDart get destroySpeechSegment {
    _checkInitialized();
    return _destroySpeechSegment!;
  }

  /// 重置 VAD 状态
  ///
  /// 清空内部状态，准备处理新的音频流
  static VoiceActivityDetectorResetDart get voiceActivityDetectorReset {
    _checkInitialized();
    return _voiceActivityDetectorReset!;
  }

  static void _checkInitialized() {
    if (!_initialized) {
      throw StateError('SherpaOnnxVadBindings 未初始化，请先调用 init()');
    }
  }

  /// 初始化绑定
  ///
  /// [lib] 已加载的动态库
  static void init(DynamicLibrary lib) {
    if (_initialized) return;

    _createVoiceActivityDetector = lib.lookupFunction<
        CreateVoiceActivityDetectorNative,
        CreateVoiceActivityDetectorDart>('SherpaOnnxCreateVoiceActivityDetector');

    _destroyVoiceActivityDetector = lib.lookupFunction<
            DestroyVoiceActivityDetectorNative,
            DestroyVoiceActivityDetectorDart>(
        'SherpaOnnxDestroyVoiceActivityDetector');

    _voiceActivityDetectorAcceptWaveform = lib.lookupFunction<
            VoiceActivityDetectorAcceptWaveformNative,
            VoiceActivityDetectorAcceptWaveformDart>(
        'SherpaOnnxVoiceActivityDetectorAcceptWaveform');

    _voiceActivityDetectorEmpty = lib.lookupFunction<
        VoiceActivityDetectorEmptyNative,
        VoiceActivityDetectorEmptyDart>('SherpaOnnxVoiceActivityDetectorEmpty');

    _voiceActivityDetectorDetected = lib.lookupFunction<
            VoiceActivityDetectorDetectedNative,
            VoiceActivityDetectorDetectedDart>(
        'SherpaOnnxVoiceActivityDetectorDetected');

    _voiceActivityDetectorPop = lib.lookupFunction<
        VoiceActivityDetectorPopNative,
        VoiceActivityDetectorPopDart>('SherpaOnnxVoiceActivityDetectorPop');

    _voiceActivityDetectorClear = lib.lookupFunction<
        VoiceActivityDetectorClearNative,
        VoiceActivityDetectorClearDart>('SherpaOnnxVoiceActivityDetectorClear');

    _voiceActivityDetectorFlush = lib.lookupFunction<
        VoiceActivityDetectorFlushNative,
        VoiceActivityDetectorFlushDart>('SherpaOnnxVoiceActivityDetectorFlush');

    _voiceActivityDetectorFront = lib.lookupFunction<
        VoiceActivityDetectorFrontNative,
        VoiceActivityDetectorFrontDart>('SherpaOnnxVoiceActivityDetectorFront');

    _destroySpeechSegment =
        lib.lookupFunction<DestroySpeechSegmentNative, DestroySpeechSegmentDart>(
            'SherpaOnnxDestroySpeechSegment');

    _voiceActivityDetectorReset = lib.lookupFunction<
        VoiceActivityDetectorResetNative,
        VoiceActivityDetectorResetDart>('SherpaOnnxVoiceActivityDetectorReset');

    _initialized = true;
  }

  /// 重置绑定状态 (仅用于测试)
  static void resetForTesting() {
    _initialized = false;
    _createVoiceActivityDetector = null;
    _destroyVoiceActivityDetector = null;
    _voiceActivityDetectorAcceptWaveform = null;
    _voiceActivityDetectorEmpty = null;
    _voiceActivityDetectorDetected = null;
    _voiceActivityDetectorPop = null;
    _voiceActivityDetectorClear = null;
    _voiceActivityDetectorFlush = null;
    _voiceActivityDetectorFront = null;
    _destroySpeechSegment = null;
    _voiceActivityDetectorReset = null;
  }
}

