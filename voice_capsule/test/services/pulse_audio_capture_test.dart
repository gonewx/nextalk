import 'dart:ffi';
import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/ffi/libpulse_simple_ffi.dart';
import 'package:voice_capsule/services/pulse_audio_capture.dart';

/// PulseAudio 缓冲属性防回归测试
///
/// libpulse-simple 无法在测试环境注入 fake bindings，
/// 因此测试聚焦于 FFI 结构体布局与 fragsize 常量推导的正确性:
/// - PaBufferAttr 必须与 C 的 pa_buffer_attr 布局一致 (5 个 uint32_t)
/// - fragsize = framesPerBuffer * 4 = 6400 bytes (100ms @ 16kHz Float32)
void main() {
  group('PaBufferAttr 结构体布局', () {
    test('大小与 C 的 pa_buffer_attr 一致 (5 x uint32 = 20 bytes)', () {
      expect(sizeOf<PaBufferAttr>(), 20);
    });

    test('字段顺序为 maxlength/tlength/prebuf/minreq/fragsize', () {
      final attr = calloc<PaBufferAttr>();
      try {
        attr.ref.maxlength = 1;
        attr.ref.tlength = 2;
        attr.ref.prebuf = 3;
        attr.ref.minreq = 4;
        attr.ref.fragsize = 5;

        // 按内存布局逐 uint32 读取，验证字段偏移与 C 结构体一致
        final raw = attr.cast<Uint32>().asTypedList(5);
        expect(raw, [1, 2, 3, 4, 5]);
      } finally {
        calloc.free(attr);
      }
    });

    test('字段可容纳 0xFFFFFFFF (-1: 服务端默认)', () {
      final attr = calloc<PaBufferAttr>();
      try {
        attr.ref.maxlength = 0xFFFFFFFF;
        expect(attr.ref.maxlength, 0xFFFFFFFF);
      } finally {
        calloc.free(attr);
      }
    });
  });

  group('fragsize 常量推导', () {
    test('framesPerBuffer 为 100ms @ 16kHz', () {
      expect(PulseAudioConfig.framesPerBuffer, 1600);
      expect(PulseAudioConfig.sampleRate, 16000);
    });

    test('fragsizeBytes = framesPerBuffer x sizeOf<Float> = 6400 (与循环节拍对齐)', () {
      // 锁定 initialize() 实际写入 fragsize 的同一来源
      expect(PulseAudioConfig.fragsizeBytes, 6400);
      expect(PulseAudioConfig.fragsizeBytes,
          PulseAudioConfig.framesPerBuffer * sizeOf<Float>());
    });
  });
}
