import 'package:flutter/material.dart';
import '../../constants/capsule_colors.dart';
import '../../state/init_state.dart';

/// 下载进度组件
/// Story 3-7: 初始化向导 - AC3, AC4
/// 显示进度百分比和已下载大小，支持切换手动安装和取消
class DownloadProgress extends StatelessWidget {
  const DownloadProgress({
    super.key,
    required this.state,
    required this.onSwitchToManual,
    required this.onCancel,
    this.onRetry,
  });

  /// 当前初始化状态
  final InitStateData state;

  /// 切换到手动安装回调
  final VoidCallback onSwitchToManual;

  /// 取消下载回调
  final VoidCallback onCancel;

  /// 重试下载回调 (错误时可用)
  final VoidCallback? onRetry;

  bool get _isError => state.phase == InitPhase.error;
  bool get _isExtracting => state.phase == InitPhase.extracting;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 400),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: CapsuleColors.background,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CapsuleColors.borderGlow),
        boxShadow: [
          BoxShadow(
            color: CapsuleColors.shadow,
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 标题/状态
          Text(
            _isError
                ? '❌ 下载失败'
                : _isExtracting
                    ? '解压模型...'
                    : '正在下载模型...',
            style: const TextStyle(
              color: CapsuleColors.textWhite,
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 16),

          // 错误消息或进度
          if (_isError) ...[
            Text(
              state.errorMessage ?? '未知错误',
              style: TextStyle(
                color: CapsuleColors.warning,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 16),
          ] else ...[
            // 百分比
            Text(
              '${(state.progress * 100).toStringAsFixed(1)}%',
              style: const TextStyle(
                color: CapsuleColors.textWhite,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),

            // 进度条
            LinearProgressIndicator(
              value: state.progress,
              backgroundColor: CapsuleColors.borderGlow,
              valueColor: AlwaysStoppedAnimation<Color>(CapsuleColors.accentRed),
              borderRadius: BorderRadius.circular(4),
              minHeight: 8,
            ),
            const SizedBox(height: 8),

            // 已下载/总大小
            if (state.formattedSize.isNotEmpty)
              Text(
                state.formattedSize,
                style: TextStyle(
                  color: CapsuleColors.textHint,
                  fontSize: 12,
                ),
              ),
            const SizedBox(height: 16),
          ],

          // 按钮区域
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // 切换手动安装
              TextButton(
                onPressed: onSwitchToManual,
                child: Text(
                  '切换手动安装',
                  style: TextStyle(
                    color: CapsuleColors.textHint,
                    fontSize: 14,
                  ),
                ),
              ),

              // 重试或取消按钮
              if (_isError && onRetry != null)
                TextButton(
                  onPressed: onRetry,
                  child: const Text(
                    '重试',
                    style: TextStyle(
                      color: CapsuleColors.accentRed,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                )
              else
                TextButton(
                  onPressed: onCancel,
                  child: Text(
                    '取消',
                    style: TextStyle(
                      color: CapsuleColors.textHint,
                      fontSize: 14,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
