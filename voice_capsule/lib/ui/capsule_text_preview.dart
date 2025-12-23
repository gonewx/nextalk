import 'package:flutter/material.dart';
import '../constants/capsule_colors.dart';

/// 胶囊文本预览组件
/// Story 3-2: 胶囊 UI 组件
/// Story 3-3: 新增 isProcessing 支持处理中样式
class CapsuleTextPreview extends StatelessWidget {
  const CapsuleTextPreview({
    super.key,
    required this.text,
    this.showHint = true,
    this.hintText = '正在聆听...',
    this.isProcessing = false,
  });

  /// 显示的文本内容
  final String text;

  /// 是否显示提示文字 (text 为空时)
  final bool showHint;

  /// 提示文字内容
  final String hintText;

  /// 是否处于处理中状态 (AC6: 文字颜色降低透明度)
  final bool isProcessing;

  @override
  Widget build(BuildContext context) {
    final displayText = text.isEmpty && showHint ? hintText : text;
    final isHint = text.isEmpty && showHint;

    // 确定文字样式: 处理中 > 提示 > 主文字
    TextStyle style;
    if (isProcessing) {
      style = CapsuleTextStyles.processingText;
    } else if (isHint) {
      style = CapsuleTextStyles.hintText;
    } else {
      style = CapsuleTextStyles.primaryText;
    }

    return Text(
      displayText,
      style: style,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      textAlign: TextAlign.left,
    );
  }
}



