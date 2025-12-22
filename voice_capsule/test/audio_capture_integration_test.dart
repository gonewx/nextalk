import 'dart:ffi';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/audio_capture.dart';

@Tags(['integration'])
void main() {
  group('AudioCapture 集成测试', () {
    test('录音 3 秒并验证数据', () async {
      final capture = AudioCapture();
      final error = await capture.start();

      if (error != AudioCaptureError.none) {
        print('跳过测试: 设备不可用 ($error)');
        return;
      }

      print('开始录音 3 秒...');
      final samples = <double>[];

      // 30 次 x 100ms = 3 秒
      for (int i = 0; i < 30; i++) {
        final read = capture.read(capture.buffer, AudioConfig.framesPerBuffer);
        if (read > 0) {
          for (int j = 0; j < read; j++) {
            samples.add(capture.buffer[j]);
          }
        }
        await Future.delayed(const Duration(milliseconds: 100));
      }

      await capture.stop();
      capture.dispose();

      final nonZero = samples.where((s) => s.abs() > 0.001).length;
      print('总样本: ${samples.length}, 非零样本: $nonZero');

      // 验证采集到了数据
      expect(samples.length, greaterThan(0));
    });

    test('采样率和格式验证', () async {
      final capture = AudioCapture();
      final error = await capture.start();

      if (error != AudioCaptureError.none) {
        print('跳过测试: 设备不可用 ($error)');
        return;
      }

      // 验证配置正确
      expect(AudioConfig.sampleRate, equals(16000));
      expect(AudioConfig.channels, equals(1));
      expect(AudioConfig.framesPerBuffer, equals(1600));

      // 读取一帧数据
      final read = capture.read(capture.buffer, AudioConfig.framesPerBuffer);
      expect(read, equals(AudioConfig.framesPerBuffer));

      // 验证数据在有效范围内 (Float32: -1.0 ~ 1.0)
      for (int i = 0; i < read; i++) {
        final sample = capture.buffer[i];
        expect(sample, inInclusiveRange(-1.0, 1.0));
      }

      capture.dispose();
    });

    test('停止和重启功能', () async {
      final capture = AudioCapture();
      var error = await capture.start();

      if (error != AudioCaptureError.none) {
        print('跳过测试: 设备不可用 ($error)');
        return;
      }

      expect(capture.isCapturing, isTrue);

      // 停止
      await capture.stop();
      expect(capture.isCapturing, isFalse);

      // 清理并重新创建
      capture.dispose();

      // 重新创建实例并启动
      final capture2 = AudioCapture();
      error = await capture2.start();

      if (error == AudioCaptureError.none) {
        expect(capture2.isCapturing, isTrue);
        capture2.dispose();
      }
    });

    test('读取延迟测试', () async {
      final capture = AudioCapture();
      final error = await capture.start();

      if (error != AudioCaptureError.none) {
        print('跳过测试: 设备不可用 ($error)');
        return;
      }

      // M1 修复: 预热读取 - 跳过首次填充缓冲区的时间
      capture.read(capture.buffer, AudioConfig.framesPerBuffer);
      await Future.delayed(const Duration(milliseconds: 50));

      // 测量稳态延迟 (缓冲区已填充后的读取时间)
      // 1600 samples @ 16kHz = 100ms 阻塞时间 (物理限制)
      // 额外处理延迟应 < 50ms，即总时间应 < 150ms
      final stopwatch = Stopwatch()..start();
      final read = capture.read(capture.buffer, AudioConfig.framesPerBuffer);
      stopwatch.stop();

      print('读取 $read 样本耗时: ${stopwatch.elapsedMilliseconds}ms');
      print('  - 理论阻塞时间: 100ms (1600 samples @ 16kHz)');
      print('  - 额外处理延迟: ${stopwatch.elapsedMilliseconds - 100}ms');

      // AC2 验证: 处理延迟 < 50ms (总时间 < 150ms)
      // 阻塞时间 100ms + 允许的处理延迟 50ms = 150ms
      expect(stopwatch.elapsedMilliseconds, lessThan(150));

      capture.dispose();
    });

    test('缓冲区指针零拷贝验证', () async {
      final capture = AudioCapture();
      final error = await capture.start();

      if (error != AudioCaptureError.none) {
        print('跳过测试: 设备不可用 ($error)');
        return;
      }

      // 获取缓冲区指针
      final buffer1 = capture.buffer;
      final buffer2 = capture.buffer;

      // 验证是同一个指针 (零拷贝)
      expect(buffer1.address, equals(buffer2.address));

      // 验证缓冲区大小足够
      // 读取一帧验证缓冲区可用
      final read = capture.read(buffer1, AudioConfig.framesPerBuffer);
      expect(read, greaterThan(0));

      capture.dispose();
    });
  });
}
