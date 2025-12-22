import 'package:flutter/material.dart';
import '../constants/capsule_colors.dart';

/// 胶囊文本预览组件
/// Story 3-2: 胶囊 UI 组件
class CapsuleTextPreview extends StatelessWidget {
  const CapsuleTextPreview({
    super.key,
    required this.text,
    this.showHint = true,
    this.hintText = '正在聆听...',
  });

  /// 显示的文本内容
  final String text;

  /// 是否显示提示文字 (text 为空时)
  final bool showHint;

  /// 提示文字内容
  final String hintText;

  @override
  Widget build(BuildContext context) {
    final displayText = text.isEmpty && showHint ? hintText : text;
    final isHint = text.isEmpty && showHint;

    return Text(
      displayText,
      style: isHint ? CapsuleTextStyles.hintText : CapsuleTextStyles.primaryText,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      textAlign: TextAlign.left,
    );
  }
}
