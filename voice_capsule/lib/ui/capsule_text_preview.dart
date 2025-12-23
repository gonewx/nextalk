import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../constants/capsule_colors.dart';

/// 胶囊文本预览组件
/// Story 3-2: 胶囊 UI 组件
/// Story 3-3: 新增 isProcessing 支持处理中样式
/// Story 3-7: 新增 isError 支持点击复制错误信息
class CapsuleTextPreview extends StatefulWidget {
  const CapsuleTextPreview({
    super.key,
    required this.text,
    this.showHint = true,
    this.hintText = '正在聆听...',
    this.isProcessing = false,
    this.isError = false,
  });

  /// 显示的文本内容
  final String text;

  /// 是否显示提示文字 (text 为空时)
  final bool showHint;

  /// 提示文字内容
  final String hintText;

  /// 是否处于处理中状态 (AC6: 文字颜色降低透明度)
  final bool isProcessing;

  /// Story 3-7: 是否处于错误状态 (支持点击复制)
  final bool isError;

  @override
  State<CapsuleTextPreview> createState() => _CapsuleTextPreviewState();
}

class _CapsuleTextPreviewState extends State<CapsuleTextPreview> {
  bool _showCopied = false;

  Future<void> _copyToClipboard() async {
    final textToCopy = widget.text.isEmpty && widget.showHint
        ? widget.hintText
        : widget.text;

    await Clipboard.setData(ClipboardData(text: textToCopy));

    setState(() => _showCopied = true);

    // 1.5 秒后恢复原文本
    Future.delayed(const Duration(milliseconds: 1500), () {
      if (mounted) {
        setState(() => _showCopied = false);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final displayText = widget.text.isEmpty && widget.showHint
        ? widget.hintText
        : widget.text;
    final isHint = widget.text.isEmpty && widget.showHint;

    // 确定文字样式: 处理中 > 提示 > 主文字
    TextStyle style;
    if (widget.isProcessing) {
      style = CapsuleTextStyles.processingText;
    } else if (isHint) {
      style = CapsuleTextStyles.hintText;
    } else {
      style = CapsuleTextStyles.primaryText;
    }

    // Story 3-7: 错误状态下显示复制提示或原文本
    final finalText = _showCopied ? '已复制到剪贴板' : displayText;
    final finalStyle = _showCopied
        ? style.copyWith(color: Colors.green.shade300)
        : style;

    // Story 3-7: 错误状态下可点击复制
    if (widget.isError) {
      return MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: _copyToClipboard,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Flexible(
                child: Text(
                  finalText,
                  style: finalStyle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.left,
                ),
              ),
              if (!_showCopied) ...[
                const SizedBox(width: 6),
                Icon(
                  Icons.copy_rounded,
                  size: 14,
                  color: style.color?.withOpacity(0.6),
                ),
              ],
            ],
          ),
        ),
      );
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



