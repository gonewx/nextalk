import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/asr/asr_engine_factory.dart';
import 'package:voice_capsule/services/asr/sensevoice_engine.dart';
import 'package:voice_capsule/services/asr/zipformer_engine.dart';

void main() {
  // ============================================
  // Story 2-7 Task 1.6: ASR 引擎抽象层单元测试
  // ============================================

  group('ASREngineType 枚举', () {
    test('应该包含 zipformer 类型', () {
      expect(ASREngineType.values, contains(ASREngineType.zipformer));
    });

    test('应该包含 sensevoice 类型', () {
      expect(ASREngineType.values, contains(ASREngineType.sensevoice));
    });

    test('应该有且仅有 2 种引擎类型', () {
      expect(ASREngineType.values.length, equals(2));
    });
  });

  group('ASRError 枚举', () {
    test('应该包含 none 错误类型', () {
      expect(ASRError.values, contains(ASRError.none));
    });

    test('应该包含 libraryLoadFailed 错误类型', () {
      expect(ASRError.values, contains(ASRError.libraryLoadFailed));
    });

    test('应该包含 modelNotFound 错误类型', () {
      expect(ASRError.values, contains(ASRError.modelNotFound));
    });

    test('应该包含 modelFileMissing 错误类型', () {
      expect(ASRError.values, contains(ASRError.modelFileMissing));
    });

    test('应该包含 recognizerCreateFailed 错误类型', () {
      expect(ASRError.values, contains(ASRError.recognizerCreateFailed));
    });

    test('应该包含 streamCreateFailed 错误类型', () {
      expect(ASRError.values, contains(ASRError.streamCreateFailed));
    });

    test('应该包含 notInitialized 错误类型', () {
      expect(ASRError.values, contains(ASRError.notInitialized));
    });

    test('应该包含 vadInitFailed 错误类型', () {
      expect(ASRError.values, contains(ASRError.vadInitFailed));
    });

    test('应该包含 invalidConfig 错误类型', () {
      expect(ASRError.values, contains(ASRError.invalidConfig));
    });

    test('应该有 9 种错误类型', () {
      expect(ASRError.values.length, equals(9));
    });
  });

  group('ZipformerConfig 类', () {
    test('应该正确创建默认配置', () {
      const config = ZipformerConfig(modelDir: '/test/path');

      expect(config.modelDir, equals('/test/path'));
      expect(config.numThreads, equals(2));
      expect(config.sampleRate, equals(16000));
      expect(config.useInt8Model, isTrue);
      expect(config.featureDim, equals(80));
      expect(config.enableEndpoint, isTrue);
      expect(config.rule1MinTrailingSilence, equals(2.4));
      expect(config.rule2MinTrailingSilence, equals(1.2));
      expect(config.rule3MinUtteranceLength, equals(20.0));
      expect(config.decodingMethod, equals('greedy_search'));
      expect(config.provider, equals('cpu'));
    });

    test('应该正确创建自定义配置', () {
      const config = ZipformerConfig(
        modelDir: '/custom/path',
        numThreads: 4,
        sampleRate: 8000,
        useInt8Model: false,
        featureDim: 40,
        enableEndpoint: false,
        rule1MinTrailingSilence: 3.0,
        rule2MinTrailingSilence: 2.0,
        rule3MinUtteranceLength: 30.0,
        decodingMethod: 'modified_beam_search',
        provider: 'cuda',
      );

      expect(config.modelDir, equals('/custom/path'));
      expect(config.numThreads, equals(4));
      expect(config.sampleRate, equals(8000));
      expect(config.useInt8Model, isFalse);
      expect(config.featureDim, equals(40));
      expect(config.enableEndpoint, isFalse);
      expect(config.rule1MinTrailingSilence, equals(3.0));
      expect(config.rule2MinTrailingSilence, equals(2.0));
      expect(config.rule3MinUtteranceLength, equals(30.0));
      expect(config.decodingMethod, equals('modified_beam_search'));
      expect(config.provider, equals('cuda'));
    });

    test('toString() 应该返回有意义的字符串', () {
      const config = ZipformerConfig(modelDir: '/test/path');
      final str = config.toString();

      expect(str, contains('ZipformerConfig'));
      expect(str, contains('/test/path'));
      expect(str, contains('useInt8Model'));
    });
  });

  group('SenseVoiceConfig 类', () {
    test('应该正确创建默认配置', () {
      const config = SenseVoiceConfig(
        modelDir: '/test/path',
        vadModelPath: '/vad/path',
      );

      expect(config.modelDir, equals('/test/path'));
      expect(config.vadModelPath, equals('/vad/path'));
      expect(config.numThreads, equals(2));
      expect(config.sampleRate, equals(16000));
      expect(config.useItn, isTrue);
      expect(config.language, equals('auto'));
      expect(config.vadThreshold, equals(0.25));
      expect(config.minSilenceDuration, equals(0.5));
      expect(config.minSpeechDuration, equals(0.5));
      expect(config.maxSpeechDuration, equals(10.0));
      expect(config.vadWindowSize, equals(512));
      expect(config.provider, equals('cpu'));
    });

    test('应该正确创建自定义配置', () {
      const config = SenseVoiceConfig(
        modelDir: '/custom/path',
        vadModelPath: '/custom/vad',
        numThreads: 4,
        sampleRate: 8000,
        useItn: false,
        language: 'zh',
        vadThreshold: 0.5,
        minSilenceDuration: 1.0,
        minSpeechDuration: 0.25,
        maxSpeechDuration: 30.0,
        vadWindowSize: 256,
        provider: 'cuda',
      );

      expect(config.modelDir, equals('/custom/path'));
      expect(config.vadModelPath, equals('/custom/vad'));
      expect(config.numThreads, equals(4));
      expect(config.sampleRate, equals(8000));
      expect(config.useItn, isFalse);
      expect(config.language, equals('zh'));
      expect(config.vadThreshold, equals(0.5));
      expect(config.minSilenceDuration, equals(1.0));
      expect(config.minSpeechDuration, equals(0.25));
      expect(config.maxSpeechDuration, equals(30.0));
      expect(config.vadWindowSize, equals(256));
      expect(config.provider, equals('cuda'));
    });

    test('toString() 应该返回有意义的字符串', () {
      const config = SenseVoiceConfig(
        modelDir: '/test/path',
        vadModelPath: '/vad/path',
      );
      final str = config.toString();

      expect(str, contains('SenseVoiceConfig'));
      expect(str, contains('/test/path'));
      expect(str, contains('/vad/path'));
    });
  });

  group('ASRResult 类', () {
    test('应该正确创建结果对象', () {
      const result = ASRResult(
        text: '你好世界',
        lang: 'zh',
        emotion: 'NEUTRAL',
        tokens: ['你', '好', '世', '界'],
        timestamps: [0.1, 0.2, 0.3, 0.4],
      );

      expect(result.text, equals('你好世界'));
      expect(result.lang, equals('zh'));
      expect(result.emotion, equals('NEUTRAL'));
      expect(result.tokens, equals(['你', '好', '世', '界']));
      expect(result.timestamps, equals([0.1, 0.2, 0.3, 0.4]));
    });

    test('应该正确创建空结果', () {
      final result = ASRResult.empty();

      expect(result.text, isEmpty);
      expect(result.lang, isNull);
      expect(result.emotion, isNull);
      expect(result.tokens, isEmpty);
      expect(result.timestamps, isEmpty);
    });

    test('isEmpty 应该正确判断空结果', () {
      final emptyResult = ASRResult.empty();
      const nonEmptyResult = ASRResult(text: '测试');

      expect(emptyResult.isEmpty, isTrue);
      expect(emptyResult.isNotEmpty, isFalse);
      expect(nonEmptyResult.isEmpty, isFalse);
      expect(nonEmptyResult.isNotEmpty, isTrue);
    });

    test('应该正确实现 == 运算符', () {
      const result1 = ASRResult(text: '测试', lang: 'zh', emotion: 'HAPPY');
      const result2 = ASRResult(text: '测试', lang: 'zh', emotion: 'HAPPY');
      const result3 = ASRResult(text: '不同', lang: 'zh', emotion: 'HAPPY');

      expect(result1 == result2, isTrue);
      expect(result1 == result3, isFalse);
    });

    test('应该正确实现 hashCode', () {
      const result1 = ASRResult(text: '测试', lang: 'zh', emotion: 'HAPPY');
      const result2 = ASRResult(text: '测试', lang: 'zh', emotion: 'HAPPY');

      expect(result1.hashCode, equals(result2.hashCode));
    });

    test('toString() 应该返回有意义的字符串', () {
      const result = ASRResult(text: '测试', lang: 'zh', emotion: 'HAPPY');
      final str = result.toString();

      expect(str, contains('ASRResult'));
      expect(str, contains('测试'));
      expect(str, contains('zh'));
      expect(str, contains('HAPPY'));
    });

    test('默认 tokens 和 timestamps 应该是空列表', () {
      const result = ASRResult(text: '测试');

      expect(result.tokens, isEmpty);
      expect(result.timestamps, isEmpty);
    });
  });

  group('ASREngineFactory 类', () {
    test('create() 应该创建 ZipformerEngine', () {
      final engine = ASREngineFactory.create(ASREngineType.zipformer);

      expect(engine, isA<ZipformerEngine>());
      expect(engine.engineType, equals(ASREngineType.zipformer));
    });

    test('create() 应该创建带调试日志的 ZipformerEngine', () {
      final engine = ASREngineFactory.create(
        ASREngineType.zipformer,
        enableDebugLog: true,
      );

      expect(engine, isA<ZipformerEngine>());
    });

    test('create() 应该创建 SenseVoiceEngine', () {
      final engine = ASREngineFactory.create(ASREngineType.sensevoice);

      expect(engine, isA<SenseVoiceEngine>());
      expect(engine.engineType, equals(ASREngineType.sensevoice));
    });

    test('create() 应该创建带调试日志的 SenseVoiceEngine', () {
      final engine = ASREngineFactory.create(
        ASREngineType.sensevoice,
        enableDebugLog: true,
      );

      expect(engine, isA<SenseVoiceEngine>());
    });

    test('createConfig() 应该创建 ZipformerConfig', () {
      final config = ASREngineFactory.createConfig(
        ASREngineType.zipformer,
        modelDir: '/test/path',
      );

      expect(config, isA<ZipformerConfig>());
      expect(config.modelDir, equals('/test/path'));
    });

    test('createConfig() 应该创建带自定义参数的 ZipformerConfig', () {
      final config = ASREngineFactory.createConfig(
        ASREngineType.zipformer,
        modelDir: '/test/path',
        useInt8Model: false,
        enableEndpoint: false,
        rule2MinTrailingSilence: 2.5,
      );

      expect(config, isA<ZipformerConfig>());
      final zipformerConfig = config as ZipformerConfig;
      expect(zipformerConfig.useInt8Model, isFalse);
      expect(zipformerConfig.enableEndpoint, isFalse);
      expect(zipformerConfig.rule2MinTrailingSilence, equals(2.5));
    });

    test('createConfig() 应该创建 SenseVoiceConfig', () {
      final config = ASREngineFactory.createConfig(
        ASREngineType.sensevoice,
        modelDir: '/test/path',
        vadModelPath: '/vad/path',
      );

      expect(config, isA<SenseVoiceConfig>());
      expect(config.modelDir, equals('/test/path'));
      final senseVoiceConfig = config as SenseVoiceConfig;
      expect(senseVoiceConfig.vadModelPath, equals('/vad/path'));
    });

    test('createConfig() 应该对 SenseVoice 缺少 vadModelPath 时抛出 ArgumentError',
        () {
      expect(
        () => ASREngineFactory.createConfig(
          ASREngineType.sensevoice,
          modelDir: '/test/path',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('createConfig() 应该创建带自定义参数的 SenseVoiceConfig', () {
      final config = ASREngineFactory.createConfig(
        ASREngineType.sensevoice,
        modelDir: '/test/path',
        vadModelPath: '/vad/path',
        useItn: false,
        language: 'zh',
      );

      expect(config, isA<SenseVoiceConfig>());
      final senseVoiceConfig = config as SenseVoiceConfig;
      expect(senseVoiceConfig.useItn, isFalse);
      expect(senseVoiceConfig.language, equals('zh'));
    });
  });

  group('ZipformerEngine 类', () {
    test('初始状态应该未初始化', () {
      final engine = ZipformerEngine();

      expect(engine.isInitialized, isFalse);
      expect(engine.engineType, equals(ASREngineType.zipformer));
      expect(engine.lastError, equals(ASRError.none));
    });

    test('初始化前调用方法应该安全返回', () {
      final engine = ZipformerEngine();

      // 这些方法应该不会崩溃
      expect(engine.isReady(), isFalse);
      expect(engine.isEndpoint(), isFalse);
      expect(engine.getResult().isEmpty, isTrue);

      // void 方法也应该安全
      engine.decode();
      engine.reset();
      engine.inputFinished();
    });

    test('dispose() 后状态应该正确', () {
      final engine = ZipformerEngine();
      engine.dispose();

      expect(engine.isInitialized, isFalse);
    });

    test('传入错误配置类型应该返回 invalidConfig', () async {
      final engine = ZipformerEngine();
      const wrongConfig = SenseVoiceConfig(
        modelDir: '/test',
        vadModelPath: '/vad',
      );

      final error = await engine.initialize(wrongConfig);

      expect(error, equals(ASRError.invalidConfig));
      expect(engine.lastError, equals(ASRError.invalidConfig));
    });

    test('模型目录不存在时应该返回 modelNotFound', () async {
      final engine = ZipformerEngine();
      const config = ZipformerConfig(
        modelDir: '/nonexistent/path/that/does/not/exist',
      );

      final error = await engine.initialize(config);

      expect(error, equals(ASRError.modelNotFound));
      expect(engine.lastError, equals(ASRError.modelNotFound));
    });
  });

  group('ASRConfig 继承层次', () {
    test('ZipformerConfig 应该是 ASRConfig 的子类', () {
      const config = ZipformerConfig(modelDir: '/test');
      expect(config, isA<ASRConfig>());
    });

    test('SenseVoiceConfig 应该是 ASRConfig 的子类', () {
      const config = SenseVoiceConfig(
        modelDir: '/test',
        vadModelPath: '/vad',
      );
      expect(config, isA<ASRConfig>());
    });

    test('两种配置应该共享基类属性', () {
      const zipConfig = ZipformerConfig(modelDir: '/zip', numThreads: 4);
      const senseConfig = SenseVoiceConfig(
        modelDir: '/sense',
        vadModelPath: '/vad',
        numThreads: 8,
      );

      // 通过 ASRConfig 类型引用访问共享属性
      ASRConfig config1 = zipConfig;
      ASRConfig config2 = senseConfig;

      expect(config1.modelDir, equals('/zip'));
      expect(config1.numThreads, equals(4));
      expect(config2.modelDir, equals('/sense'));
      expect(config2.numThreads, equals(8));
    });
  });

  // ============================================
  // Story 2-7 Task 3.9: SenseVoiceEngine 单元测试
  // ============================================

  group('SenseVoiceEngine 类', () {
    test('初始状态应该未初始化', () {
      final engine = SenseVoiceEngine();

      expect(engine.isInitialized, isFalse);
      expect(engine.engineType, equals(ASREngineType.sensevoice));
      expect(engine.lastError, equals(ASRError.none));
    });

    test('初始化前调用方法应该安全返回', () {
      final engine = SenseVoiceEngine();

      // 这些方法应该不会崩溃
      expect(engine.isReady(), isFalse);
      expect(engine.isEndpoint(), isFalse);
      expect(engine.getResult().isEmpty, isTrue);

      // void 方法也应该安全
      engine.decode();
      engine.reset();
      engine.inputFinished();
    });

    test('dispose() 后状态应该正确', () {
      final engine = SenseVoiceEngine();
      engine.dispose();

      expect(engine.isInitialized, isFalse);
    });

    test('传入错误配置类型应该返回 invalidConfig', () async {
      final engine = SenseVoiceEngine();
      const wrongConfig = ZipformerConfig(modelDir: '/test');

      final error = await engine.initialize(wrongConfig);

      expect(error, equals(ASRError.invalidConfig));
      expect(engine.lastError, equals(ASRError.invalidConfig));
    });

    test('模型目录不存在时应该返回 modelNotFound', () async {
      final engine = SenseVoiceEngine();
      const config = SenseVoiceConfig(
        modelDir: '/nonexistent/path/that/does/not/exist',
        vadModelPath: '/nonexistent/vad.onnx',
      );

      final error = await engine.initialize(config);

      expect(error, equals(ASRError.modelNotFound));
      expect(engine.lastError, equals(ASRError.modelNotFound));
    });

    test('引擎类型应该是 sensevoice', () {
      final engine = SenseVoiceEngine();
      expect(engine.engineType, equals(ASREngineType.sensevoice));
    });

    test('isReady() 应该始终返回 false (非流式引擎)', () {
      final engine = SenseVoiceEngine();
      // SenseVoice 引擎不使用 isReady 机制
      expect(engine.isReady(), isFalse);
    });

    test('初始 getResult() 应该返回空结果', () {
      final engine = SenseVoiceEngine();
      final result = engine.getResult();

      expect(result.isEmpty, isTrue);
      expect(result.text, isEmpty);
    });

    test('isEndpoint() 调用后应该重置标志', () {
      final engine = SenseVoiceEngine();

      // 第一次调用
      final first = engine.isEndpoint();
      expect(first, isFalse);

      // 连续调用应该一直是 false (因为没有音频数据)
      final second = engine.isEndpoint();
      expect(second, isFalse);
    });

    test('多次 dispose() 不应该崩溃', () {
      final engine = SenseVoiceEngine();

      // 多次调用 dispose 应该安全
      engine.dispose();
      engine.dispose();
      engine.dispose();

      expect(engine.isInitialized, isFalse);
    });

    test('dispose() 后调用方法应该安全', () {
      final engine = SenseVoiceEngine();
      engine.dispose();

      // 这些方法应该不会崩溃
      expect(engine.isReady(), isFalse);
      expect(engine.isEndpoint(), isFalse);
      expect(engine.getResult().isEmpty, isTrue);

      engine.decode();
      engine.reset();
      engine.inputFinished();
    });

    test('enableDebugLog 参数应该被保存', () {
      final engineWithLog = SenseVoiceEngine(enableDebugLog: true);
      final engineWithoutLog = SenseVoiceEngine(enableDebugLog: false);

      // 引擎应该正常创建
      expect(engineWithLog, isNotNull);
      expect(engineWithoutLog, isNotNull);
    });
  });

  group('SenseVoiceEngine 与 ZipformerEngine 对比', () {
    test('两种引擎应该有不同的 engineType', () {
      final zipformer = ZipformerEngine();
      final sensevoice = SenseVoiceEngine();

      expect(zipformer.engineType, equals(ASREngineType.zipformer));
      expect(sensevoice.engineType, equals(ASREngineType.sensevoice));
      expect(zipformer.engineType, isNot(equals(sensevoice.engineType)));
    });

    test('两种引擎都应该实现 ASREngine 接口', () {
      final zipformer = ZipformerEngine();
      final sensevoice = SenseVoiceEngine();

      expect(zipformer, isA<ASREngine>());
      expect(sensevoice, isA<ASREngine>());
    });

    test('两种引擎初始状态应该一致', () {
      final zipformer = ZipformerEngine();
      final sensevoice = SenseVoiceEngine();

      expect(zipformer.isInitialized, equals(sensevoice.isInitialized));
      expect(zipformer.lastError, equals(sensevoice.lastError));
      expect(zipformer.getResult().isEmpty, equals(sensevoice.getResult().isEmpty));
    });
  });

  group('SenseVoiceConfig 验证', () {
    test('默认 VAD 配置应该使用 Silero VAD 标准参数', () {
      const config = SenseVoiceConfig(
        modelDir: '/test',
        vadModelPath: '/vad',
      );

      // Silero VAD 必须使用 512 窗口大小
      expect(config.vadWindowSize, equals(512));
      // 推荐的检测阈值
      expect(config.vadThreshold, equals(0.25));
      // 标准采样率
      expect(config.sampleRate, equals(16000));
    });

    test('SenseVoice 默认启用 ITN', () {
      const config = SenseVoiceConfig(
        modelDir: '/test',
        vadModelPath: '/vad',
      );

      expect(config.useItn, isTrue);
    });

    test('SenseVoice 默认语言应该是 auto', () {
      const config = SenseVoiceConfig(
        modelDir: '/test',
        vadModelPath: '/vad',
      );

      expect(config.language, equals('auto'));
    });

    test('VAD 最大语音时长应该为 10 秒', () {
      const config = SenseVoiceConfig(
        modelDir: '/test',
        vadModelPath: '/vad',
      );

      expect(config.maxSpeechDuration, equals(10.0));
    });
  });
}

