import 'package:flutter/material.dart';

import '../constants/animation_constants.dart';
import '../constants/capsule_colors.dart';

/// 脉冲指示器 (处理中状态)
/// Story 3-3: 状态机与动画系统
/// 400ms 周期，Scale 1.0 → 1.2 → 1.0 快速脉冲
class PulseIndicator extends StatefulWidget {
  const PulseIndicator({
    super.key,
    this.color = CapsuleColors.accentRed,
    this.size = 30.0,
    this.animate = true,
  });

  /// 指示器颜色
  final Color color;

  /// 指示器尺寸 (直径)
  final double size;

  /// 是否启用动画
  final bool animate;

  @override
  State<PulseIndicator> createState() => _PulseIndicatorState();
}

class _PulseIndicatorState extends State<PulseIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: AnimationConstants.pulseDuration,
      vsync: this,
    );

    // 使用 TweenSequence 实现 1.0 → 1.2 → 1.0 的脉冲效果
    _scaleAnimation = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: 1.0, end: AnimationConstants.pulseMaxScale),
        weight: 50,
      ),
      TweenSequenceItem(
        tween: Tween(begin: AnimationConstants.pulseMaxScale, end: 1.0),
        weight: 50,
      ),
    ]).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    ));

    if (widget.animate) {
      _controller.repeat();
    }
  }

  @override
  void didUpdateWidget(PulseIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.animate != oldWidget.animate) {
      if (widget.animate) {
        _controller.repeat();
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
      animation: _scaleAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: child,
        );
      },
      child: Container(
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(
          color: widget.color,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}




