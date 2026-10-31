import 'package:flutter/material.dart';
import '../../constants/capsule_colors.dart';
import '../../constants/settings_constants.dart';
import '../../l10n/app_localizations.dart';

/// 手动安装引导组件
/// Story 3-7: 初始化向导 - AC5, AC6, AC7
/// Story 3-8: 国际化 - AC9
/// Story 2-7: 多模型 ASR 支持 - 动态显示不同引擎的下载说明
/// 提供下载链接、目标路径和检测按钮
class ManualInstallGuide extends StatelessWidget {
  const ManualInstallGuide({
    super.key,
    required this.onCopyLink,
    required this.onOpenDirectory,
    required this.onVerifyModel,
    required this.onSwitchToAuto,
    required this.engineType,
    required this.modelUrl,
    required this.targetPath,
    required this.expectedStructure,
    this.vadUrl,
    this.vadExpectedStructure,
  });

  /// 复制链接回调（参数为要复制的 URL）
  final void Function(String url) onCopyLink;

  /// 打开目录回调
  final VoidCallback onOpenDirectory;

  /// 检测模型回调
  final VoidCallback onVerifyModel;

  /// 切换到自动下载回调
  final VoidCallback onSwitchToAuto;

  /// 当前引擎类型
  final EngineType engineType;

  /// 模型下载 URL
  final String modelUrl;

  /// 目标路径
  final String targetPath;

  /// 期望的目录结构
  final String expectedStructure;

  /// VAD 模型下载 URL (离线引擎需要)
  final String? vadUrl;

  /// VAD 期望的目录结构 (离线引擎需要)
  final String? vadExpectedStructure;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final needsVad = engineType != EngineType.zipformer;
    final engineName = switch (engineType) {
      EngineType.zipformer => 'Zipformer',
      EngineType.sensevoice => 'SenseVoice',
      EngineType.qwen3Asr => 'Qwen3-ASR 0.6B',
    };

    return Container(
      constraints: const BoxConstraints(maxWidth: 520),
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
          // 标题（显示当前引擎类型）
          Center(
            child: Text(
              '📁 ${l10n?.wizardManualInstallTitle ?? '手动安装模型'} ($engineName)',
              style: const TextStyle(
                color: CapsuleColors.textWhite,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 20),

          // 步骤 1: 下载 ASR 模型
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
                  onPressed: () => onCopyLink(modelUrl),
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

          // 步骤 1.5: 下载 VAD 模型（离线引擎需要）
          if (needsVad && vadUrl != null) ...[
            _buildStep(
              context: context,
              number: '1b',
              title: '下载 VAD 模型 (语音活动检测):',
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _truncateUrl(vadUrl!),
                      style: TextStyle(
                        color: CapsuleColors.textHint,
                        fontSize: 12,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  TextButton.icon(
                    onPressed: () => onCopyLink(vadUrl!),
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
          ],

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

          // 步骤 3: ASR 模型目录结构说明
          _buildStep(
            context: context,
            number: '3',
            title: l10n?.wizardStep3Structure ?? '目录结构应为:',
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black26,
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                expectedStructure.trim(),
                style: TextStyle(
                  color: CapsuleColors.textHint,
                  fontSize: 11,
                  fontFamily: 'monospace',
                  height: 1.5,
                ),
              ),
            ),
          ),

          // 步骤 3b: VAD 模型目录结构（离线引擎需要）
          if (needsVad && vadExpectedStructure != null) ...[
            const SizedBox(height: 12),
            _buildStep(
              context: context,
              number: '3b',
              title: 'VAD 模型结构:',
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.black26,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: SelectableText(
                  vadExpectedStructure!.trim(),
                  style: TextStyle(
                    color: CapsuleColors.textHint,
                    fontSize: 11,
                    fontFamily: 'monospace',
                    height: 1.5,
                  ),
                ),
              ),
            ),
          ],
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
