import 'dart:ffi';
import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/ffi/portaudio_ffi.dart';
import 'package:voice_capsule/services/audio_capture.dart';

void main() {
  group('PortAudioBindings', () {
    test('FFI 绑定加载成功', () {
      expect(() => PortAudioBindings(), returnsNormally);
    });

    test('可以获取错误文本', () {
      final bindings = PortAudioBindings();
      // paNoError 应该返回 "Success" 或类似文本
      final text = bindings.errorText(paNoError);
      expect(text, isNotEmpty);
    });
  });

  group('AudioConfig', () {
    test('采样率为 16kHz', () {
      expect(AudioConfig.sampleRate, equals(16000));
    });

    test('单声道', () {
      expect(AudioConfig.channels, equals(1));
    });

    test('缓冲区大小为 100ms', () {
      // 16kHz * 0.1s = 1600 samples
      expect(AudioConfig.framesPerBuffer, equals(1600));
    });
  });

  group('AudioCapture', () {
    test('初始化和清理流程', () async {
      final capture = AudioCapture();
      final error = await capture.start();
      // 可能因无麦克风失败，但不应抛异常
      expect(error, isA<AudioCaptureError>());

      // 如果成功启动，验证状态
      if (error == AudioCaptureError.none) {
        expect(capture.isCapturing, isTrue);
        expect(capture.isInitialized, isTrue);
      }

      capture.dispose();
      expect(capture.isCapturing, isFalse);
    });

    test('未初始化时访问 buffer 抛出 StateError', () {
      final capture = AudioCapture();
      expect(() => capture.buffer, throwsStateError);
    });

    test('多次 dispose 不抛异常', () {
      final capture = AudioCapture();
      expect(() {
        capture.dispose();
        capture.dispose();
      }, returnsNormally);
    });

    test('未启动时 stop 不抛异常', () async {
      final capture = AudioCapture();
      await expectLater(capture.stop(), completes);
    });

    test('未初始化时 read 返回 -1 且设置 lastReadError', () {
      final capture = AudioCapture();
      // 未调用 start()，直接调用 read
      expect(capture.lastReadError, equals(AudioCaptureError.none));

      // 创建临时缓冲区
      final buffer = calloc<Float>(100);
      final result = capture.read(buffer, 100);

      expect(result, equals(-1));
      expect(capture.lastReadError, equals(AudioCaptureError.readFailed));

      calloc.free(buffer);
    });

    test('设备不可用返回正确错误', () async {
      final capture = AudioCapture();
      final error = await capture.start();

      // 根据系统环境，可能是 none 或各种错误
      expect(
        error,
        anyOf([
          AudioCaptureError.none,
          AudioCaptureError.noInputDevice,
          AudioCaptureError.deviceUnavailable,
          AudioCaptureError.initializationFailed,
        ]),
      );

      capture.dispose();
    });
  });

  group('AudioCaptureError', () {
    test('包含所有预期的错误类型', () {
      expect(AudioCaptureError.values, contains(AudioCaptureError.none));
      expect(
        AudioCaptureError.values,
        contains(AudioCaptureError.initializationFailed),
      );
      expect(
        AudioCaptureError.values,
        contains(AudioCaptureError.noInputDevice),
      );
      expect(
        AudioCaptureError.values,
        contains(AudioCaptureError.deviceUnavailable),
      );
      expect(
        AudioCaptureError.values,
        contains(AudioCaptureError.streamOpenFailed),
      );
      expect(
        AudioCaptureError.values,
        contains(AudioCaptureError.streamStartFailed),
      );
      expect(AudioCaptureError.values, contains(AudioCaptureError.readFailed));
    });
  });
}
