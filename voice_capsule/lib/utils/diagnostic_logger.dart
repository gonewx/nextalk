import 'dart:io';

/// 诊断日志工具
/// Story 3-7: 用于记录应用运行时的诊断信息和异常
class DiagnosticLogger {
  DiagnosticLogger._();

  static final DiagnosticLogger instance = DiagnosticLogger._();

  /// XDG 数据目录
  static String get _xdgDataHome {
    final xdgData = Platform.environment['XDG_DATA_HOME'];
    if (xdgData != null && xdgData.isNotEmpty) return xdgData;
    final home = Platform.environment['HOME']!;
    return '$home/.local/share';
  }

  /// 日志文件路径
  static String get logPath => '$_xdgDataHome/nextalk/logs/diagnostic.log';

  /// 最大日志文件大小 (1MB)
  static const int _maxLogSize = 1024 * 1024;

  /// 日志级别常量
  static const String levelDebug = 'DEBUG';
  static const String levelInfo = 'INFO';
  static const String levelWarn = 'WARN';
  static const String levelError = 'ERROR';
  static const String levelFatal = 'FATAL';

  bool _isInitialized = false;

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 初始化日志系统 (创建目录)
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      final logDir = Directory('$_xdgDataHome/nextalk/logs');
      if (!logDir.existsSync()) {
        logDir.createSync(recursive: true);
      }

      // 检查日志文件大小，超过则轮转
      final logFile = File(logPath);
      if (logFile.existsSync() && logFile.lengthSync() > _maxLogSize) {
        await _rotateLog(logFile);
      }

      _isInitialized = true;
      info('DiagnosticLogger', '日志系统初始化完成');
    } catch (e) {
      stderr.writeln('DiagnosticLogger: 初始化失败 - $e');
    }
  }

  /// 日志轮转 (重命名旧文件)
  Future<void> _rotateLog(File logFile) async {
    try {
      final timestamp = DateTime.now()
          .toIso8601String()
          .replaceAll(':', '-')
          .replaceAll('.', '-');
      final backupPath = '${logPath}_$timestamp.bak';
      await logFile.rename(backupPath);
    } catch (e) {
      stderr.writeln('DiagnosticLogger: 日志轮转失败 - $e');
    }
  }

  /// 记录日志
  /// 格式: [ISO8601] [LEVEL] [TAG] message
  void log(String level, String tag, String message) {
    final timestamp = DateTime.now().toIso8601String();
    final line = '[$timestamp] [$level] [$tag] $message\n';

    try {
      File(logPath).writeAsStringSync(line, mode: FileMode.append);
    } catch (e) {
      // 日志写入失败时输出到 stderr
      stderr.writeln('DiagnosticLogger: 写入失败 - $line');
    }
  }

  // ============ 便捷方法 ============

  /// 记录调试信息
  void debug(String tag, String message) => log(levelDebug, tag, message);

  /// 记录一般信息
  void info(String tag, String message) => log(levelInfo, tag, message);

  /// 记录警告信息
  void warn(String tag, String message) => log(levelWarn, tag, message);

  /// 记录错误信息
  void error(String tag, String message) => log(levelError, tag, message);

  /// 记录致命错误
  void fatal(String tag, String message) => log(levelFatal, tag, message);

  /// 记录异常 (含堆栈)
  void exception(String tag, Object error, StackTrace? stackTrace) {
    log(levelError, tag, '$error');
    if (stackTrace != null) {
      log(levelError, tag, 'StackTrace:\n$stackTrace');
    }
  }

  /// 导出诊断报告 (用于问题排查)
  Future<String> exportReport({String? modelStatus}) async {
    final buffer = StringBuffer();

    // 1. 系统信息
    buffer.writeln('=== 系统信息 ===');
    buffer.writeln('平台: ${Platform.operatingSystem} ${Platform.operatingSystemVersion}');
    buffer.writeln('Dart 版本: ${Platform.version}');
    buffer.writeln('时间: ${DateTime.now().toIso8601String()}');
    buffer.writeln();

    // 2. 模型状态
    if (modelStatus != null) {
      buffer.writeln('=== 模型状态 ===');
      buffer.writeln(modelStatus);
      buffer.writeln();
    }

    // 3. 最近日志 (最后 50 行)
    buffer.writeln('=== 最近日志 ===');
    final logFile = File(logPath);
    if (logFile.existsSync()) {
      try {
        final lines = await logFile.readAsLines();
        final recentLines =
            lines.length > 50 ? lines.sublist(lines.length - 50) : lines;
        buffer.writeln(recentLines.join('\n'));
      } catch (e) {
        buffer.writeln('(读取日志失败: $e)');
      }
    } else {
      buffer.writeln('(无日志文件)');
    }

    return buffer.toString();
  }
}
