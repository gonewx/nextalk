import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/services/model_manager.dart';

void main() {
  group('ModelManager Story 3-7 Tests', () {
    group('Static Properties Tests', () {
      test('downloadUrl returns non-empty URL', () {
        expect(ModelManager.downloadUrl, isNotEmpty);
        expect(ModelManager.downloadUrl, contains('github.com'));
        expect(ModelManager.downloadUrl, contains('sherpa-onnx'));
      });

      test('modelDirectory returns non-empty path', () {
        expect(ModelManager.modelDirectory, isNotEmpty);
        expect(ModelManager.modelDirectory, contains('nextalk'));
        expect(ModelManager.modelDirectory, contains('models'));
      });
    });

    group('Instance Methods Tests', () {
      late ModelManager manager;

      setUp(() {
        manager = ModelManager();
      });

      test('getExpectedStructure returns non-empty structure description', () {
        final structure = manager.getExpectedStructure();
        expect(structure, isNotEmpty);
        expect(structure, contains('encoder'));
        expect(structure, contains('decoder'));
        expect(structure, contains('joiner'));
        expect(structure, contains('tokens.txt'));
      });

      test('modelPath returns expected path format', () {
        final path = manager.modelPath;
        expect(path, isNotEmpty);
        expect(path, contains('nextalk/models'));
        expect(path, contains('sherpa-onnx'));
      });

      // 注意: deleteModel 和 openModelDirectory 测试需要文件系统访问
      // 这里只验证方法存在且可调用
      test('deleteModel is callable', () {
        expect(() => manager.deleteModel, returnsNormally);
      });

      test('openModelDirectory is callable', () {
        expect(() => manager.openModelDirectory, returnsNormally);
      });
    });

    group('ModelStatus Tests', () {
      test('ModelStatus enum contains all expected values', () {
        expect(ModelStatus.values.length, 6);
        expect(ModelStatus.values, contains(ModelStatus.notFound));
        expect(ModelStatus.values, contains(ModelStatus.incomplete));
        expect(ModelStatus.values, contains(ModelStatus.corrupted));
        expect(ModelStatus.values, contains(ModelStatus.ready));
        expect(ModelStatus.values, contains(ModelStatus.downloading));
        expect(ModelStatus.values, contains(ModelStatus.extracting));
      });
    });

    group('ModelError Tests', () {
      test('ModelError enum contains all expected values', () {
        expect(ModelError.values.length, 7);
        expect(ModelError.values, contains(ModelError.none));
        expect(ModelError.values, contains(ModelError.networkError));
        expect(ModelError.values, contains(ModelError.diskSpaceError));
        expect(ModelError.values, contains(ModelError.checksumMismatch));
        expect(ModelError.values, contains(ModelError.extractionFailed));
        expect(ModelError.values, contains(ModelError.permissionDenied));
        expect(ModelError.values, contains(ModelError.downloadCancelled));
      });
    });
  });

  // ============================================
  // Story 2-7 Task 4.6: 多引擎模型管理测试
  // ============================================

  group('ModelManager Story 2-7 Multi-Engine Tests', () {
    group('EngineType Enum Tests', () {
      test('EngineType should contain zipformer', () {
        expect(EngineType.values, contains(EngineType.zipformer));
      });

      test('EngineType should contain sensevoice', () {
        expect(EngineType.values, contains(EngineType.sensevoice));
      });

      test('EngineType should have exactly 2 values', () {
        expect(EngineType.values.length, equals(2));
      });
    });

    group('ModelConfig Tests', () {
      test('Zipformer config has correct properties', () {
        final config = ModelConfigs.zipformer;
        expect(config.displayName, equals('Zipformer (流式)'));
        expect(config.dirName, equals('zipformer'));
        expect(config.defaultUrl, contains('sherpa-onnx'));
        expect(config.sha256, isNotNull);
        expect(config.requiredFilePrefixes, contains('encoder'));
        expect(config.requiredFilePrefixes, contains('decoder'));
        expect(config.requiredFilePrefixes, contains('joiner'));
        expect(config.isSingleFile, isFalse);
      });

      test('SenseVoice config has correct properties', () {
        final config = ModelConfigs.sensevoice;
        expect(config.displayName, equals('SenseVoice (离线)'));
        expect(config.dirName, equals('sensevoice'));
        expect(config.defaultUrl, contains('sense-voice'));
        expect(config.requiredFilePrefixes, contains('model'));
        expect(config.isSingleFile, isFalse);
      });

      test('VAD config has correct properties', () {
        final config = ModelConfigs.sileroVad;
        expect(config.displayName, equals('Silero VAD'));
        expect(config.dirName, equals('vad'));
        expect(config.defaultUrl, contains('silero_vad.onnx'));
        expect(config.requiredFilePrefixes, contains('silero_vad'));
        expect(config.isSingleFile, isTrue);
      });

      test('forEngine returns correct config for Zipformer', () {
        final config = ModelConfigs.forEngine(EngineType.zipformer);
        expect(config.dirName, equals('zipformer'));
      });

      test('forEngine returns correct config for SenseVoice', () {
        final config = ModelConfigs.forEngine(EngineType.sensevoice);
        expect(config.dirName, equals('sensevoice'));
      });
    });

    group('Multi-Engine Path Tests', () {
      late ModelManager manager;

      setUp(() {
        manager = ModelManager();
      });

      test('getModelPathForEngine returns correct path for Zipformer', () {
        final path = manager.getModelPathForEngine(EngineType.zipformer);
        expect(path, isNotEmpty);
        expect(path, contains('nextalk/models'));
        expect(path, endsWith('/zipformer'));
      });

      test('getModelPathForEngine returns correct path for SenseVoice', () {
        final path = manager.getModelPathForEngine(EngineType.sensevoice);
        expect(path, isNotEmpty);
        expect(path, contains('nextalk/models'));
        expect(path, endsWith('/sensevoice'));
      });

      test('vadModelPath returns correct path', () {
        final path = manager.vadModelPath;
        expect(path, isNotEmpty);
        expect(path, contains('nextalk/models'));
        expect(path, endsWith('/vad'));
      });

      test('vadModelFilePath returns correct file path', () {
        final path = manager.vadModelFilePath;
        expect(path, isNotEmpty);
        expect(path, endsWith('/vad/silero_vad.onnx'));
      });
    });

    group('Multi-Engine Status Tests', () {
      late ModelManager manager;

      setUp(() {
        manager = ModelManager();
      });

      test('checkModelStatusForEngine returns valid status', () {
        // 测试两种引擎都应返回有效状态
        final zipformerStatus = manager.checkModelStatusForEngine(EngineType.zipformer);
        final sensevoiceStatus = manager.checkModelStatusForEngine(EngineType.sensevoice);
        
        // 状态应该是 ModelStatus 枚举值之一
        expect(ModelStatus.values, contains(zipformerStatus));
        expect(ModelStatus.values, contains(sensevoiceStatus));
      });

      test('checkVadModelStatus returns valid status', () {
        final status = manager.checkVadModelStatus();
        // 状态应该是 notFound 或 ready (VAD 不会是 incomplete，因为它是单文件)
        expect(status, anyOf(ModelStatus.notFound, ModelStatus.ready));
      });

      test('isModelReadyForEngine returns boolean', () {
        final zipformerReady = manager.isModelReadyForEngine(EngineType.zipformer);
        final sensevoiceReady = manager.isModelReadyForEngine(EngineType.sensevoice);
        expect(zipformerReady, isA<bool>());
        expect(sensevoiceReady, isA<bool>());
      });

      test('isVadModelReady returns boolean', () {
        final ready = manager.isVadModelReady;
        expect(ready, isA<bool>());
      });

      test('isSenseVoiceReady returns boolean', () {
        final ready = manager.isSenseVoiceReady;
        expect(ready, isA<bool>());
      });

      test('isSenseVoiceReady requires both model and VAD', () {
        // isSenseVoiceReady 应该是两者的 AND 关系
        final sensevoiceModelReady = manager.isModelReadyForEngine(EngineType.sensevoice);
        final vadReady = manager.isVadModelReady;
        final combinedReady = manager.isSenseVoiceReady;
        
        // 如果 SenseVoice 完全就绪，则两者都应就绪
        if (combinedReady) {
          expect(sensevoiceModelReady, isTrue);
          expect(vadReady, isTrue);
        }
      });
    });

    group('Multi-Engine URL Tests', () {
      late ModelManager manager;

      setUp(() {
        manager = ModelManager();
      });

      test('getDownloadUrlForEngine returns non-empty URL for Zipformer', () {
        final url = manager.getDownloadUrlForEngine(EngineType.zipformer);
        expect(url, isNotEmpty);
        expect(url, contains('github.com'));
        expect(url, contains('sherpa-onnx'));
      });

      test('getDownloadUrlForEngine returns non-empty URL for SenseVoice', () {
        final url = manager.getDownloadUrlForEngine(EngineType.sensevoice);
        expect(url, isNotEmpty);
        expect(url, contains('github.com'));
        expect(url, contains('sense-voice'));
      });

      test('vadDownloadUrl returns non-empty URL', () {
        final url = manager.vadDownloadUrl;
        expect(url, isNotEmpty);
        expect(url, contains('silero_vad.onnx'));
      });
    });

    group('Multi-Engine Structure Description Tests', () {
      late ModelManager manager;

      setUp(() {
        manager = ModelManager();
      });

      test('getExpectedStructureForEngine returns valid structure for Zipformer', () {
        final structure = manager.getExpectedStructureForEngine(EngineType.zipformer);
        expect(structure, isNotEmpty);
        expect(structure, contains('zipformer'));
        expect(structure, contains('encoder'));
        expect(structure, contains('decoder'));
        expect(structure, contains('joiner'));
        expect(structure, contains('tokens.txt'));
      });

      test('getExpectedStructureForEngine returns valid structure for SenseVoice', () {
        final structure = manager.getExpectedStructureForEngine(EngineType.sensevoice);
        expect(structure, isNotEmpty);
        expect(structure, contains('sensevoice'));
        expect(structure, contains('model.onnx'));
        expect(structure, contains('tokens.txt'));
      });

      test('vadExpectedStructure returns valid structure', () {
        final structure = manager.vadExpectedStructure;
        expect(structure, isNotEmpty);
        expect(structure, contains('vad'));
        expect(structure, contains('silero_vad.onnx'));
      });
    });

    group('Multi-Engine Delete Tests', () {
      late ModelManager manager;

      setUp(() {
        manager = ModelManager();
      });

      test('deleteModelForEngine is callable', () {
        expect(() => manager.deleteModelForEngine, returnsNormally);
      });

      test('deleteVadModel is callable', () {
        expect(() => manager.deleteVadModel, returnsNormally);
      });
    });

    group('Multi-Engine Open Directory Tests', () {
      late ModelManager manager;

      setUp(() {
        manager = ModelManager();
      });

      test('openModelDirectoryForEngine is callable', () {
        expect(() => manager.openModelDirectoryForEngine, returnsNormally);
      });
    });
  });
}
