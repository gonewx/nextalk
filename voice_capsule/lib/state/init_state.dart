import '../services/model_manager.dart';

/// 初始化阶段枚举
/// Story 3-7: 初始化向导与错误处理系统
enum InitPhase {
  /// 检测模型状态
  checkingModel,

  /// 选择安装方式
  selectingMode,

  /// 自动下载中
  downloading,

  /// 解压中
  extracting,

  /// 手动安装引导
  manualGuide,

  /// 验证模型
  verifying,

  /// 初始化完成
  completed,

  /// 初始化失败
  error,
}

/// 初始化状态数据
/// Story 3-7: 用于跟踪初始化向导的当前状态
class InitStateData {
  const InitStateData({
    required this.phase,
    this.progress = 0.0,
    this.statusMessage = '',
    this.downloadedBytes = 0,
    this.totalBytes = 0,
    this.errorMessage,
    this.modelError,
    this.canRetry = false,
  });

  /// 当前阶段
  final InitPhase phase;

  /// 进度 (0.0 - 1.0)
  final double progress;

  /// 状态消息
  final String statusMessage;

  /// 已下载字节数
  final int downloadedBytes;

  /// 总字节数
  final int totalBytes;

  /// 错误消息
  final String? errorMessage;

  /// 模型错误类型 (来自 ModelManager)
  final ModelError? modelError;

  /// 是否可以重试
  final bool canRetry;

  // ============ 工厂构造函数 ============

  /// 检测模型状态
  factory InitStateData.checking() => const InitStateData(
        phase: InitPhase.checkingModel,
        statusMessage: '检测模型状态...',
      );

  /// 选择安装方式
  factory InitStateData.selectMode() => const InitStateData(
        phase: InitPhase.selectingMode,
      );

  /// 下载中
  factory InitStateData.downloading({
    required double progress,
    required int downloaded,
    required int total,
  }) =>
      InitStateData(
        phase: InitPhase.downloading,
        progress: progress,
        downloadedBytes: downloaded,
        totalBytes: total,
        statusMessage: '下载中: ${(progress * 100).toStringAsFixed(1)}%',
      );

  /// 解压中
  factory InitStateData.extracting(double progress) => InitStateData(
        phase: InitPhase.extracting,
        progress: progress,
        statusMessage: '解压中: ${(progress * 100).toStringAsFixed(1)}%',
      );

  /// 手动安装引导
  factory InitStateData.manualGuide() => const InitStateData(
        phase: InitPhase.manualGuide,
      );

  /// 验证模型
  factory InitStateData.verifying() => const InitStateData(
        phase: InitPhase.verifying,
        statusMessage: '验证模型...',
      );

  /// 初始化完成
  factory InitStateData.completed() => const InitStateData(
        phase: InitPhase.completed,
        progress: 1.0,
        statusMessage: '初始化完成',
      );

  /// 初始化错误
  factory InitStateData.error(ModelError error, {String? message}) =>
      InitStateData(
        phase: InitPhase.error,
        modelError: error,
        errorMessage: message ?? _defaultErrorMessage(error),
        canRetry: error != ModelError.permissionDenied,
      );

  /// 默认错误消息映射
  static String _defaultErrorMessage(ModelError error) => switch (error) {
        ModelError.networkError => '网络错误，请检查网络连接',
        ModelError.diskSpaceError => '磁盘空间不足',
        ModelError.checksumMismatch => '文件校验失败，请重新下载',
        ModelError.extractionFailed => '解压失败',
        ModelError.permissionDenied => '权限不足',
        ModelError.downloadCancelled => '下载已取消',
        ModelError.none => '',
      };

  /// 格式化下载大小 (如 "68MB / 150MB")
  String get formattedSize {
    if (totalBytes == 0) return '';
    final downloaded = (downloadedBytes / 1024 / 1024).toStringAsFixed(0);
    final total = (totalBytes / 1024 / 1024).toStringAsFixed(0);
    return '${downloaded}MB / ${total}MB';
  }
}
