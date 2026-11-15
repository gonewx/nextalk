import 'package:flutter/material.dart';
import '../../constants/capsule_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../state/init_state.dart';

/// 下载进度组件
/// Story 3-7: 初始化向导 - AC3, AC4
/// Story 3-8: 国际化 - AC9
/// 显示进度百分比和已下载大小，支持切换手动安装和取消
class DownloadProgress extends StatelessWidget {
  const DownloadProgress({
    super.key,
    required this.state,
    required this.onSwitchToManual,
    required this.onCancel,
    this.onRetry,
    this.cancelling = false,
  });

  /// 当前初始化状态
  final InitStateData state;
  final bool cancelling;

  /// 切换到手动安装回调
  final VoidCallback onSwitchToManual;

  /// 取消下载回调
  final VoidCallback onCancel;

  /// 重试下载回调 (错误时可用)
  final VoidCallback? onRetry;

  bool get _isError => state.phase == InitPhase.error;
  bool get _isExtracting => state.phase == InitPhase.extracting;
  bool get _isVerifying => state.phase == InitPhase.verifying;

  /// Story 3-8: 使用国际化获取标题
  String _getTitle(AppLocalizations? l10n) {
    if (cancelling) return l10n?.localeName == 'en' ? 'Cancelling…' : '正在取消…';
    if (_isError) return '❌ ${l10n?.wizardDownloadFailed ?? '下载失败'}';
    if (_isExtracting) return '📦 ${l10n?.wizardExtractingModel ?? '解压模型...'}';
    if (_isVerifying) return '🔍 ${l10n?.wizardVerifyingFile ?? '校验文件...'}';
    return '⬇️ ${l10n?.wizardDownloadingModel ?? '正在下载模型...'}';
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF242424),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
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
            _getTitle(l10n),
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
              state.errorMessage ?? (l10n?.errorUnknown ?? '未知错误'),
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
              value: cancelling ||
                      (_isExtracting || _isVerifying) ||
                      (state.totalBytes == 0 && state.progress == 0)
                  ? null
                  : state.progress,
              backgroundColor: CapsuleColors.borderGlow,
              valueColor:
                  AlwaysStoppedAnimation<Color>(CapsuleColors.accentRed),
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

          if (!_isError && state.statusMessage.isNotEmpty)
            Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Semantics(
                    liveRegion: true,
                    child: Text(
                        cancelling
                            ? (Localizations.localeOf(context).languageCode ==
                                    'zh'
                                ? '正在停止任务，请稍候…'
                                : 'Stopping the task. Please wait…')
                            : state.statusMessage,
                        key: const ValueKey('download-status'),
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white70)))),
          // 按钮区域
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // 切换手动安装
              TextButton(
                onPressed: cancelling ? null : onSwitchToManual,
                child: Text(
                  l10n?.wizardSwitchManual ?? '切换手动安装',
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
                  child: Text(
                    l10n?.wizardRetry ?? '重试',
                    style: const TextStyle(
                      color: CapsuleColors.accentRed,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                )
              else
                TextButton(
                  onPressed: cancelling ? null : onCancel,
                  child: Text(
                    l10n?.wizardCancel ?? '取消',
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
