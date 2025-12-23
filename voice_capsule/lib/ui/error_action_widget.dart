import 'package:flutter/material.dart';
import '../constants/capsule_colors.dart';
import '../state/capsule_state.dart';

/// 错误操作按钮定义
/// Story 3-7: 错误处理系统
class ErrorAction {
  const ErrorAction({
    required this.label,
    required this.onPressed,
    this.isPrimary = false,
  });

  /// 按钮文本
  final String label;

  /// 点击回调
  final VoidCallback onPressed;

  /// 是否为主要操作 (高亮显示)
  final bool isPrimary;
}

/// 带操作按钮的错误 UI 组件
/// Story 3-7: AC10-16 错误状态下提供可操作的恢复按钮
class ErrorActionWidget extends StatelessWidget {
  const ErrorActionWidget({
    super.key,
    required this.errorType,
    required this.message,
    required this.actions,
    this.preservedText, // 需保护的文本 (AC15)
    this.iconColor,
  });

  /// 错误类型
  final CapsuleErrorType errorType;

  /// 错误消息
  final String message;

  /// 操作按钮列表 (最多显示 3 个)
  final List<ErrorAction> actions;

  /// 需保护的用户文本 (AC15: 提交失败时保护文本)
  final String? preservedText;

  /// 自定义图标颜色 (保留用于未来扩展)
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // 错误消息
        Text(
          message,
          style: const TextStyle(
            color: CapsuleColors.textWhite,
            fontSize: 14,
          ),
          textAlign: TextAlign.center,
        ),

        // 保护的文本 (AC15)
        if (preservedText != null && preservedText!.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            '"$preservedText"',
            style: TextStyle(
              color: CapsuleColors.textWhite.withOpacity(0.7),
              fontSize: 12,
              fontStyle: FontStyle.italic,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],

        // 操作按钮行 (最多 3 个)
        if (actions.isNotEmpty) ...[
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: actions.take(3).map((action) {
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: action.isPrimary
                    ? ElevatedButton(
                        onPressed: action.onPressed,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: CapsuleColors.accentRed,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: Text(
                          action.label,
                          style: const TextStyle(fontSize: 12),
                        ),
                      )
                    : TextButton(
                        onPressed: action.onPressed,
                        style: TextButton.styleFrom(
                          foregroundColor: CapsuleColors.textHint,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: Text(
                          action.label,
                          style: const TextStyle(fontSize: 12),
                        ),
                      ),
              );
            }).toList(),
          ),
        ],
      ],
    );
  }
}
