import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/audio_capture.dart';
import 'package:voice_capsule/services/sherpa_service.dart';

void main() {
  late String modelDir;
  late bool modelExists;

  setUpAll(() {
    modelDir = Platform.environment['SHERPA_MODEL_DIR'] ??
        '${Platform.environment['HOME']}/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en';
    modelExists = Directory(modelDir).existsSync();
  });

  group('Sherpa Integration Tests', () {
    test(
      '零拷贝音频送入与识别',
      () async {
        if (!modelExists) {
          markTestSkipped('模型不存在: $modelDir');
          return;
        }

        // 初始化 Sherpa
        final sherpa = SherpaService();
        final sherpaError = await sherpa.initialize(
          SherpaConfig(modelDir: modelDir),
        );

        if (sherpaError != SherpaError.none) {
          print('Sherpa 初始化失败: $sherpaError');
          return;
        }

        expect(sherpa.isInitialized, true);

        // 初始化音频采集
        final audio = AudioCapture();
        final audioError = await audio.start();

        if (audioError != AudioCaptureError.none) {
          print('音频初始化失败: $audioError');
          sherpa.dispose();
          return;
        }

        expect(audio.isCapturing, true);

        print('开始录音识别 5 秒...');
        final stopwatch = Stopwatch()..start();

        for (int i = 0; i < 50; i++) {
          final read = audio.read(audio.buffer, AudioConfig.framesPerBuffer);
          if (read <= 0) continue;

          // 零拷贝送入 (同一 Pointer<Float>)
          final t1 = stopwatch.elapsedMicroseconds;
          sherpa.acceptWaveform(AudioConfig.sampleRate, audio.buffer, read);

          while (sherpa.isReady()) {
            sherpa.decode();
          }
          final t2 = stopwatch.elapsedMicroseconds;

          final result = sherpa.getResult();
          if (result.text.isNotEmpty) {
            print('[$i] 结果: ${result.text}');
          }

          // 检测端点
          if (sherpa.isEndpoint()) {
            print('[$i] 检测到端点');
            sherpa.reset();
          }

          // 性能验证: < 50ms (含解码)
          final processTimeMs = (t2 - t1) / 1000.0;
          if (i > 5) {
            // 跳过前几帧的冷启动
            expect(
              processTimeMs,
              lessThan(50),
              reason: '处理时间 ${processTimeMs}ms 超过 50ms 阈值',
            );
          }

          await Future.delayed(const Duration(milliseconds: 100));
        }

        await audio.stop();
        audio.dispose();
        sherpa.dispose();

        expect(sherpa.isInitialized, false);
        expect(audio.isCapturing, false);

        print('测试完成');
      },
      tags: ['integration'],
      timeout: const Timeout(Duration(seconds: 30)),
    );

    test(
      '端点检测功能验证',
      () async {
        if (!modelExists) {
          markTestSkipped('模型不存在: $modelDir');
          return;
        }

        final sherpa = SherpaService();
        final error = await sherpa.initialize(
          SherpaConfig(
            modelDir: modelDir,
            enableEndpoint: true,
            rule1MinTrailingSilence: 1.0, // 较短的阈值便于测试
            rule2MinTrailingSilence: 0.5,
          ),
        );

        if (error != SherpaError.none) {
          fail('初始化失败: $error');
        }

        expect(sherpa.isInitialized, true);

        // 初始状态不应检测到端点
        expect(sherpa.isEndpoint(), false);

        sherpa.dispose();
      },
      tags: ['integration'],
    );

    test(
      'reset 后可继续识别',
      () async {
        if (!modelExists) {
          markTestSkipped('模型不存在: $modelDir');
          return;
        }

        final sherpa = SherpaService();
        final error = await sherpa.initialize(SherpaConfig(modelDir: modelDir));

        if (error != SherpaError.none) {
          fail('初始化失败: $error');
        }

        // 重置
        sherpa.reset();

        // 重置后应该仍然可以使用
        expect(sherpa.isInitialized, true);
        expect(sherpa.isReady(), false); // 无数据时不就绪

        sherpa.dispose();
      },
      tags: ['integration'],
    );

    test(
      '性能基准: 处理 100ms 音频块耗时 < 10ms',
      () async {
        if (!modelExists) {
          markTestSkipped('模型不存在: $modelDir');
          return;
        }

        final sherpa = SherpaService();
        final error = await sherpa.initialize(
          SherpaConfig(modelDir: modelDir),
        );

        if (error != SherpaError.none) {
          fail('初始化失败: $error');
        }

        // 分配测试缓冲区 (1600 samples = 100ms @ 16kHz)
        final buffer = calloc<Float>(1600);
        try {
          // 填充静音数据
          for (int i = 0; i < 1600; i++) {
            buffer[i] = 0.0;
          }

          final stopwatch = Stopwatch();
          final times = <double>[];

          // 预热
          for (int i = 0; i < 5; i++) {
            sherpa.acceptWaveform(16000, buffer, 1600);
            while (sherpa.isReady()) {
              sherpa.decode();
            }
          }

          // 测量
          for (int i = 0; i < 20; i++) {
            stopwatch.reset();
            stopwatch.start();

            sherpa.acceptWaveform(16000, buffer, 1600);
            while (sherpa.isReady()) {
              sherpa.decode();
            }

            stopwatch.stop();
            times.add(stopwatch.elapsedMicroseconds / 1000.0);
          }

          final avgTime = times.reduce((a, b) => a + b) / times.length;
          final maxTime = times.reduce((a, b) => a > b ? a : b);

          print('平均处理时间: ${avgTime.toStringAsFixed(2)}ms');
          print('最大处理时间: ${maxTime.toStringAsFixed(2)}ms');

          // AC3 要求: 100ms 音频块处理耗时 < 10ms
          expect(
            avgTime,
            lessThan(10),
            reason: '平均处理时间 ${avgTime}ms 超过 10ms 阈值',
          );
        } finally {
          calloc.free(buffer);
          sherpa.dispose();
        }
      },
      tags: ['integration', 'performance'],
      timeout: const Timeout(Duration(seconds: 60)),
    );
  });
}
