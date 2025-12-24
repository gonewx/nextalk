import 'package:flutter/material.dart';
import '../../constants/capsule_colors.dart';
import '../../l10n/app_localizations.dart';

/// 手动安装引导组件
/// Story 3-7: 初始化向导 - AC5, AC6, AC7
/// Story 3-8: 国际化 - AC9
/// 提供下载链接、目标路径和检测按钮
class ManualInstallGuide extends StatelessWidget {
  const ManualInstallGuide({
    super.key,
    required this.onCopyLink,
    required this.onOpenDirectory,
    required this.onVerifyModel,
    required this.onSwitchToAuto,
    this.modelUrl =
        'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2',
    this.targetPath = '~/.local/share/nextalk/models/',
  });

  /// 复制链接回调
  final VoidCallback onCopyLink;

  /// 打开目录回调
  final VoidCallback onOpenDirectory;

  /// 检测模型回调
  final VoidCallback onVerifyModel;

  /// 切换到自动下载回调
  final VoidCallback onSwitchToAuto;

  /// 模型下载 URL
  final String modelUrl;

  /// 目标路径
  final String targetPath;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Container(
      constraints: const BoxConstraints(maxWidth: 480),
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
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题
          Center(
            child: Text(
              '📁 ${l10n?.wizardManualInstallTitle ?? '手动安装模型'}',
              style: const TextStyle(
                color: CapsuleColors.textWhite,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 20),

          // 步骤 1: 下载模型
          _buildStep(
            context: context,
            number: '1',
            title: l10n?.wizardStep1Download ?? '下载模型文件:',
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    _truncateUrl(modelUrl),
                    style: TextStyle(
                      color: CapsuleColors.textHint,
                      fontSize: 12,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: onCopyLink,
                  icon: const Icon(Icons.copy, size: 16),
                  label: Text(l10n?.wizardCopyLink ?? '复制链接'),
                  style: TextButton.styleFrom(
                    foregroundColor: CapsuleColors.accentRed,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // 步骤 2: 解压并放置
          _buildStep(
            context: context,
            number: '2',
            title: l10n?.wizardStep2Extract ?? '解压并放置到:',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 完整显示路径，支持选择复制
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: SelectableText(
                    targetPath,
                    style: TextStyle(
                      color: CapsuleColors.textHint,
                      fontSize: 12,
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: onOpenDirectory,
                  icon: const Icon(Icons.folder_open, size: 16),
                  label: Text(l10n?.wizardOpenDir ?? '打开目录'),
                  style: TextButton.styleFrom(
                    foregroundColor: CapsuleColors.accentRed,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // 步骤 3: 目录结构说明
          _buildStep(
            context: context,
            number: '3',
            title: l10n?.wizardStep3Structure ?? '目录结构应为:',
            child: Tooltip(
              message: 'sherpa-onnx-streaming-zipformer-bilingual-zh-en/',
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.black26,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: SelectableText(
                  'sherpa-onnx-streaming-zipformer-bilingual-zh-en/\n'
                  '  ├── encoder-*.onnx\n'
                  '  ├── decoder-*.onnx\n'
                  '  ├── joiner-*.onnx\n'
                  '  └── tokens.txt',
                  style: TextStyle(
                    color: CapsuleColors.textHint,
                    fontSize: 11,
                    fontFamily: 'monospace',
                    height: 1.5,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // 按钮区域
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // 检测模型按钮
              ElevatedButton(
                onPressed: onVerifyModel,
                style: ElevatedButton.styleFrom(
                  backgroundColor: CapsuleColors.accentRed,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                child: Text(l10n?.wizardVerify ?? '检测模型'),
              ),

              // 返回自动下载
              TextButton(
                onPressed: onSwitchToAuto,
                child: Text(
                  l10n?.wizardBackToAuto ?? '返回自动下载',
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

  Widget _buildStep({
    required BuildContext context,
    required String number,
    required String title,
    required Widget child,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                color: CapsuleColors.accentRed.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text(
                  number,
                  style: TextStyle(
                    color: CapsuleColors.accentRed,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              title,
              style: const TextStyle(
                color: CapsuleColors.textWhite,
                fontSize: 14,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.only(left: 28),
          child: child,
        ),
      ],
    );
  }

  String _truncateUrl(String url) {
    if (url.length <= 50) return url;
    return '${url.substring(0, 30)}...${url.substring(url.length - 17)}';
  }
}
