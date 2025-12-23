import 'package:flutter/material.dart';

import '../constants/animation_constants.dart';
import '../constants/capsule_colors.dart';

/// 闪烁光标组件
/// Story 3-3: 状态机与动画系统
/// 800ms 周期，EaseInOut，Opacity 1.0 <-> 0.0 来回闪烁
class CursorBlink extends StatefulWidget {
  const CursorBlink({
    super.key,
    this.color = CapsuleColors.textHint,
    this.width = 2.0,
    this.height = 20.0,
    this.animate = true,
  });

  /// 光标颜色
  final Color color;

  /// 光标宽度
  final double width;

  /// 光标高度
  final double height;

  /// 是否启用动画
  final bool animate;

  @override
  State<CursorBlink> createState() => _CursorBlinkState();
}

class _CursorBlinkState extends State<CursorBlink>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: AnimationConstants.cursorDuration,
      vsync: this,
    );

    _opacityAnimation = Tween<double>(
      begin: 1.0,
      end: 0.0,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: AnimationConstants.cursorCurve,
    ));

    if (widget.animate) {
      _controller.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(CursorBlink oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.animate != oldWidget.animate) {
      if (widget.animate) {
        _controller.repeat(reverse: true);
      } else {
        _controller.stop();
        _controller.value = 0;
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _opacityAnimation,
      builder: (context, child) {
        return Opacity(
          opacity: _opacityAnimation.value,
          child: child,
        );
      },
      child: Container(
        width: widget.width,
        height: widget.height,
        decoration: BoxDecoration(
          color: widget.color,
          borderRadius: BorderRadius.circular(1.0),
        ),
      ),
    );
  }
}





