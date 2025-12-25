import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';

import '../constants/settings_constants.dart';
import 'settings_service.dart';

/// 模型状态枚举
enum ModelStatus {
  notFound, // 模型不存在
  incomplete, // 模型不完整 (部分文件缺失)
  corrupted, // 模型损坏 (校验失败)
  ready, // 模型就绪
  downloading, // 正在下载
  extracting, // 正在解压
}

/// 模型管理错误类型
enum ModelError {
  none,
  networkError,
  diskSpaceError,
  checksumMismatch,
  extractionFailed,
  permissionDenied,
  downloadCancelled,
}

/// 下载进度回调 (progress: 0-1, status: 状态文本, downloaded: 已下载字节, total: 总字节)
typedef ProgressCallback = void Function(double progress, String status,
    {int downloaded, int total});

// ===== Story 2-7: 多引擎模型配置 =====

/// 模型配置 (用于多引擎支持)
class ModelConfig {
  /// 模型显示名称
  final String displayName;

  /// 模型目录名 (在 models/ 下的子目录)
  final String dirName;

  /// 压缩包内顶层目录名 (解压时剥离)
  final String archiveTopDir;

  /// 默认下载 URL
  final String defaultUrl;

  /// SHA256 校验值 (null 表示跳过校验)
  final String? sha256;

  /// 必需的模型文件前缀列表 (用于完整性检查)
  final List<String> requiredFilePrefixes;

  /// 是否为单文件模型 (如 silero_vad.onnx)
  final bool isSingleFile;

  const ModelConfig({
    required this.displayName,
    required this.dirName,
    required this.archiveTopDir,
    required this.defaultUrl,
    this.sha256,
    this.requiredFilePrefixes = const [],
    this.isSingleFile = false,
  });
}

/// 预定义模型配置
class ModelConfigs {
  ModelConfigs._();

  /// Zipformer 流式模型 (中英双语)
  static const zipformer = ModelConfig(
    displayName: 'Zipformer (流式)',
    dirName: 'zipformer',
    archiveTopDir: 'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20',
    defaultUrl:
        'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'
        'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2',
    sha256: '27ffbd9ee24ad186d99acc2f6354d7992b27bcab490812510665fa8f9389c5f8',
    requiredFilePrefixes: ['encoder', 'decoder', 'joiner'],
  );

  /// SenseVoice 离线模型 (多语言)
  /// 注意: sherpa-onnx 官方未提供 SHA256 校验值，跳过校验
  static const sensevoice = ModelConfig(
    displayName: 'SenseVoice (离线)',
    dirName: 'sensevoice',
    archiveTopDir: 'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17',
    defaultUrl:
        'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'
        'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2',
    sha256: null, // 官方未提供校验值
    requiredFilePrefixes: ['model'],
  );

  /// Silero VAD 模型
  /// 注意: sherpa-onnx 官方未提供 SHA256 校验值，跳过校验
  static const sileroVad = ModelConfig(
    displayName: 'Silero VAD',
    dirName: 'vad',
    archiveTopDir: '', // 单文件，无顶层目录
    defaultUrl:
        'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'
        'silero_vad.onnx',
    sha256: null, // 官方未提供校验值
    requiredFilePrefixes: ['silero_vad'],
    isSingleFile: true,
  );

  /// 根据引擎类型获取配置
  static ModelConfig forEngine(EngineType type) {
    switch (type) {
      case EngineType.zipformer:
        return zipformer;
      case EngineType.sensevoice:
        return sensevoice;
    }
  }
}

class ModelManager {
  // === 向后兼容: 原有 Zipformer 配置 ===
  static const String _modelName =
      'sherpa-onnx-streaming-zipformer-bilingual-zh-en';
  static const String _archiveName =
      'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20';
  static const String _defaultDownloadUrl =
        'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'
      '$_archiveName.tar.bz2';
  static const String _expectedSha256 =
      '27ffbd9ee24ad186d99acc2f6354d7992b27bcab490812510665fa8f9389c5f8';

  /// Story 3-7: 下载取消令牌
  CancelToken? _cancelToken;

  // === Story 3-7: 新增公开静态属性 ===

  /// 获取模型下载 URL (优先使用自定义 URL)
  static String get downloadUrl {
    // 优先使用 SettingsService 中的自定义 URL
    if (SettingsService.instance.isInitialized) {
      final customUrl = SettingsService.instance.customModelUrl;
      if (customUrl != null && customUrl.isNotEmpty) {
        return customUrl;
      }
    }
    return _defaultDownloadUrl;
  }

  /// 获取默认下载 URL (用于显示默认值)
  static String get defaultDownloadUrl => _defaultDownloadUrl;

