import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../constants/animation_constants.dart';
import '../constants/capsule_colors.dart';
import '../services/animation_ticker_service.dart';

/// 波纹扩散效果
/// Story 3-3: 状态机与动画系统
/// 使用全局 AnimationTickerService 实现预热，确保无延迟显示
class RippleEffect extends StatefulWidget {
  const RippleEffect({
    super.key,
    this.color = CapsuleColors.accentRed,
    this.size = 30.0,
    this.rippleCount = 2,
    this.animate = true,
  });

  /// 波纹颜色
  final Color color;

  /// 波纹基础尺寸 (直径)
  final double size;

  /// 波纹数量 (同时显示的波纹层数)
  final int rippleCount;

  /// 是否启用动画
  final bool animate;

  @override
  State<RippleEffect> createState() => _RippleEffectState();
}

class _RippleEffectState extends State<RippleEffect>
    with SingleTickerProviderStateMixin {
  Ticker? _ticker;
  bool _tickerCreated = false;

  @override
  void initState() {
    super.initState();
    if (widget.animate) {
      _startTicker();
    }
  }

  void _startTicker() {
    if (_tickerCreated) {
      // Ticker 已创建，只需重新启动
      _ticker?.start();
      return;
    }
    _ticker = createTicker((_) {
      if (mounted) setState(() {});
    });
    _tickerCreated = true;
    _ticker!.start();
  }

  void _stopTicker() {
    _ticker?.stop();
    // 不 dispose ticker，保留以便重用
  }

  @override
  void didUpdateWidget(RippleEffect oldWidget) {
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
    _ticker?.stop();
    _ticker?.dispose();
    _ticker = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: SizedBox(
        width: widget.size,
        height: widget.size,
        child: Stack(
          alignment: Alignment.center,
          clipBehavior: Clip.none,
          children: List.generate(widget.rippleCount, (index) {
            // 使用全局预热的动画值
            final value = AnimationTickerService.instance.rippleValue(
              index,
              widget.rippleCount,
            );

            // 计算 scale 和 opacity
            final scale = AnimationConstants.rippleStartScale +
                (AnimationConstants.rippleEndScale -
                        AnimationConstants.rippleStartScale) *
                    value;
            final opacity = AnimationConstants.rippleStartOpacity +
                (AnimationConstants.rippleEndOpacity -
                        AnimationConstants.rippleStartOpacity) *
                    value;

            return Transform.scale(
              scale: scale,
              child: Container(
                width: widget.size,
                height: widget.size,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: widget.color.withValues(alpha: opacity),
                ),
              ),
            );
          }),
        ),
      ),
    );
  }
}
