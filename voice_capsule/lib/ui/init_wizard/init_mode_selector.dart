import 'package:flutter/material.dart';
import '../../constants/capsule_colors.dart';

/// 初始化模式选择器
/// Story 3-7: 初始化向导 - AC2
/// 提供"自动下载"和"手动安装"两种选项
class InitModeSelector extends StatelessWidget {
  const InitModeSelector({
    super.key,
    required this.onAutoDownload,
    required this.onManualInstall,
  });

  /// 自动下载回调
  final VoidCallback onAutoDownload;

  /// 手动安装回调
  final VoidCallback onManualInstall;

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
          // 标题
          const Text(
            '🎤 Nextalk 首次启动',
            style: TextStyle(
              color: CapsuleColors.textWhite,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),

          // 说明文字
          Text(
            '需要下载语音识别模型 (~150MB)',
            style: TextStyle(
              color: CapsuleColors.textHint,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 24),

          // 按钮区域
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // 自动下载按钮 (推荐)
              ElevatedButton(
                onPressed: onAutoDownload,
                style: ElevatedButton.styleFrom(
                  backgroundColor: CapsuleColors.accentRed,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 24,
                    vertical: 16,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '📥 自动下载',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      '(推荐)',
                      style: TextStyle(fontSize: 12),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),

              // 手动安装按钮
              OutlinedButton(
                onPressed: onManualInstall,
                style: OutlinedButton.styleFrom(
                  foregroundColor: CapsuleColors.textHint,
                  side: BorderSide(color: CapsuleColors.borderGlow),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 24,
                    vertical: 16,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '📁 手动安装',
                      style: TextStyle(fontSize: 16),
                    ),
                    SizedBox(height: 4),
                    Text(
                      '',
                      style: TextStyle(fontSize: 12),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