  /// 获取模型根目录路径 (用于手动安装引导显示)
  static String get modelDirectory => _modelBaseDir;

  /// XDG 数据目录 (遵循 XDG Base Directory 规范)
  static String get _xdgDataHome {
    final xdgData = Platform.environment['XDG_DATA_HOME'];
    if (xdgData != null && xdgData.isNotEmpty) return xdgData;
    final home = Platform.environment['HOME']!;
    return '$home/.local/share';
  }

  /// 模型根目录
  static String get _modelBaseDir => '$_xdgDataHome/nextalk/models';

  /// 当前模型目录路径 (同步属性)
  String get modelPath => '$_modelBaseDir/$_modelName';

  /// 临时下载文件路径
  String get _tempFilePath => '$_xdgDataHome/nextalk/temp_model.tar.bz2';

  /// 公开临时文件路径（用于检查下载状态）
  String get tempFilePath => _tempFilePath;

  /// 检查临时文件状态（异步，需要请求服务器获取预期大小）
  /// 返回 (是否存在, 已下载字节数, 预期总字节数)
  Future<(bool exists, int downloaded, int expected)>
      checkTempFileStatus() async {
    final tempFile = File(_tempFilePath);
    if (!tempFile.existsSync()) {
      return (false, 0, 0);
    }
    final downloaded = tempFile.lengthSync();

    // 通过 HEAD 请求获取服务器文件大小
    int expected = 0;
    try {
      final client = HttpClient();
      client.connectionTimeout = const Duration(seconds: 10);
      final uri = Uri.parse(downloadUrl);
      final request = await client.headUrl(uri);
      final response = await request.close();
      expected = response.contentLength;
      await response.drain<void>();
      client.close(force: true);
    } catch (e) {
      print('[ModelManager] 获取服务器文件大小失败: $e');
    }

    return (true, downloaded, expected);
  }

  /// 检查是否有完整的临时文件等待解压（异步）
  Future<bool> hasPendingExtraction() async {
    final (exists, downloaded, expected) = await checkTempFileStatus();
    return exists && expected > 0 && downloaded >= expected;
  }

  /// 在目录中查找指定前缀的模型文件
  bool _hasModelFile(String prefix) {
    final dir = Directory(modelPath);
    if (!dir.existsSync()) return false;
    try {
      return dir.listSync().any((f) {
        final name = f.path.split('/').last;
        return name.startsWith(prefix) && name.endsWith('.onnx');
      });
    } catch (_) {
      return false;
    }
  }

  /// 检查模型状态
  ModelStatus checkModelStatus() {
    final dir = Directory(modelPath);
    if (!dir.existsSync()) {
      return ModelStatus.notFound;
    }

    // 检查必要文件 (使用前缀匹配，与 SherpaService._findModelFile 一致)
    if (!_hasModelFile('encoder')) return ModelStatus.incomplete;
    if (!_hasModelFile('decoder')) return ModelStatus.incomplete;
    if (!_hasModelFile('joiner')) return ModelStatus.incomplete;
    if (!File('$modelPath/tokens.txt').existsSync()) {
      return ModelStatus.incomplete;
    }

    return ModelStatus.ready;
  }

  /// 快捷属性: 模型是否就绪
  bool get isModelReady => checkModelStatus() == ModelStatus.ready;

  // === Story 3-7: 新增实例方法 ===

