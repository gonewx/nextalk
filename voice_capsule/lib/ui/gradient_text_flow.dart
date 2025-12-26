import 'package:flutter/material.dart';

/// 渐变文字流组件
///
/// 实现"文字流"效果：
/// - 最新的文字在右边，字体大、颜色亮
/// - 旧的文字往左推，字体逐渐变小、颜色变淡
/// - 溢出时左边的文字逐渐消失
///
/// 视觉效果：像文字从右边"流入"，往左边"流出"
class GradientTextFlow extends StatelessWidget {
  const GradientTextFlow({
    super.key,
    required this.text,
    this.baseColor = Colors.white,
    this.maxFontSize = 16.0,
    this.minFontSize = 10.0,
    this.maxOpacity = 1.0,
    this.minOpacity = 0.3,
    this.visibleCharCount = 30,
    this.fontWeight = FontWeight.w500,
  });

  /// 要显示的文本
  final String text;

  /// 基础颜色（最新文字的颜色）
  final Color baseColor;

  /// 最大字体大小（最新文字）
  final double maxFontSize;

  /// 最小字体大小（最旧文字）
  final double minFontSize;

  /// 最大不透明度（最新文字）
  final double maxOpacity;

  /// 最小不透明度（最旧文字）
  final double minOpacity;

  /// 可见字符数（超过此数量的旧字符会逐渐隐藏）
  final int visibleCharCount;

  /// 字体粗细
  final FontWeight fontWeight;

  @override
  Widget build(BuildContext context) {
    if (text.isEmpty) {
      return const SizedBox.shrink();
    }

    // 只显示最后 visibleCharCount 个字符（带渐变）
    final displayText = text.length > visibleCharCount
        ? text.substring(text.length - visibleCharCount)
        : text;

    final characters = displayText.characters.toList();
    final charCount = characters.length;

    // 构建每个字符的 TextSpan
    final spans = <InlineSpan>[];

    for (var i = 0; i < charCount; i++) {
      // 计算进度：0.0 (最旧/最左) -> 1.0 (最新/最右)
      final progress = charCount == 1 ? 1.0 : i / (charCount - 1);

      // 渐变计算
      final fontSize = minFontSize + (maxFontSize - minFontSize) * progress;
      final opacity = minOpacity + (maxOpacity - minOpacity) * progress;

      spans.add(
        TextSpan(
          text: characters[i],
          style: TextStyle(
            fontSize: fontSize,
            fontWeight: fontWeight,
            color: baseColor.withValues(alpha: opacity),
            height: 1.2, // 统一行高，避免不同字号导致的垂直偏移
          ),
        ),
      );
    }

    return RichText(
      text: TextSpan(children: spans),
      maxLines: 1,
      overflow: TextOverflow.clip,
      textAlign: TextAlign.right, // 右对齐，新文字固定在右边
    );
  }
}

/// 带淡出遮罩的渐变文字流
///
/// 在左边添加渐变遮罩，让旧文字更自然地"消失"
class GradientTextFlowWithFade extends StatelessWidget {
  const GradientTextFlowWithFade({
    super.key,
    required this.text,
    this.baseColor = Colors.white,
    this.maxFontSize = 16.0,
    this.minFontSize = 10.0,
    this.maxOpacity = 1.0,
    this.minOpacity = 0.3,
    this.visibleCharCount = 30,
    this.fontWeight = FontWeight.w500,
    this.fadeWidth = 30.0,
  });

  final String text;
  final Color baseColor;
  final double maxFontSize;
  final double minFontSize;
  final double maxOpacity;
  final double minOpacity;
  final int visibleCharCount;
  final FontWeight fontWeight;

  /// 左边淡出遮罩的宽度
  final double fadeWidth;

  @override
  Widget build(BuildContext context) {
    if (text.isEmpty) {
      return const SizedBox.shrink();
    }

    return ShaderMask(
      shaderCallback: (Rect bounds) {
        return LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          colors: const [
            Colors.transparent,
            Colors.white,
          ],
          stops: [
            0.0,
            fadeWidth / bounds.width.clamp(fadeWidth, double.infinity),
          ],
        ).createShader(bounds);
      },
      blendMode: BlendMode.dstIn,
      child: GradientTextFlow(
        text: text,
        baseColor: baseColor,
        maxFontSize: maxFontSize,
        minFontSize: minFontSize,
        maxOpacity: maxOpacity,
        minOpacity: minOpacity,
        visibleCharCount: visibleCharCount,
        fontWeight: fontWeight,
      ),
    );
  }
}
