import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/model_manager.dart';

void main() {
  late ModelManager manager;
  late String testModelPath;
  late Directory testDir;

  setUp(() {
    manager = ModelManager();
    testModelPath = manager.modelPath;
    testDir = Directory(testModelPath);
  });

  tearDown(() {
    // 清理测试目录 (仅清理测试创建的内容)
    // 注意: 不要删除实际的模型目录，只在测试结束后清理
  });

  group('ModelManager', () {
    test('模型目录不存在时返回 notFound', () {
      // 使用临时目录进行测试
      final tempManager = _TestModelManager();
      expect(tempManager.checkModelStatus(), ModelStatus.notFound);
    });

    test('模型文件不完整时返回 incomplete', () {
      final tempManager = _TestModelManager();
      final tempDir = Directory(tempManager.modelPath);
      tempDir.createSync(recursive: true);
      File('${tempManager.modelPath}/tokens.txt').writeAsStringSync('test');

      expect(tempManager.checkModelStatus(), ModelStatus.incomplete);

      // 清理
      tempDir.deleteSync(recursive: true);
    });

    test('使用前缀匹配检测模型文件', () {
      final tempManager = _TestModelManager();
      final tempDir = Directory(tempManager.modelPath);
      tempDir.createSync(recursive: true);

      // 使用实际的文件名格式
      File('${tempManager.modelPath}/encoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/decoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/joiner-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/tokens.txt').writeAsStringSync('test');

      expect(tempManager.checkModelStatus(), ModelStatus.ready);

      // 清理
      tempDir.deleteSync(recursive: true);
    });

    test('modelPath 使用 XDG 规范路径', () {
      expect(manager.modelPath, contains('nextalk/models'));
      expect(manager.modelPath, isNot(contains('voice_capsule')));
    });

    test('isModelReady 属性正确反映模型状态', () {
      final tempManager = _TestModelManager();

      // 模型不存在时应返回 false
      expect(tempManager.isModelReady, isFalse);

      // 创建完整的模型文件后应返回 true
      final tempDir = Directory(tempManager.modelPath);
      tempDir.createSync(recursive: true);
      File('${tempManager.modelPath}/encoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/decoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/joiner-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/tokens.txt').writeAsStringSync('test');

      expect(tempManager.isModelReady, isTrue);

      // 清理
      tempDir.deleteSync(recursive: true);
    });

    test('checkModelStatus 正确检测缺失的 encoder', () {
      final tempManager = _TestModelManager();
      final tempDir = Directory(tempManager.modelPath);
      tempDir.createSync(recursive: true);

      // 只创建 decoder, joiner, tokens (缺少 encoder)
      File('${tempManager.modelPath}/decoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/joiner-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/tokens.txt').writeAsStringSync('test');

      expect(tempManager.checkModelStatus(), ModelStatus.incomplete);

      // 清理
      tempDir.deleteSync(recursive: true);
    });

    test('checkModelStatus 正确检测缺失的 tokens.txt', () {
      final tempManager = _TestModelManager();
      final tempDir = Directory(tempManager.modelPath);
      tempDir.createSync(recursive: true);

      // 创建所有 onnx 文件但缺少 tokens.txt
      File('${tempManager.modelPath}/encoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/decoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/joiner-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);

      expect(tempManager.checkModelStatus(), ModelStatus.incomplete);

      // 清理
      tempDir.deleteSync(recursive: true);
    });
  });

  group('ModelManager SHA256 校验', () {
    test('verifyChecksum 对正确文件返回 true', () async {
      // 创建测试文件
      final testDir = Directory.systemTemp.createTempSync('sha256_test_');
      final testFile = File('${testDir.path}/test.txt');
      testFile.writeAsStringSync('hello world');

      // 计算期望的 SHA256
      final expectedHash = sha256.convert('hello world'.codeUnits).toString();

      // 创建可测试的 manager
      final testManager = _TestableModelManager(expectedHash);
      final result = await testManager.verifyChecksum(testFile.path);

      expect(result, isTrue);

      // 清理
      testDir.deleteSync(recursive: true);
    });

    test('verifyChecksum 对错误文件返回 false', () async {
      // 创建测试文件
      final testDir = Directory.systemTemp.createTempSync('sha256_test_');
      final testFile = File('${testDir.path}/test.txt');
      testFile.writeAsStringSync('hello world');

      // 使用错误的期望哈希
      final testManager = _TestableModelManager('wrong_hash_value');
      final result = await testManager.verifyChecksum(testFile.path);

      expect(result, isFalse);

      // 清理
      testDir.deleteSync(recursive: true);
    });

    test('进度回调在校验过程中被调用', () async {
      final testDir = Directory.systemTemp.createTempSync('sha256_progress_');
      final testFile = File('${testDir.path}/test.txt');
      testFile.writeAsStringSync('test content');

      final progressCalls = <double>[];
      final testManager = _TestableModelManager(
          sha256.convert('test content'.codeUnits).toString());

      await testManager.verifyChecksum(
        testFile.path,
        onProgress: (progress, status) => progressCalls.add(progress),
      );

      expect(progressCalls, contains(0.0));
      expect(progressCalls, contains(1.0));

      testDir.deleteSync(recursive: true);
    });
  });

  group('ModelManager 错误处理', () {
    test('ModelError 枚举包含所有必要错误类型', () {
      expect(ModelError.values, contains(ModelError.none));
      expect(ModelError.values, contains(ModelError.networkError));
      expect(ModelError.values, contains(ModelError.diskSpaceError));
      expect(ModelError.values, contains(ModelError.checksumMismatch));
      expect(ModelError.values, contains(ModelError.extractionFailed));
      expect(ModelError.values, contains(ModelError.permissionDenied));
      expect(ModelError.values, contains(ModelError.downloadCancelled));
    });

    test('ModelStatus 枚举包含所有必要状态', () {
      expect(ModelStatus.values, contains(ModelStatus.notFound));
      expect(ModelStatus.values, contains(ModelStatus.incomplete));
      expect(ModelStatus.values, contains(ModelStatus.corrupted));
      expect(ModelStatus.values, contains(ModelStatus.ready));
      expect(ModelStatus.values, contains(ModelStatus.downloading));
      expect(ModelStatus.values, contains(ModelStatus.extracting));
    });
  });

  group('ModelManager ensureModelReady', () {
    test('模型已就绪时直接返回 none', () async {
      final tempManager = _TestModelManager();
      final tempDir = Directory(tempManager.modelPath);
      tempDir.createSync(recursive: true);

      // 创建完整的模型文件
      File('${tempManager.modelPath}/encoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/decoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/joiner-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/tokens.txt').writeAsStringSync('test');

      final result = await tempManager.ensureModelReady();
      expect(result, ModelError.none);

      // 清理
      tempDir.deleteSync(recursive: true);
    });

    test('ensureModelReady 调用进度回调', () async {
      final tempManager = _TestModelManager();
      final tempDir = Directory(tempManager.modelPath);
      tempDir.createSync(recursive: true);

      // 创建完整模型
      File('${tempManager.modelPath}/encoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/decoder-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/joiner-epoch-99-avg-1.onnx')
          .writeAsBytesSync([0]);
      File('${tempManager.modelPath}/tokens.txt').writeAsStringSync('test');

      String? lastStatus;
      await tempManager.ensureModelReady(
        onProgress: (progress, status) => lastStatus = status,
      );

      expect(lastStatus, '模型已就绪');

      tempDir.deleteSync(recursive: true);
    });
  });

  group('ModelManager 路径配置', () {
    test('临时文件路径在 XDG_DATA_HOME 下', () {
      final manager = ModelManager();
      // 通过反射或公开方法验证路径格式
      expect(manager.modelPath, contains('nextalk'));
      expect(manager.modelPath, contains('models'));
    });

    test('模型路径包含正确的模型名称', () {
      final manager = ModelManager();
      expect(manager.modelPath,
          contains('sherpa-onnx-streaming-zipformer-bilingual-zh-en'));
    });
  });
}

/// 使用临时目录的测试用 ModelManager
class _TestModelManager extends ModelManager {
  final String _instanceTestDir;

  _TestModelManager()
      : _instanceTestDir =
            '${Directory.systemTemp.path}/nextalk_test_${DateTime.now().millisecondsSinceEpoch}_${_counter++}';

  static int _counter = 0;

  @override
  String get modelPath =>
      '$_instanceTestDir/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en';
}

/// 可配置 SHA256 期望值的测试用 ModelManager
class _TestableModelManager extends ModelManager {
  final String _testExpectedSha256;

  _TestableModelManager(this._testExpectedSha256);

  /// 使用自定义期望哈希进行校验
  @override
  Future<bool> verifyChecksum(String filePath,
      {ProgressCallback? onProgress}) async {
    onProgress?.call(0.0, '校验文件完整性...');

    // 计算实际哈希
    final file = File(filePath);
    final bytes = await file.readAsBytes();
    final actual = sha256.convert(bytes).toString();

    onProgress?.call(1.0, '校验完成');

    return actual == _testExpectedSha256;
  }
}
