import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../constants/capsule_colors.dart';
import '../services/animation_ticker_service.dart';

/// 呼吸红点组件
/// Story 3-3: 状态机与动画系统
/// 使用全局 AnimationTickerService 实现预热，确保无延迟显示
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
  Ticker? _ticker;

  @override
  void initState() {
    super.initState();
    if (widget.animate) {
      _startTicker();
    }
  }

  void _startTicker() {
    _ticker = createTicker((_) {
      // 每帧触发重绘，使用全局 ticker 的值
      if (mounted) setState(() {});
    });
    _ticker!.start();
  }

  void _stopTicker() {
    _ticker?.stop();
    _ticker?.dispose();
    _ticker = null;
  }

  @override
  void didUpdateWidget(BreathingDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.animate != oldWidget.animate) {
      if (widget.animate) {
        _startTicker();
      } else {
        _stopTicker();
      }
    }
  }

  @override
  void dispose() {
    _stopTicker();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // 使用全局预热的动画值
    final scale = AnimationTickerService.instance.breathingScale;

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
              blurRadius: 8 * scale,
              spreadRadius: 1,
            ),
          ],
        ),
      ),
    );
  }
}