  /// 使用 xdg-open 打开模型目录 (AC6: 打开目录按钮)
  /// 如果目录不存在则先创建
  Future<void> openModelDirectory() async {
    final dir = Directory(modelDirectory);
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }
    await Process.run('xdg-open', [modelDirectory]);
  }

  /// 获取期望的目录结构描述 (用于手动安装引导显示)
  String getExpectedStructure() => '''
models/$_modelName/
├── encoder-epoch-*.onnx
├── decoder-epoch-*.onnx
├── joiner-epoch-*.onnx
└── tokens.txt
''';

  /// 删除现有模型目录 (用于"重新下载"操作)
  Future<void> deleteModel() async {
    final dir = Directory(modelPath);
    if (dir.existsSync()) {
      await dir.delete(recursive: true);
    }
  }

  /// Story 3-7: 取消正在进行的下载 (AC4: 取消按钮)
  void cancelDownload() {
    _cancelToken?.cancel('用户取消下载');
    _cancelToken = null;
  }

  /// 下载模型 (使用 HttpClient，支持代理、重试、进度回调、断点续传)
  Future<String> downloadModel({
    ProgressCallback? onProgress,
    int maxRetries = 3,
  }) async {
    // 确保目录存在
    final baseDir = Directory('$_xdgDataHome/nextalk');
    if (!baseDir.existsSync()) {
      baseDir.createSync(recursive: true);
    }

    final tempFile = File(_tempFilePath);
    Object lastException = Exception('下载失败');

    // Story 3-7: 创建新的取消令牌
    _cancelToken = CancelToken();
    bool isCancelled = false;
    _cancelToken!.whenCancel.then((_) => isCancelled = true);

    for (var attempt = 1; attempt <= maxRetries; attempt++) {
      HttpClient? client;
      try {
        // 创建 HttpClient
        client = HttpClient();
        client.connectionTimeout = const Duration(seconds: 30);

        // 检查并配置代理环境变量
        final httpProxy = Platform.environment['HTTP_PROXY'] ??
            Platform.environment['http_proxy'] ??
            Platform.environment['HTTPS_PROXY'] ??
            Platform.environment['https_proxy'];
        if (httpProxy != null && httpProxy.isNotEmpty) {
          print('[ModelManager] 检测到代理: $httpProxy');
          client.findProxy = (uri) => 'PROXY $httpProxy';
          client.badCertificateCallback = (cert, host, port) => true;
        }

        // 检查已下载的大小
        int downloadedBytes = 0;
        if (tempFile.existsSync()) {
          downloadedBytes = tempFile.lengthSync();
          print(
              '[ModelManager] 发现临时文件: ${(downloadedBytes / 1024 / 1024).toStringAsFixed(1)}MB');
        } else {
          print('[ModelManager] 临时文件不存在: ${tempFile.path}');
        }

        // 获取文件总大小 (使用独立的 HttpClient)
        final uri = Uri.parse(downloadUrl);
        int totalBytes = 0;
        try {
          final headClient = HttpClient();
          headClient.connectionTimeout = const Duration(seconds: 10);
          final headRequest = await headClient.headUrl(uri);
          final headResponse = await headRequest.close();
          totalBytes = headResponse.contentLength;
          // 完全消费响应体并关闭
          await headResponse.drain<void>();
          headClient.close(force: true);
          print(
              '[ModelManager] 文件总大小: ${(totalBytes / 1024 / 1024).toStringAsFixed(1)}MB');
        } catch (e) {
          print('[ModelManager] HEAD 请求失败: $e');
        }

        // 如果已经下载完成
        if (totalBytes > 0 && downloadedBytes >= totalBytes) {
          print('[ModelManager] 文件已完整下载');
          onProgress?.call(1.0, '下载完成');
          client.close();
          return _tempFilePath;
        }

        // 发起 GET 请求
        onProgress?.call(0.0, '下载中 (尝试 $attempt/$maxRetries)...',
            downloaded: downloadedBytes, total: totalBytes);
        print('[ModelManager] 开始下载: $downloadUrl');

        final request = await client.getUrl(uri);
        print('[ModelManager] GET 请求已创建');

        // 断点续传
        if (downloadedBytes > 0) {
          request.headers.set('Range', 'bytes=$downloadedBytes-');
          print(
              '[ModelManager] 断点续传: 从 ${(downloadedBytes / 1024 / 1024).toStringAsFixed(1)}MB 处继续');
        }

        print('[ModelManager] 等待服务器响应...');
        final response = await request.close();
        print('[ModelManager] 服务器已响应');
        final statusCode = response.statusCode;
        final isResuming = statusCode == 206;
        print(
            '[ModelManager] 服务器响应: $statusCode (${isResuming ? "断点续传" : "完整下载"})');

        if (downloadedBytes > 0 && !isResuming) {
          print('[ModelManager] 服务器不支持断点续传，重新下载');
          if (tempFile.existsSync()) {
            tempFile.deleteSync();
          }
          downloadedBytes = 0;
        }

        // 计算总大小
        final contentLength = response.contentLength;
        final expectedTotal = isResuming
            ? downloadedBytes + contentLength
            : (totalBytes > 0 ? totalBytes : contentLength);

        // 打开文件
        print('[ModelManager] 打开文件: ${isResuming ? "追加模式" : "写入模式"}');
        final raf = tempFile.openSync(
            mode: isResuming ? FileMode.append : FileMode.write);
        int received = isResuming ? downloadedBytes : 0;

        try {
          await for (final chunk in response) {
            if (isCancelled) {
              throw Exception('用户取消下载');
            }
            raf.writeFromSync(chunk);
            received += chunk.length;

            if (expectedTotal > 0) {
              final progress = received / expectedTotal;
              onProgress?.call(
                progress,
                '下载中: ${(progress * 100).toStringAsFixed(1)}%',
                downloaded: received,
                total: expectedTotal,
              );
            }
          }
        } finally {
          raf.closeSync();
          print(
              '[ModelManager] 文件已关闭，已写入: ${(received / 1024 / 1024).toStringAsFixed(1)}MB');
        }

        print(
            '[ModelManager] 下载完成，文件大小: ${(received / 1024 / 1024).toStringAsFixed(1)}MB');
        onProgress?.call(1.0, '下载完成',
            downloaded: received, total: expectedTotal);
        client.close();
        return _tempFilePath;
      } catch (e) {
        client?.close();
        lastException = e is Exception ? e : Exception(e.toString());
        print('[ModelManager] 下载失败 (${e.runtimeType}): $e');

        if (isCancelled) {
          print('[ModelManager] 下载被取消，保留临时文件');
          throw DioException(
            requestOptions: RequestOptions(path: downloadUrl),
            type: DioExceptionType.cancel,
          );
        }

        if (tempFile.existsSync()) {
          print(
              '[ModelManager] 临时文件保留: ${(tempFile.lengthSync() / 1024 / 1024).toStringAsFixed(1)}MB');
        }
        if (attempt < maxRetries) {
          onProgress?.call(0.0, '下载失败，3秒后重试...', downloaded: 0, total: 0);
          await Future.delayed(const Duration(seconds: 3));
        }
      }
    }

    throw lastException;
  }

  /// 流式计算文件 SHA256 (内存友好)
  Future<String> _computeSha256(String filePath) async {
    final file = File(filePath);
    var output = sha256.convert([]);

    // 使用流式读取，分块计算哈希
    final sink = sha256.startChunkedConversion(
      ChunkedConversionSink.withCallback((chunks) {
        output = chunks.single;
      }),
    );

    await for (final chunk in file.openRead()) {
      sink.add(chunk);
    }
    sink.close();

    return output.toString();
  }

  /// 校验文件 SHA256
  Future<bool> verifyChecksum(String filePath,
      {ProgressCallback? onProgress}) async {
    onProgress?.call(0.0, '校验文件完整性...', downloaded: 0, total: 0);
    final actual = await _computeSha256(filePath);
    onProgress?.call(1.0, '校验完成', downloaded: 0, total: 0);

    if (actual != _expectedSha256) {
      print('SHA256 不匹配: 期望 $_expectedSha256, 实际 $actual');
      return false;
    }
    return true;
  }

  /// 解压模型文件 (使用 Isolate 避免阻塞)
  Future<void> extractModel(String archivePath,
      {ProgressCallback? onProgress}) async {
    onProgress?.call(0.0, '解压中 (后台处理)...', downloaded: 0, total: 0);

    // 提取值为局部变量，避免捕获 this（包含不可发送的 CancelToken）
    final targetPath = modelPath;
    final archiveTopDir = _archiveName;

    await Isolate.run(() => _extractInIsolate(
          archivePath,
          targetPath,
          archiveTopDir,
        ));

    onProgress?.call(1.0, '解压完成', downloaded: 0, total: 0);
  }

  /// 在 Isolate 中执行解压 (耗时操作)
  static Future<void> _extractInIsolate(
    String archivePath,
    String modelDir,
    String archiveTopDir,
  ) async {
    final modelDirObj = Directory(modelDir);

    // 清理并创建目标目录
    if (modelDirObj.existsSync()) {
      modelDirObj.deleteSync(recursive: true);
    }
    modelDirObj.createSync(recursive: true);

    // 读取并解压
    final bytes = await File(archivePath).readAsBytes();
    final tarBytes = BZip2Decoder().decodeBytes(bytes);
    final archive = TarDecoder().decodeBytes(tarBytes);

    // 解压时剥离顶层目录前缀
    final prefix = '$archiveTopDir/';

    for (final file in archive) {
      if (!file.isFile) continue;

      var filename = file.name;
      // 剥离顶层目录 (如 sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/)
      if (filename.startsWith(prefix)) {
        filename = filename.substring(prefix.length);
      }
      if (filename.isEmpty) continue;

      final outputFile = File('$modelDir/$filename');
      outputFile.parent.createSync(recursive: true);
      outputFile.writeAsBytesSync(file.content as List<int>);
    }
  }

  /// 确保模型就绪 (检查 → 下载 → 校验 → 解压)
  Future<ModelError> ensureModelReady({
    ProgressCallback? onProgress,
  }) async {
    // 1. 检查现有模型
    final status = checkModelStatus();
    if (status == ModelStatus.ready) {
      onProgress?.call(1.0, '模型已就绪', downloaded: 0, total: 0);
      return ModelError.none;
    }

    final tempFile = File(_tempFilePath);
    bool downloadCompleted = false; // 标记下载是否完成

    try {
      // 2. 下载 (0% - 60%)
      onProgress?.call(0.0, '开始下载...', downloaded: 0, total: 0);
      await downloadModel(
        onProgress: (p, s, {int downloaded = 0, int total = 0}) =>
            onProgress?.call(p * 0.6, s, downloaded: downloaded, total: total),
        maxRetries: 3,
      );
      downloadCompleted = true; // 下载完成

      // 3. 校验 (60% - 70%)
      print('[ModelManager] 开始校验...');
      onProgress?.call(0.6, '校验中...', downloaded: 0, total: 0);
      final valid = await verifyChecksum(
        _tempFilePath,
        onProgress: (p, s, {int downloaded = 0, int total = 0}) =>
            onProgress?.call(0.6 + p * 0.1, s, downloaded: 0, total: 0),
      );
      if (!valid) {
        print('[ModelManager] 校验失败，删除临时文件');
        tempFile.deleteSync();
        return ModelError.checksumMismatch;
      }
      print('[ModelManager] 校验通过');

      // 4. 解压 (70% - 100%)
      print('[ModelManager] 开始解压...');
      onProgress?.call(0.7, '解压中...', downloaded: 0, total: 0);
      await extractModel(
        _tempFilePath,
        onProgress: (p, s, {int downloaded = 0, int total = 0}) =>
            onProgress?.call(0.7 + p * 0.3, s, downloaded: 0, total: 0),
      );

      // 5. 清理临时文件
      if (tempFile.existsSync()) {
        tempFile.deleteSync();
      }

      onProgress?.call(1.0, '模型准备完成', downloaded: 0, total: 0);
      return ModelError.none;
    } on DioException catch (e) {
      // 网络错误和取消：保留临时文件以便断点续传
      print('[ModelManager] DioException: ${e.type}, 保留临时文件');
      if (e.type == DioExceptionType.cancel) {
        return ModelError.downloadCancelled;
      }
      return ModelError.networkError;
    } on FileSystemException catch (e) {
      // 文件系统错误：只在下载完成后删除临时文件
      if (downloadCompleted) {
        _cleanupTempFile(tempFile);
      }
      if (e.message.contains('No space')) {
        return ModelError.diskSpaceError;
      }
      return ModelError.permissionDenied;
    } catch (e) {
      // 其他错误：只在下载完成后（校验/解压阶段）删除临时文件
      print('[ModelManager] 捕获异常 (${e.runtimeType}): $e');
      print('[ModelManager] 下载已完成: $downloadCompleted');
      if (downloadCompleted) {
        // 校验或解压阶段错误，删除可能损坏的文件
        _cleanupTempFile(tempFile);
        return ModelError.extractionFailed;
      } else {
        // 下载阶段错误，保留临时文件以便断点续传
        return ModelError.networkError;
      }
    }
  }

  void _cleanupTempFile(File tempFile) {
    try {
      if (tempFile.existsSync()) tempFile.deleteSync();
    } catch (_) {}
  }

  // ===== Story 2-7: 多引擎模型管理 =====

  /// 获取指定引擎的模型目录路径
  String getModelPathForEngine(EngineType engineType) {
    final config = ModelConfigs.forEngine(engineType);
    return '$_modelBaseDir/${config.dirName}';
  }

  /// 获取 VAD 模型目录路径
  String get vadModelPath => '$_modelBaseDir/${ModelConfigs.sileroVad.dirName}';

  /// 获取 VAD 模型文件路径
  String get vadModelFilePath => '$vadModelPath/silero_vad.onnx';

  /// 检查指定引擎的模型状态
  ModelStatus checkModelStatusForEngine(EngineType engineType) {
    final config = ModelConfigs.forEngine(engineType);
    final modelDir = Directory(getModelPathForEngine(engineType));

    if (!modelDir.existsSync()) {
      return ModelStatus.notFound;
    }

    // 检查必需文件
    for (final prefix in config.requiredFilePrefixes) {
      if (!_hasModelFileInDir(modelDir.path, prefix)) {
        return ModelStatus.incomplete;
      }
    }

    // 检查 tokens.txt (除了单文件模型)
    if (!config.isSingleFile && !File('${modelDir.path}/tokens.txt').existsSync()) {
      return ModelStatus.incomplete;
    }

    return ModelStatus.ready;
  }

  /// 检查 VAD 模型状态
  ModelStatus checkVadModelStatus() {
    final vadFile = File(vadModelFilePath);
    if (!vadFile.existsSync()) {
      return ModelStatus.notFound;
    }
    return ModelStatus.ready;
  }

  /// 检查指定引擎的模型是否就绪
  bool isModelReadyForEngine(EngineType engineType) {
    return checkModelStatusForEngine(engineType) == ModelStatus.ready;
  }

  /// 检查 VAD 模型是否就绪
  bool get isVadModelReady => checkVadModelStatus() == ModelStatus.ready;

  /// 检查 SenseVoice 引擎是否完全就绪 (模型 + VAD)
  bool get isSenseVoiceReady {
    return isModelReadyForEngine(EngineType.sensevoice) && isVadModelReady;
  }

  /// 在指定目录中查找模型文件
  bool _hasModelFileInDir(String dirPath, String prefix) {
    final dir = Directory(dirPath);
    if (!dir.existsSync()) return false;
    try {
      return dir.listSync().any((f) {
        final name = f.path.split('/').last;
        return name.startsWith(prefix) && name.endsWith('.onnx');
      });
    } catch (_) {
      return false;
    }
  }

  /// 获取引擎模型的下载 URL
  String getDownloadUrlForEngine(EngineType engineType) {
    final config = ModelConfigs.forEngine(engineType);

    // 优先使用配置文件中的自定义 URL
    if (SettingsService.instance.isInitialized) {
      final customUrl = _getCustomUrlForEngine(engineType);
      if (customUrl != null && customUrl.isNotEmpty) {
        return customUrl;
      }
    }
    return config.defaultUrl;
  }

  /// 获取 VAD 模型下载 URL
  String get vadDownloadUrl => ModelConfigs.sileroVad.defaultUrl;

  /// 从配置获取引擎的自定义 URL
  String? _getCustomUrlForEngine(EngineType engineType) {
    // 后续 Task 5 会扩展 settings.yaml 支持多引擎配置
    // 目前仅支持 Zipformer 的 custom_url
    if (engineType == EngineType.zipformer) {
      return SettingsService.instance.customModelUrl;
    }
    return null;
  }

  /// 获取引擎模型的期望目录结构描述
  /// Story 2-7: 解压时会剥离压缩包顶层目录，所以文件直接在引擎目录下
  String getExpectedStructureForEngine(EngineType engineType) {
    final config = ModelConfigs.forEngine(engineType);
    switch (engineType) {
      case EngineType.zipformer:
        return '''
models/${config.dirName}/
├── encoder-epoch-*.onnx
├── decoder-epoch-*.onnx
├── joiner-epoch-*.onnx
└── tokens.txt
''';
      case EngineType.sensevoice:
        return '''
models/${config.dirName}/
├── model.onnx (或 model.int8.onnx)
└── tokens.txt
''';
    }
  }

  /// 获取 VAD 模型的期望结构描述
  String get vadExpectedStructure => '''
models/vad/
└── silero_vad.onnx
''';

  /// 下载指定引擎的模型
  Future<String> downloadModelForEngine(
    EngineType engineType, {
    ProgressCallback? onProgress,
    int maxRetries = 3,
  }) async {
    final config = ModelConfigs.forEngine(engineType);
    final url = getDownloadUrlForEngine(engineType);
    final tempPath = '$_xdgDataHome/nextalk/temp_${config.dirName}.tar.bz2';

    return _downloadFile(
      url: url,
      tempPath: tempPath,
      onProgress: onProgress,
      maxRetries: maxRetries,
    );
  }

  /// 下载 VAD 模型 (单文件)
  Future<String> downloadVadModel({
    ProgressCallback? onProgress,
    int maxRetries = 3,
  }) async {
    final url = vadDownloadUrl;
    final targetPath = vadModelFilePath;

    // 确保目录存在
    final vadDir = Directory(vadModelPath);
    if (!vadDir.existsSync()) {
      vadDir.createSync(recursive: true);
    }

    return _downloadFile(
      url: url,
      tempPath: targetPath, // VAD 是单文件，直接下载到目标位置
      onProgress: onProgress,
      maxRetries: maxRetries,
    );
  }

  /// 通用文件下载方法
  Future<String> _downloadFile({
    required String url,
    required String tempPath,
    ProgressCallback? onProgress,
    int maxRetries = 3,
  }) async {
    // 确保目录存在
    final baseDir = Directory('$_xdgDataHome/nextalk');
    if (!baseDir.existsSync()) {
      baseDir.createSync(recursive: true);
    }

    final tempFile = File(tempPath);
    Object lastException = Exception('下载失败');

    _cancelToken = CancelToken();
    bool isCancelled = false;
    _cancelToken!.whenCancel.then((_) => isCancelled = true);

    for (var attempt = 1; attempt <= maxRetries; attempt++) {
      HttpClient? client;
      try {
        client = HttpClient();
        client.connectionTimeout = const Duration(seconds: 30);

        // 配置代理
        final httpProxy = Platform.environment['HTTP_PROXY'] ??
            Platform.environment['http_proxy'] ??
            Platform.environment['HTTPS_PROXY'] ??
            Platform.environment['https_proxy'];
        if (httpProxy != null && httpProxy.isNotEmpty) {
          client.findProxy = (uri) => 'PROXY $httpProxy';
          client.badCertificateCallback = (cert, host, port) => true;
        }

        // 检查已下载大小
        int downloadedBytes = 0;
        if (tempFile.existsSync()) {
          downloadedBytes = tempFile.lengthSync();
        }

        // 获取文件总大小
        final uri = Uri.parse(url);
        int totalBytes = 0;
        try {
          final headClient = HttpClient();
          headClient.connectionTimeout = const Duration(seconds: 10);
          final headRequest = await headClient.headUrl(uri);
          final headResponse = await headRequest.close();
          totalBytes = headResponse.contentLength;
          await headResponse.drain<void>();
          headClient.close(force: true);
        } catch (_) {}

        // 如果已经下载完成
        if (totalBytes > 0 && downloadedBytes >= totalBytes) {
          onProgress?.call(1.0, '下载完成');
          client.close();
          return tempPath;
        }

        // 发起 GET 请求
        onProgress?.call(0.0, '下载中 (尝试 $attempt/$maxRetries)...',
            downloaded: downloadedBytes, total: totalBytes);

        final request = await client.getUrl(uri);

        // 断点续传
        if (downloadedBytes > 0) {
          request.headers.set('Range', 'bytes=$downloadedBytes-');
        }

        final response = await request.close();
        final statusCode = response.statusCode;
        final isResuming = statusCode == 206;

        if (downloadedBytes > 0 && !isResuming) {
          if (tempFile.existsSync()) {
            tempFile.deleteSync();
          }
          downloadedBytes = 0;
        }

        // 计算总大小
        final contentLength = response.contentLength;
        final expectedTotal = isResuming
            ? downloadedBytes + contentLength
            : (totalBytes > 0 ? totalBytes : contentLength);

        // 下载
        final raf = tempFile.openSync(
            mode: isResuming ? FileMode.append : FileMode.write);
        int received = isResuming ? downloadedBytes : 0;

        try {
          await for (final chunk in response) {
            if (isCancelled) {
              throw Exception('用户取消下载');
            }
            raf.writeFromSync(chunk);
            received += chunk.length;

            if (expectedTotal > 0) {
              final progress = received / expectedTotal;
              onProgress?.call(
                progress,
                '下载中: ${(progress * 100).toStringAsFixed(1)}%',
                downloaded: received,
                total: expectedTotal,
              );
            }
          }
        } finally {
          raf.closeSync();
        }

        onProgress?.call(1.0, '下载完成',
            downloaded: received, total: expectedTotal);
        client.close();
        return tempPath;
      } catch (e) {
        client?.close();
        lastException = e is Exception ? e : Exception(e.toString());

        if (isCancelled) {
          throw DioException(
            requestOptions: RequestOptions(path: url),
            type: DioExceptionType.cancel,
          );
        }

        if (attempt < maxRetries) {
          onProgress?.call(0.0, '下载失败，3秒后重试...', downloaded: 0, total: 0);
          await Future.delayed(const Duration(seconds: 3));
        }
      }
    }

    throw lastException;
  }

  /// 解压指定引擎的模型
  Future<void> extractModelForEngine(
    EngineType engineType,
    String archivePath, {
    ProgressCallback? onProgress,
  }) async {
    final config = ModelConfigs.forEngine(engineType);
    final targetPath = getModelPathForEngine(engineType);

    onProgress?.call(0.0, '解压中 (后台处理)...', downloaded: 0, total: 0);

    await Isolate.run(() => _extractInIsolate(
          archivePath,
          targetPath,
          config.archiveTopDir,
        ));

    onProgress?.call(1.0, '解压完成', downloaded: 0, total: 0);
  }

  /// 确保指定引擎的模型就绪
  Future<ModelError> ensureModelReadyForEngine(
    EngineType engineType, {
    ProgressCallback? onProgress,
  }) async {
    final config = ModelConfigs.forEngine(engineType);

    // 1. 检查现有模型
    final status = checkModelStatusForEngine(engineType);
    if (status == ModelStatus.ready) {
      onProgress?.call(1.0, '${config.displayName} 模型已就绪', downloaded: 0, total: 0);
      return ModelError.none;
    }

    final tempPath = '$_xdgDataHome/nextalk/temp_${config.dirName}.tar.bz2';
    final tempFile = File(tempPath);
    bool downloadCompleted = false;

    try {
      // 2. 下载 (0% - 60%)
      onProgress?.call(0.0, '开始下载 ${config.displayName}...', downloaded: 0, total: 0);
      await downloadModelForEngine(
        engineType,
        onProgress: (p, s, {int downloaded = 0, int total = 0}) =>
            onProgress?.call(p * 0.6, s, downloaded: downloaded, total: total),
        maxRetries: 3,
      );
      downloadCompleted = true;

      // 3. 校验 (60% - 70%)
      if (config.sha256 != null) {
        onProgress?.call(0.6, '校验中...', downloaded: 0, total: 0);
        final valid = await _verifyChecksumForFile(tempPath, config.sha256!);
        if (!valid) {
          tempFile.deleteSync();
          return ModelError.checksumMismatch;
        }
      }

      // 4. 解压 (70% - 100%)
      onProgress?.call(0.7, '解压中...', downloaded: 0, total: 0);
      await extractModelForEngine(
        engineType,
        tempPath,
        onProgress: (p, s, {int downloaded = 0, int total = 0}) =>
            onProgress?.call(0.7 + p * 0.3, s, downloaded: 0, total: 0),
      );

      // 5. 清理临时文件
      if (tempFile.existsSync()) {
        tempFile.deleteSync();
      }

      onProgress?.call(1.0, '${config.displayName} 模型准备完成', downloaded: 0, total: 0);
      return ModelError.none;
    } on DioException catch (e) {
      if (e.type == DioExceptionType.cancel) {
        return ModelError.downloadCancelled;
      }
      return ModelError.networkError;
    } on FileSystemException catch (e) {
      if (downloadCompleted) {
        _cleanupTempFile(tempFile);
      }
      if (e.message.contains('No space')) {
        return ModelError.diskSpaceError;
      }
      return ModelError.permissionDenied;
    } catch (e) {
      if (downloadCompleted) {
        _cleanupTempFile(tempFile);
        return ModelError.extractionFailed;
      } else {
        return ModelError.networkError;
      }
    }
  }

  /// 确保 VAD 模型就绪 (单文件下载)
  Future<ModelError> ensureVadModelReady({
    ProgressCallback? onProgress,
  }) async {
    // 1. 检查现有模型
    final status = checkVadModelStatus();
    if (status == ModelStatus.ready) {
      onProgress?.call(1.0, 'VAD 模型已就绪', downloaded: 0, total: 0);
      return ModelError.none;
    }

    try {
      // 2. 下载 (0% - 100%)
      onProgress?.call(0.0, '开始下载 VAD 模型...', downloaded: 0, total: 0);
      await downloadVadModel(
        onProgress: onProgress,
        maxRetries: 3,
      );

      onProgress?.call(1.0, 'VAD 模型准备完成', downloaded: 0, total: 0);
      return ModelError.none;
    } on DioException catch (e) {
      if (e.type == DioExceptionType.cancel) {
        return ModelError.downloadCancelled;
      }
      return ModelError.networkError;
    } on FileSystemException catch (e) {
      if (e.message.contains('No space')) {
        return ModelError.diskSpaceError;
      }
      return ModelError.permissionDenied;
    } catch (_) {
      return ModelError.networkError;
    }
  }

  /// 确保 SenseVoice 引擎完全就绪 (模型 + VAD)
  Future<ModelError> ensureSenseVoiceReady({
    ProgressCallback? onProgress,
  }) async {
    // 1. 确保 SenseVoice 模型就绪 (0% - 80%)
    final modelError = await ensureModelReadyForEngine(
      EngineType.sensevoice,
      onProgress: (p, s, {int downloaded = 0, int total = 0}) =>
          onProgress?.call(p * 0.8, s, downloaded: downloaded, total: total),
    );

    if (modelError != ModelError.none) {
      return modelError;
    }

    // 2. 确保 VAD 模型就绪 (80% - 100%)
    final vadError = await ensureVadModelReady(
      onProgress: (p, s, {int downloaded = 0, int total = 0}) =>
          onProgress?.call(0.8 + p * 0.2, s, downloaded: downloaded, total: total),
    );

    return vadError;
  }

  /// 校验文件 SHA256
  Future<bool> _verifyChecksumForFile(String filePath, String expectedSha256) async {
    final actual = await _computeSha256(filePath);
    return actual == expectedSha256;
  }

  /// 删除指定引擎的模型
  Future<void> deleteModelForEngine(EngineType engineType) async {
    final dir = Directory(getModelPathForEngine(engineType));
    if (dir.existsSync()) {
      await dir.delete(recursive: true);
    }
  }

  /// 删除 VAD 模型
  Future<void> deleteVadModel() async {
    final file = File(vadModelFilePath);
    if (file.existsSync()) {
      await file.delete();
    }
  }

  /// 打开指定引擎的模型目录
  Future<void> openModelDirectoryForEngine(EngineType engineType) async {
    final dir = Directory(getModelPathForEngine(engineType));
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }
    await Process.run('xdg-open', [dir.path]);
  }
}
