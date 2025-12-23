import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';

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
typedef ProgressCallback = void Function(double progress, String status, {int downloaded, int total});

class ModelManager {
  static const String _modelName =
      'sherpa-onnx-streaming-zipformer-bilingual-zh-en';
  static const String _archiveName =
      'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20';
  static const String _downloadUrl =
      'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'
      '$_archiveName.tar.bz2';
  static const String _expectedSha256 =
      'fb034d9c586c72c2b1e0c3c0cfcf68d0bfe7eec36f1e2073c7f2edbc1bc5b8e5';

  /// Story 3-7: 下载取消令牌
  CancelToken? _cancelToken;

  // === Story 3-7: 新增公开静态属性 ===

  /// 获取模型下载 URL (用于手动安装引导显示)
  static String get downloadUrl => _downloadUrl;

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

  /// 下载模型 (支持代理、重试、进度回调、断点续传)
  Future<String> downloadModel({
    ProgressCallback? onProgress,
    int maxRetries = 3,
  }) async {
    // 确保目录存在
    final baseDir = Directory('$_xdgDataHome/nextalk');
    if (!baseDir.existsSync()) {
      baseDir.createSync(recursive: true);
    }

    final dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(minutes: 10),
    ));

    // 检查并配置代理环境变量
    final httpProxy = Platform.environment['HTTP_PROXY'] ??
        Platform.environment['http_proxy'] ??
        Platform.environment['HTTPS_PROXY'] ??
        Platform.environment['https_proxy'];
    if (httpProxy != null && httpProxy.isNotEmpty) {
      print('[ModelManager] 检测到代理: $httpProxy');
      (dio.httpClientAdapter as IOHttpClientAdapter).createHttpClient = () {
        final client = HttpClient();
        client.findProxy = (uri) => 'PROXY $httpProxy';
        client.badCertificateCallback = (cert, host, port) => true;
        return client;
      };
    }

    final tempFile = File(_tempFilePath);
    Object lastException = Exception('下载失败');

    // Story 3-7: 创建新的取消令牌
    _cancelToken = CancelToken();

    // 获取最终下载 URL (跟随重定向)
    String finalUrl = _downloadUrl;
    try {
      final redirectDio = Dio();
      redirectDio.options.followRedirects = false;
      redirectDio.options.validateStatus = (status) => status != null && status < 400;

      var currentUrl = _downloadUrl;
      for (var i = 0; i < 5; i++) { // 最多跟随 5 次重定向
        final response = await redirectDio.head(currentUrl, cancelToken: _cancelToken);
        if (response.statusCode == 301 || response.statusCode == 302) {
          final location = response.headers.value('location');
          if (location != null) {
            currentUrl = location;
            print('[ModelManager] 重定向到: $currentUrl');
            continue;
          }
        }
        break;
      }
      finalUrl = currentUrl;
      redirectDio.close();
      print('[ModelManager] 最终下载 URL: ${finalUrl.substring(0, 80)}...');
    } catch (e) {
      print('[ModelManager] 获取最终 URL 失败: $e，使用原始 URL');
    }

    for (var attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        // 检查已下载的大小（每次尝试时重新检查）
        int downloadedBytes = 0;
        if (tempFile.existsSync()) {
          downloadedBytes = tempFile.lengthSync();
          print('[ModelManager] 发现临时文件: ${(downloadedBytes / 1024 / 1024).toStringAsFixed(1)}MB');
        } else {
          print('[ModelManager] 临时文件不存在: ${tempFile.path}');
        }

        // 获取文件总大小 (使用最终 URL)
        int totalBytes = 0;
        try {
          final headResponse = await dio.head(finalUrl, cancelToken: _cancelToken);
          totalBytes = int.tryParse(
            headResponse.headers.value('content-length') ?? '0',
          ) ?? 0;
          print('[ModelManager] 文件总大小: ${(totalBytes / 1024 / 1024).toStringAsFixed(1)}MB');
        } catch (e) {
          print('[ModelManager] HEAD 请求失败: $e');
        }

        // 如果已经下载完成
        if (totalBytes > 0 && downloadedBytes >= totalBytes) {
          print('[ModelManager] 文件已完整下载');
          onProgress?.call(1.0, '下载完成');
          dio.close();
          return _tempFilePath;
        }

        // 准备断点续传 (即使不知道总大小也尝试续传)
        Map<String, dynamic>? headers;
        if (downloadedBytes > 0) {
          headers = {'Range': 'bytes=$downloadedBytes-'};
          print('[ModelManager] 断点续传: 从 ${(downloadedBytes / 1024 / 1024).toStringAsFixed(1)}MB 处继续');
          if (totalBytes > 0) {
            onProgress?.call(downloadedBytes / totalBytes, '续传中...', downloaded: downloadedBytes, total: totalBytes);
          } else {
            onProgress?.call(0.0, '续传中...', downloaded: downloadedBytes, total: 0);
          }
        } else {
          onProgress?.call(0.0, '下载中 (尝试 $attempt/$maxRetries)...', downloaded: 0, total: totalBytes);
        }

        // 使用流式下载 (使用最终 URL，避免重定向丢失 Range header)
        final response = await dio.get<ResponseBody>(
          finalUrl,
          options: Options(
            responseType: ResponseType.stream,
            headers: headers,
            followRedirects: false, // 已经是最终 URL，不需要重定向
          ),
          cancelToken: _cancelToken,
        );

        // 检查服务器是否支持断点续传
        final statusCode = response.statusCode ?? 200;
        final isResuming = statusCode == 206;
        print('[ModelManager] 服务器响应: $statusCode (${isResuming ? "断点续传" : "完整下载"})');

        if (downloadedBytes > 0 && !isResuming) {
          // 服务器不支持断点续传，删除已有文件重新下载
          print('[ModelManager] 服务器不支持断点续传，重新下载');
          if (tempFile.existsSync()) {
            tempFile.deleteSync();
          }
          downloadedBytes = 0;
        }

        // 获取本次下载的内容长度
        final contentLength = int.tryParse(
          response.headers.value('content-length') ?? '0',
        ) ?? 0;

        // 计算总大小
        final expectedTotal = isResuming
            ? downloadedBytes + contentLength
            : (totalBytes > 0 ? totalBytes : contentLength);

        // 打开文件（续传用追加模式，否则用写入模式）
        print('[ModelManager] 打开文件: ${isResuming ? "追加模式" : "写入模式"}');
        final raf = tempFile.openSync(mode: isResuming ? FileMode.append : FileMode.write);
        int received = isResuming ? downloadedBytes : 0;

        try {
          await for (final chunk in response.data!.stream) {
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
          print('[ModelManager] 文件已关闭，已写入: ${(received / 1024 / 1024).toStringAsFixed(1)}MB');
        }

        print('[ModelManager] 下载完成，文件大小: ${(received / 1024 / 1024).toStringAsFixed(1)}MB');
        onProgress?.call(1.0, '下载完成', downloaded: received, total: expectedTotal);
        dio.close();
        return _tempFilePath;
      } on DioException catch (e) {
        lastException = e;
        // 取消不重试
        if (e.type == DioExceptionType.cancel) {
          print('[ModelManager] 下载被取消，保留临时文件');
          dio.close();
          throw e;
        }
        print('[ModelManager] 下载失败 (DioException): ${e.message}');
        // 检查临时文件状态
        if (tempFile.existsSync()) {
          print('[ModelManager] 临时文件保留: ${(tempFile.lengthSync() / 1024 / 1024).toStringAsFixed(1)}MB');
        } else {
          print('[ModelManager] 警告：临时文件丢失！');
        }
        if (attempt < maxRetries) {
          onProgress?.call(0.0, '下载失败，3秒后重试...', downloaded: 0, total: 0);
          await Future.delayed(const Duration(seconds: 3));
        }
      } catch (e) {
        // 捕获所有其他异常（如 SocketException）
        lastException = e is Exception ? e : Exception(e.toString());
        print('[ModelManager] 下载失败 (${e.runtimeType}): $e');
        // 检查临时文件状态
        if (tempFile.existsSync()) {
          print('[ModelManager] 临时文件保留: ${(tempFile.lengthSync() / 1024 / 1024).toStringAsFixed(1)}MB');
        } else {
          print('[ModelManager] 警告：临时文件丢失！');
        }
        if (attempt < maxRetries) {
          onProgress?.call(0.0, '下载失败，3秒后重试...', downloaded: 0, total: 0);
          await Future.delayed(const Duration(seconds: 3));
        }
      }
    }

    dio.close();
    // 断点续传：失败时不删除临时文件，以便下次续传
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

    await Isolate.run(() => _extractInIsolate(
          archivePath,
          modelPath,
          _archiveName,
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
      onProgress?.call(0.6, '校验中...', downloaded: 0, total: 0);
      final valid = await verifyChecksum(
        _tempFilePath,
        onProgress: (p, s, {int downloaded = 0, int total = 0}) =>
            onProgress?.call(0.6 + p * 0.1, s, downloaded: 0, total: 0),
      );
      if (!valid) {
        tempFile.deleteSync();
        return ModelError.checksumMismatch;
      }

      // 4. 解压 (70% - 100%)
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
}
