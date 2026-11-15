import 'package:flutter/material.dart';
import '../../constants/capsule_colors.dart';
import '../../l10n/app_localizations.dart';

/// 初始化模式选择器
/// Story 3-7: 初始化向导 - AC2
/// Story 3-8: 国际化 - AC9
/// 提供"自动下载"和"手动安装"两种选项
class InitModeSelector extends StatelessWidget {
  const InitModeSelector({
    super.key,
    required this.onAutoDownload,
    required this.onManualInstall,
    this.title,
  });

  /// 自动下载回调
  final VoidCallback onAutoDownload;
  final String? title;

  /// 手动安装回调
  final VoidCallback onManualInstall;

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
          // 标题
          Text(
            title ?? '🎤 ${l10n?.wizardFirstLaunch ?? 'Nextalk 首次启动'}',
            style: const TextStyle(
              color: CapsuleColors.textWhite,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),

          // 说明文字
          Text(
            l10n?.wizardModelSizeHint ?? '需要下载语音识别模型',
            style: TextStyle(
              color: CapsuleColors.textHint,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 24),

          // 按钮区域
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 自动下载按钮 (推荐)
                Expanded(
                  child: ElevatedButton(
                    onPressed: onAutoDownload,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: CapsuleColors.accentRed,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 16,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '📥 ${l10n?.wizardAutoDownload ?? '自动下载'}',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          l10n?.wizardRecommended ?? '(推荐)',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 16),

                // 手动安装按钮
                Expanded(
                  child: OutlinedButton(
                    onPressed: onManualInstall,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: CapsuleColors.textHint,
                      side: BorderSide(color: CapsuleColors.borderGlow),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 16,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '📁 ${l10n?.wizardManualMode ?? '手动安装'}',
                          style: const TextStyle(fontSize: 16),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
