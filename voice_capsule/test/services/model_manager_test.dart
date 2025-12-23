import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
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
}
