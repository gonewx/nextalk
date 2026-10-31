import 'dart:io';
import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/qwen3_asr_constants.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/services/asr/asr_engine.dart';
import 'package:voice_capsule/services/asr/asr_engine_factory.dart';
import 'package:voice_capsule/services/asr/engine_initializer.dart';
import 'package:voice_capsule/services/asr/qwen3_asr_engine.dart';
import 'package:voice_capsule/services/model_manager.dart';

class _LocalModels extends ModelManager {
  final String root;
  _LocalModels(this.root);
  @override
  String getModelPathForEngine(EngineType type) => '$root/${type.name}';
  @override
  String get vadModelFilePath => '$root/silero_vad.onnx';
}

class _CorruptedDownloadModels extends _LocalModels {
  final String archivePath;
  _CorruptedDownloadModels(super.root, this.archivePath);
  @override
  Future<String> downloadModelForEngine(EngineType type, {
    ProgressCallback? onProgress, int maxRetries = 3,
  }) async => archivePath;
}

void main() {
  late Directory temp;
  late _LocalModels models;
  late Qwen3AsrEngine engine;
  setUp(() {
    temp = Directory.systemTemp.createTempSync('nextalk_qwen_test_');
    models = _LocalModels(temp.path);
    engine = Qwen3AsrEngine();
  });
  tearDown(() {
    engine.dispose();
    temp.deleteSync(recursive: true);
  });
  void createModelFiles() {
    for (final name in Qwen3AsrConstants.requiredFiles) {
      final file =
          File('${models.getModelPathForEngine(EngineType.qwen3Asr)}/$name');
      file.parent.createSync(recursive: true);
      file.writeAsStringSync('模型占位内容，仅用于文件检查');
    }
  }

  Qwen3AsrConfig config({int threads = 2, int maxTokens = 128}) =>
      Qwen3AsrConfig(
        modelDir: models.getModelPathForEngine(EngineType.qwen3Asr),
        vadModelPath: models.vadModelFilePath,
        numThreads: threads,
        maxNewTokens: maxTokens,
      );
  test('工厂创建 Qwen3-ASR，并透传线程、生成上限和热词', () {
    final created = ASREngineFactory.create(ASREngineType.qwen3Asr);
    expect(created, isA<Qwen3AsrEngine>());
    expect(created.engineType, ASREngineType.qwen3Asr);
    final c = ASREngineFactory.createConfig(
      ASREngineType.qwen3Asr,
      modelDir: '/模型',
      vadModelPath: '/vad.onnx',
      numThreads: 4,
      maxNewTokens: 256,
      hotwords: 'Nextalk,语音输入',
    ) as Qwen3AsrConfig;
    expect(c.numThreads, 4);
    expect(c.maxNewTokens, 256);
    expect(c.hotwords, 'Nextalk,语音输入');
    expect(c.vadModelPath, '/vad.onnx');
    expect(
        () => ASREngineFactory.createConfig(ASREngineType.qwen3Asr,
            modelDir: '/模型'),
        throwsArgumentError);
    created.dispose();
  });
  test('拒绝错误配置类型和越界数值，不进入原生调用', () async {
    expect(await engine.initialize(const ZipformerConfig(modelDir: '/模型')),
        ASRError.invalidConfig);
    for (final c in [
      config(threads: 0),
      config(maxTokens: 0),
      config(maxTokens: 513)
    ]) {
      expect(await engine.initialize(c), ASRError.invalidConfig);
      expect(engine.isInitialized, isFalse);
    }
  });
  test('分别报告模型目录、文件和 VAD 缺失', () async {
    expect(await engine.initialize(config()), ASRError.modelNotFound);
    Directory(config().modelDir).createSync();
    expect(await engine.initialize(config()), ASRError.modelFileMissing);
    createModelFiles();
    expect(await engine.initialize(config()), ASRError.vadInitFailed);
    File(models.vadModelFilePath).writeAsBytesSync([]);
    expect(await engine.initialize(config()), ASRError.vadInitFailed);
  });
  test('完整性检查覆盖三个模型和 tokenizer 的每个文件，拒绝空文件', () {
    createModelFiles();
    expect(models.checkModelStatusForEngine(EngineType.qwen3Asr),
        ModelStatus.ready);
    for (final name in Qwen3AsrConstants.requiredFiles) {
      final file = File('${config().modelDir}/$name');
      final bytes = file.readAsBytesSync();
      file.deleteSync();
      expect(models.checkModelStatusForEngine(EngineType.qwen3Asr),
          ModelStatus.incomplete,
          reason: name);
      file.writeAsBytesSync([]);
      expect(models.checkModelStatusForEngine(EngineType.qwen3Asr),
          ModelStatus.incomplete,
          reason: '$name 为空');
      file.writeAsBytesSync(bytes);
    }
    expect(File('${config().modelDir}/tokens.txt').existsSync(), isFalse);
  });
  test('只有识别模型时不就绪，补齐 VAD 后可被全局可用性检查找到', () {
    createModelFiles();
    expect(models.isEngineReady(EngineType.qwen3Asr), isFalse);
    expect(models.hasAnyEngineReady, isFalse);
    File(models.vadModelFilePath).writeAsStringSync('VAD');
    expect(models.isEngineReady(EngineType.qwen3Asr), isTrue);
    expect(models.hasAnyEngineReady, isTrue);
    expect(EngineInitializer(models).getFirstAvailableEngine(),
        EngineType.qwen3Asr);
  });
  test('回退遍历所有引擎，能够选择仅安装的 Qwen3-ASR', () async {
    createModelFiles();
    File(models.vadModelFilePath).writeAsStringSync('VAD');
    final result = await EngineInitializer(models)
        .initialize(preferredType: EngineType.sensevoice);
    expect(result.actualEngineType, EngineType.qwen3Asr);
    expect(result.fallbackOccurred, isTrue);
    expect(result.engine, isA<Qwen3AsrEngine>());
    result.engine.dispose();
  });
  test('所有模型缺失时异常记录全部三种尝试', () async {
    await expectLater(
        EngineInitializer(models)
            .initialize(preferredType: EngineType.qwen3Asr),
        throwsA(isA<EngineNotAvailableException>().having((e) => e.triedEngines,
            '尝试的引擎', ['qwen3Asr', 'sensevoice', 'zipformer'])));
  });
  test('下载校验不匹配时删除坏压缩包并拒绝解压', () async {
    final archive = File('${temp.path}/bad.tar.bz2')..writeAsStringSync('损坏内容');
    final manager = _CorruptedDownloadModels(temp.path, archive.path);
    await IOOverrides.runZoned(() async {
      expect(await manager.ensureModelReadyForEngine(EngineType.qwen3Asr),
          ModelError.checksumMismatch);
    }, createFile: (path) => Zone.root.run(() => File(
        path.endsWith('/temp_qwen3_asr.tar.bz2') ? archive.path : path)));
    expect(archive.existsSync(), isFalse);
    expect(models.isModelReadyForEngine(EngineType.qwen3Asr), isFalse);
  });
  test('未初始化的收尾和重复销毁安全', () {
    expect(engine.finalizeUtterance().isEmpty, isTrue);
    expect(engine.ensureStreamReady(), isFalse);
    expect(engine.isReady(), isFalse);
    engine.reset();
    engine.dispose();
    engine.dispose();
    expect(engine.getResult().isEmpty, isTrue);
    expect(engine.isEndpoint(), isFalse);
  });
  test('解压剥离顶层目录并验证必需文件，失败时保留现有模型', () async {
    final source =
        Directory('${temp.path}/source/${ModelConfigs.qwen3Asr.archiveTopDir}');
    for (final name in Qwen3AsrConstants.requiredFiles) {
      final file = File('${source.path}/$name');
      file.parent.createSync(recursive: true);
      file.writeAsStringSync('有效占位文件');
    }
    final archive = '${temp.path}/model.tar.bz2';
    final pack = await Process.run('tar', [
      '-cjf',
      archive,
      '-C',
      '${temp.path}/source',
      ModelConfigs.qwen3Asr.archiveTopDir
    ]);
    expect(pack.exitCode, 0);
    await models.extractModelForEngine(EngineType.qwen3Asr, archive);
    expect(models.checkModelStatusForEngine(EngineType.qwen3Asr),
        ModelStatus.ready);
    File('${source.path}/tokenizer/merges.txt').deleteSync();
    await Process.run('tar', [
      '-cjf',
      archive,
      '-C',
      '${temp.path}/source',
      ModelConfigs.qwen3Asr.archiveTopDir
    ]);
    await expectLater(
        models.extractModelForEngine(EngineType.qwen3Asr, archive),
        throwsFormatException);
    expect(models.checkModelStatusForEngine(EngineType.qwen3Asr),
        ModelStatus.ready);
    expect(temp.listSync().where((f) => f.path.contains('.extract-')), isEmpty);
  });
}
