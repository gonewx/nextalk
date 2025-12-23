import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../constants/capsule_colors.dart';
import '../utils/diagnostic_logger.dart';

/// 致命错误对话框
/// Story 3-7: 用于显示应用无法恢复的致命错误 (AC18)
///
/// 功能:
/// - 显示错误信息和堆栈
/// - 复制诊断报告到剪贴板
/// - 提供重启和退出选项
class FatalErrorDialog extends StatelessWidget {
  const FatalErrorDialog({
    super.key,
    required this.error,
    this.stackTrace,
    this.onRestart,
    this.onExit,
  });

  /// 错误对象
  final Object error;

  /// 堆栈跟踪
  final StackTrace? stackTrace;

  /// 重启回调
  final VoidCallback? onRestart;

  /// 退出回调
  final VoidCallback? onExit;

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: CapsuleColors.backgroundDark,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Container(
        width: 400,
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            Row(
              children: [
                Icon(
                  Icons.error_outline,
                  color: Colors.red.shade400,
                  size: 28,
                ),
                const SizedBox(width: 12),
                const Text(
                  '应用程序错误',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // 错误消息
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black26,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                error.toString(),
                style: TextStyle(
                  color: Colors.red.shade300,
                  fontSize: 13,
                  fontFamily: 'monospace',
                ),
                maxLines: 5,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(height: 12),

            // 堆栈跟踪 (可展开)
            if (stackTrace != null)
              ExpansionTile(
                title: const Text(
                  '详细信息',
                  style: TextStyle(color: Colors.white70, fontSize: 14),
                ),
                iconColor: Colors.white70,
                collapsedIconColor: Colors.white70,
                children: [
                  Container(
                    height: 150,
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.black26,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: SingleChildScrollView(
                      child: Text(
                        stackTrace.toString(),
                        style: const TextStyle(
                          color: Colors.white60,
                          fontSize: 11,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            const SizedBox(height: 20),

            // 按钮行
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                // 复制诊断信息
                TextButton.icon(
                  onPressed: () => _copyDiagnostics(context),
                  icon: const Icon(Icons.copy, size: 16),
                  label: const Text('复制诊断'),
                  style: TextButton.styleFrom(
                    foregroundColor: Colors.white70,
                  ),
                ),
                const Spacer(),

                // 退出按钮
                TextButton(
                  onPressed: onExit ?? () => exit(1),
                  style: TextButton.styleFrom(
                    foregroundColor: Colors.white70,
                  ),
                  child: const Text('退出'),
                ),
                const SizedBox(width: 8),

                // 重启按钮 (如果提供了回调)
                if (onRestart != null)
                  ElevatedButton(
                    onPressed: onRestart,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: CapsuleColors.recordingRed,
                    ),
                    child: const Text('重启'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// 复制诊断信息到剪贴板
  Future<void> _copyDiagnostics(BuildContext context) async {
    final report = await DiagnosticLogger.instance.exportReport();
    final fullReport = '''
=== 致命错误 ===
$error

=== 堆栈跟踪 ===
${stackTrace ?? '(无堆栈信息)'}

$report
''';

    await Clipboard.setData(ClipboardData(text: fullReport));

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('诊断信息已复制到剪贴板'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  /// 显示致命错误对话框
  /// 在应用上下文中显示错误，用于 runZonedGuarded 捕获的异常
  static void show(
    BuildContext context, {
    required Object error,
    StackTrace? stackTrace,
    VoidCallback? onRestart,
    VoidCallback? onExit,
  }) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => FatalErrorDialog(
        error: error,
        stackTrace: stackTrace,
        onRestart: onRestart,
        onExit: onExit,
      ),
    );
  }
}
