import 'package:flutter/material.dart';
import '../constants/capsule_colors.dart';
import '../services/language_service.dart';

/// 音频设备错误对话框 (Story 3-9: AC16, AC17)
///
/// 用于显示音频设备初始化失败时的错误提示
/// 包含：设备名称、错误原因、解决方法
class AudioDeviceErrorDialog extends StatelessWidget {
  const AudioDeviceErrorDialog({
    super.key,
    required this.deviceName,
    required this.errorReason,
    this.onDismiss,
  });

  /// 配置的设备名称
  final String deviceName;

  /// 错误原因
  final String errorReason;

  /// 关闭回调
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final lang = LanguageService.instance;

    return Dialog(
      backgroundColor: CapsuleColors.backgroundDark,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Container(
        width: 380,
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            Row(
              children: [
                Icon(
                  Icons.mic_off,
                  color: Colors.orange.shade400,
                  size: 28,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    lang.tr('audio_error_title'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // 设备名称
            _buildInfoRow(
              label: lang.tr('audio_error_device'),
              value: deviceName == 'default'
                  ? lang.tr('tray_audio_default')
                  : deviceName,
            ),
            const SizedBox(height: 12),

            // 错误原因
            _buildInfoRow(
              label: lang.tr('audio_error_reason'),
              value: errorReason,
              valueColor: Colors.orange.shade300,
            ),
            const SizedBox(height: 20),

            // 解决方法
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black26,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    lang.tr('audio_error_solution_title'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  _buildSolutionItem(
                    '1.',
                    lang.tr('audio_error_solution_1'),
                  ),
                  const SizedBox(height: 4),
                  _buildSolutionItem(
                    '2.',
                    lang.tr('audio_error_solution_2'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // 按钮
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                ElevatedButton(
                  onPressed: () {
                    Navigator.of(context).pop();
                    onDismiss?.call();
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 12,
                    ),
                  ),
                  child: Text(lang.tr('audio_error_ok')),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow({
    required String label,
    required String value,
    Color? valueColor,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 80,
          child: Text(
            label,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: TextStyle(
              color: valueColor ?? Colors.white,
              fontSize: 14,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSolutionItem(String number, String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          number,
          style: const TextStyle(
            color: Colors.white60,
            fontSize: 13,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              color: Colors.white60,
              fontSize: 13,
            ),
          ),
        ),
      ],
    );
  }

  /// 显示音频设备错误对话框
  static void show(
    BuildContext context, {
    required String deviceName,
    required String errorReason,
    VoidCallback? onDismiss,
  }) {
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (_) => AudioDeviceErrorDialog(
        deviceName: deviceName,
        errorReason: errorReason,
        onDismiss: onDismiss,
      ),
    );
  }
}
