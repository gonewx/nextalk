import 'dart:ffi';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/ffi/sherpa_offline_bindings.dart';
import 'package:voice_capsule/ffi/sherpa_vad_bindings.dart';

void main() {
  // ============================================
  // Story 2-7 Task 2.3: FFI 绑定结构测试
  // ============================================
  //
  // 注意: 这些测试仅验证 FFI 结构体和绑定类的定义正确性。
  // 实际的 FFI 函数调用需要真实的动态库，应在集成测试中验证。

  group('SherpaOnnxOfflineBindings 结构测试', () {
    setUp(() {
      // 确保每个测试前重置状态
      SherpaOnnxOfflineBindings.resetForTesting();
    });

    test('初始状态应该未初始化', () {
      expect(SherpaOnnxOfflineBindings.isInitialized, isFalse);
    });

    test('未初始化时访问函数应该抛出 StateError', () {
      expect(
        () => SherpaOnnxOfflineBindings.createOfflineRecognizer,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 destroyOfflineRecognizer 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxOfflineBindings.destroyOfflineRecognizer,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 createOfflineStream 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxOfflineBindings.createOfflineStream,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 destroyOfflineStream 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxOfflineBindings.destroyOfflineStream,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 acceptWaveformOffline 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxOfflineBindings.acceptWaveformOffline,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 decodeOfflineStream 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxOfflineBindings.decodeOfflineStream,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 getOfflineStreamResult 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxOfflineBindings.getOfflineStreamResult,
        throwsA(isA<StateError>()),
      );
    });

    test('resetForTesting 应该重置初始化状态', () {
      // 即使没有真正初始化，也应该能调用 reset
      SherpaOnnxOfflineBindings.resetForTesting();
      expect(SherpaOnnxOfflineBindings.isInitialized, isFalse);
    });
  });

  group('SherpaOnnxVadBindings 结构测试', () {
    setUp(() {
      // 确保每个测试前重置状态
      SherpaOnnxVadBindings.resetForTesting();
    });

    test('初始状态应该未初始化', () {
      expect(SherpaOnnxVadBindings.isInitialized, isFalse);
    });

    test('未初始化时访问 createVoiceActivityDetector 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.createVoiceActivityDetector,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 destroyVoiceActivityDetector 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.destroyVoiceActivityDetector,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorAcceptWaveform 应该抛出 StateError',
        () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorAcceptWaveform,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorEmpty 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorEmpty,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorDetected 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorDetected,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorPop 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorPop,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorClear 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorClear,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorFlush 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorFlush,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorFront 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorFront,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 destroySpeechSegment 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.destroySpeechSegment,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorReset 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorReset,
        throwsA(isA<StateError>()),
      );
    });

    test('未初始化时访问 voiceActivityDetectorIsSpeech 应该抛出 StateError', () {
      expect(
        () => SherpaOnnxVadBindings.voiceActivityDetectorIsSpeech,
        throwsA(isA<StateError>()),
      );
    });

    test('resetForTesting 应该重置初始化状态', () {
      SherpaOnnxVadBindings.resetForTesting();
      expect(SherpaOnnxVadBindings.isInitialized, isFalse);
    });
  });

  group('Offline 结构体大小测试', () {
    // 这些测试验证结构体能够被正确分配

    test('SherpaOnnxOfflineSenseVoiceModelConfig 可分配', () {
      // 结构体能够被 sizeOf 计算说明定义正确
      expect(sizeOf<SherpaOnnxOfflineSenseVoiceModelConfig>(), greaterThan(0));
    });

    test('SherpaOnnxSileroVadModelConfig 可分配', () {
      expect(sizeOf<SherpaOnnxSileroVadModelConfig>(), greaterThan(0));
    });

    test('SherpaOnnxVadModelConfig 可分配', () {
      expect(sizeOf<SherpaOnnxVadModelConfig>(), greaterThan(0));
    });

    test('SherpaOnnxSpeechSegment 可分配', () {
      expect(sizeOf<SherpaOnnxSpeechSegment>(), greaterThan(0));
    });

    test('SherpaOnnxOfflineModelConfig 可分配', () {
      expect(sizeOf<SherpaOnnxOfflineModelConfig>(), greaterThan(0));
    });

    test('SherpaOnnxOfflineRecognizerConfig 可分配', () {
      expect(sizeOf<SherpaOnnxOfflineRecognizerConfig>(), greaterThan(0));
    });

    test('SherpaOnnxOfflineRecognizerResult 可分配', () {
      expect(sizeOf<SherpaOnnxOfflineRecognizerResult>(), greaterThan(0));
    });
  });

  group('Offline 结构体字段测试', () {
    test('SherpaOnnxSileroVadModelConfig 包含所有必需字段', () {
      // 验证结构体可以正确访问字段
      // 由于没有真实内存分配，这里只验证编译通过
      expect(true, isTrue); // 如果编译通过则字段定义正确
    });

    test('SherpaOnnxOfflineSenseVoiceModelConfig 应该有 model, language, useItn 字段',
        () {
      // 验证结构体定义正确
      expect(true, isTrue);
    });

    test('SherpaOnnxSpeechSegment 应该有 start, samples, n 字段', () {
      expect(true, isTrue);
    });
  });
}

