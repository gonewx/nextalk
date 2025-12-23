import 'dart:ffi';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/ffi/sherpa_ffi.dart';
import 'package:voice_capsule/services/sherpa_service.dart';

void main() {
  group('SherpaService', () {
    group('模型验证', () {
      test('模型目录不存在时返回 modelNotFound 错误', () async {
        final service = SherpaService();

        final error = await service.initialize(
          const SherpaConfig(modelDir: '/nonexistent/path/to/model'),
        );

        expect(error, SherpaError.modelNotFound);
        expect(service.isInitialized, false);
        expect(service.lastError, SherpaError.modelNotFound);

        service.dispose();
      });

      test('tokens.txt 不存在时返回 tokensNotFound 错误', () async {
        // 创建临时目录，包含模型文件但缺少 tokens.txt
        final tempDir = Directory.systemTemp.createTempSync('sherpa_test_');
        try {
          // 创建模型文件占位符
          File('${tempDir.path}/encoder-epoch-99-avg-1-chunk-16-left-128.onnx')
              .writeAsStringSync('dummy');
          File('${tempDir.path}/decoder-epoch-99-avg-1-chunk-16-left-128.onnx')
              .writeAsStringSync('dummy');
          File('${tempDir.path}/joiner-epoch-99-avg-1-chunk-16-left-128.onnx')
              .writeAsStringSync('dummy');
          // 不创建 tokens.txt

          final service = SherpaService();
          final error = await service.initialize(
            SherpaConfig(modelDir: tempDir.path),
          );

          expect(error, SherpaError.tokensNotFound);
          expect(service.isInitialized, false);

          service.dispose();
        } finally {
          tempDir.deleteSync(recursive: true);
        }
      });

      test('encoder 模型不存在时返回 encoderNotFound 错误', () async {
        final tempDir = Directory.systemTemp.createTempSync('sherpa_test_');
        try {
          // 只创建部分文件
          File('${tempDir.path}/tokens.txt').writeAsStringSync('dummy');

          final service = SherpaService();
          final error = await service.initialize(
            SherpaConfig(modelDir: tempDir.path),
          );

          expect(error, SherpaError.encoderNotFound);
          expect(service.isInitialized, false);

          service.dispose();
        } finally {
          tempDir.deleteSync(recursive: true);
        }
      });
    });

    group('未初始化状态', () {
      test('未初始化时 isReady() 返回 false', () {
        final service = SherpaService();

        expect(service.isReady(), false);

        service.dispose();
      });

      test('未初始化时 getResult() 返回空结果', () {
        final service = SherpaService();

        final result = service.getResult();

        expect(result.text, '');
        expect(result.tokens, isEmpty);
        expect(result.timestamps, isEmpty);

        service.dispose();
      });

      test('未初始化时 isEndpoint() 返回 false', () {
        final service = SherpaService();

        expect(service.isEndpoint(), false);

        service.dispose();
      });

      test('未初始化时方法调用安全，不抛异常', () {
        final service = SherpaService();

        // 所有方法应安全返回，不抛异常
        expect(
            () => service.acceptWaveform(16000, nullptr, 0), returnsNormally);
        expect(() => service.decode(), returnsNormally);
        expect(() => service.reset(), returnsNormally);
        expect(() => service.inputFinished(), returnsNormally);
        expect(() => service.dispose(), returnsNormally);
      });
    });

    group('配置类', () {
      test('SherpaConfig 默认值正确', () {
        const config = SherpaConfig(modelDir: '/test');

        expect(config.modelDir, '/test');
        expect(config.numThreads, 2);
        expect(config.sampleRate, 16000);
        expect(config.featureDim, 80);
        expect(config.enableEndpoint, true);
        expect(config.rule1MinTrailingSilence, 2.4);
        expect(config.rule2MinTrailingSilence, 1.2);
        expect(config.rule3MinUtteranceLength, 20.0);
        expect(config.decodingMethod, 'greedy_search');
        expect(config.provider, 'cpu');
      });

      test('SherpaConfig toString 包含关键信息', () {
        const config = SherpaConfig(modelDir: '/test/model');
        final str = config.toString();

        expect(str, contains('/test/model'));
        expect(str, contains('numThreads'));
        expect(str, contains('sampleRate'));
      });
    });

    group('结果类', () {
      test('SherpaResult.empty() 返回空结果', () {
        final result = SherpaResult.empty();

        expect(result.text, '');
        expect(result.tokens, isEmpty);
        expect(result.timestamps, isEmpty);
      });

      test('SherpaResult toString 包含文本', () {
        const result = SherpaResult(
          text: '测试文本',
          tokens: ['测', '试', '文', '本'],
          timestamps: [0.1, 0.2, 0.3, 0.4],
        );

        expect(result.toString(), contains('测试文本'));
      });
    });

    group('初始化和清理流程 (需要真实模型)', () {
      late String modelDir;
      late bool modelExists;
      late bool libraryAvailable;

      setUpAll(() {
        modelDir = Platform.environment['SHERPA_MODEL_DIR'] ??
            '${Platform.environment['HOME']}/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en';
        modelExists = Directory(modelDir).existsSync();
        libraryAvailable = isSherpaLibraryAvailable();
      });

      test('使用真实模型初始化成功', () async {
        if (!libraryAvailable) {
          markTestSkipped('Sherpa 动态库不可用');
          return;
        }
        if (!modelExists) {
          markTestSkipped('模型目录不存在: $modelDir');
          return;
        }

        final service = SherpaService();
        final error = await service.initialize(
          SherpaConfig(modelDir: modelDir),
        );

        expect(error, SherpaError.none);
        expect(service.isInitialized, true);
        expect(service.lastError, SherpaError.none);

        service.dispose();
        expect(service.isInitialized, false);
      });

      test('重复初始化返回 none', () async {
        if (!libraryAvailable) {
          markTestSkipped('Sherpa 动态库不可用');
          return;
        }
        if (!modelExists) {
          markTestSkipped('模型目录不存在: $modelDir');
          return;
        }

        final service = SherpaService();
        await service.initialize(SherpaConfig(modelDir: modelDir));

        // 第二次初始化应直接返回 none
        final error = await service.initialize(
          SherpaConfig(modelDir: modelDir),
        );

        expect(error, SherpaError.none);

        service.dispose();
      });
    });
  });
}
