import 'package:flutter/material.dart';
import '../constants/capsule_colors.dart';
import '../constants/window_constants.dart';
import '../services/window_service.dart';
import 'capsule_text_preview.dart';

/// 胶囊核心 Widget
/// Story 3-2: 胶囊 UI 组件
class CapsuleWidget extends StatelessWidget {
  const CapsuleWidget({
    super.key,
    this.text = '',
    this.showHint = true,
    this.hintText = '正在聆听...',
  });

  /// 显示的文本内容
  final String text;

  /// 是否显示提示文字 (text 为空时)
  final bool showHint;

  /// 提示文字内容
  final String hintText;

  /// 状态指示器区域尺寸
  static const double _indicatorSize = 30.0;

  /// 光标区域宽度
  static const double _cursorAreaWidth = 12.0;

  /// 内边距
  static const double _horizontalPadding = 25.0;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      // 拖拽移动支持 - 继承自 Story 3-1
      // 使用 windowManager.startDragging() 而非手动坐标计算
      // 原因: 避免与窗口管理器冲突，由底层 GTK 处理拖拽逻辑
      onPanStart: (_) => WindowService.instance.startDragging(),
      child: Center(
        child: Container(
          constraints: const BoxConstraints(
            minWidth: WindowConstants.capsuleMinWidth,
            maxWidth: WindowConstants.capsuleWidth,
          ),
          height: WindowConstants.capsuleHeight,
          decoration: BoxDecoration(
            // AC3: 背景色
            color: CapsuleColors.background,
            // AC2: 圆角
            borderRadius:
                BorderRadius.circular(WindowConstants.capsuleRadius),
            // AC4: 内发光描边
            border: Border.all(
              color: CapsuleColors.borderGlow,
              width: 1.0,
            ),
            // AC5: 外部阴影
            boxShadow: const [
              BoxShadow(
                color: CapsuleColors.shadow,
                blurRadius: 20.0,
                spreadRadius: 2.0,
                offset: Offset(0, 4),
              ),
            ],
          ),
          // AC9: 内边距
          padding: const EdgeInsets.symmetric(horizontal: _horizontalPadding),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // AC6: 左侧状态指示器区域
              const _IndicatorPlaceholder(size: _indicatorSize),
              const SizedBox(width: 12),

              // AC7: 中间文本预览区
              Flexible(
                child: CapsuleTextPreview(
                  text: text,
                  showHint: showHint,
                  hintText: hintText,
                ),
              ),

              // AC8: 右侧光标占位区
              const SizedBox(width: _cursorAreaWidth),
            ],
          ),
        ),
      ),
    );
  }
}

/// 状态指示器占位 Widget
/// Story 3-3 将替换为具体动画实现
class _IndicatorPlaceholder extends StatelessWidget {
  const _IndicatorPlaceholder({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(
        // 占位圆点 - Story 3-3 替换为动画
        color: CapsuleColors.accentRed,
        shape: BoxShape.circle,
      ),
    );
  }
}
