import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/audio_inference_pipeline.dart';
import 'package:voice_capsule/services/model_manager.dart';

/// buildEngineConfig 防回归测试
///
/// 预初始化 (main._preInitializeEngine) 与运行期 (Pipeline.start())
/// 共用此构造。引擎对已初始化实例直接返回，配置不一致会被静默忽略，
/// 因此必须保证:
/// - zipformer 的 modelDir 来自 getModelPathForEngine (非遗留 modelPath)
/// - 各参数值与管线运行期完全一致
void main() {
  late ModelManager modelManager;

  setUp(() {
    modelManager = ModelManager();
  });

  group('buildEngineConfig - Zipformer', () {
    test('modelDir 来自 getModelPathForEngine 而非遗留 modelPath', () {
      final config = AudioInferencePipeline.buildEngineConfig(
        engineType: ASREngineType.zipformer,
        modelManager: modelManager,
      ) as ZipformerConfig;

      expect(config.modelDir,
          modelManager.getModelPathForEngine(EngineType.zipformer));
      // 遗留路径 (根因 2: 目录已不存在，导致预热 modelNotFound)
      expect(config.modelDir, isNot(modelManager.modelPath));
    });

    test('参数值与管线运行期一致', () {
      final config = AudioInferencePipeline.buildEngineConfig(
        engineType: ASREngineType.zipformer,
        modelManager: modelManager,
      ) as ZipformerConfig;

      expect(config.numThreads, 2);
      expect(config.sampleRate, 16000);
      expect(config.enableEndpoint, true);
      expect(config.rule1MinTrailingSilence, 2.4);
      expect(config.rule2MinTrailingSilence,
          AudioInferencePipeline.kDefaultRule2Silence);
      expect(config.rule3MinUtteranceLength, 20.0);
    });

    test('silenceThresholdSec 为 null 时使用默认值 1.2', () {
      final config = AudioInferencePipeline.buildEngineConfig(
        engineType: ASREngineType.zipformer,
        modelManager: modelManager,
        silenceThresholdSec: null,
      ) as ZipformerConfig;

      expect(config.rule2MinTrailingSilence, 1.2);
    });

    test('silenceThresholdSec 显式指定时透传', () {
      final config = AudioInferencePipeline.buildEngineConfig(
        engineType: ASREngineType.zipformer,
        modelManager: modelManager,
        silenceThresholdSec: 0.8,
      ) as ZipformerConfig;

      expect(config.rule2MinTrailingSilence, 0.8);
    });
  });

  group('buildEngineConfig - SenseVoice', () {
    test('modelDir 与 vadModelPath 来自 ModelManager 对应路径', () {
      final config = AudioInferencePipeline.buildEngineConfig(
        engineType: ASREngineType.sensevoice,
        modelManager: modelManager,
      ) as SenseVoiceConfig;

      expect(config.modelDir,
          modelManager.getModelPathForEngine(EngineType.sensevoice));
      expect(config.vadModelPath, modelManager.vadModelFilePath);
    });
  });
}
