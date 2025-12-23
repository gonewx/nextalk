import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../constants/animation_constants.dart';
import '../constants/capsule_colors.dart';

/// 呼吸红点组件
/// Story 3-3: 状态机与动画系统
/// 使用正弦函数实现呼吸缩放效果: 1.0 + 0.1 * sin(t)
class BreathingDot extends StatefulWidget {
  const BreathingDot({
    super.key,
    this.color = CapsuleColors.accentRed,
    this.size = 30.0,
    this.animate = true,
  });

  /// 圆点颜色
  final Color color;

  /// 圆点尺寸 (直径)
  final double size;

  /// 是否启用动画
  final bool animate;

  @override
  State<BreathingDot> createState() => _BreathingDotState();
}

class _BreathingDotState extends State<BreathingDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: AnimationConstants.breathingPeriod,
      vsync: this,
    );
    if (widget.animate) {
      _controller.repeat();
    }
  }

  @override
  void didUpdateWidget(BreathingDot oldWidget) {
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
      animation: _controller,
      builder: (context, child) {
        // 呼吸公式: 1.0 + 0.1 * (1 + sin(t * 2π)) / 2 = 范围 [1.0, 1.1]
        // 符合 AC2 规范: Scale 1.0 -> 1.1 -> 1.0
        final normalizedSin = (1 + math.sin(_controller.value * 2 * math.pi)) / 2;
        final scale = AnimationConstants.breathingBaseScale +
            AnimationConstants.breathingAmplitude * normalizedSin;

        return Transform.scale(
          scale: scale,
          child: Container(
            width: widget.size,
            height: widget.size,
            decoration: BoxDecoration(
              color: widget.color,
              shape: BoxShape.circle,
              // 光晕效果：随呼吸律动
              boxShadow: [
                BoxShadow(
                  color: widget.color.withValues(alpha: 0.6),
                  blurRadius: 8 * scale, // 模糊半径随心跳变大
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}





