import 'package:flutter/material.dart';

import '../constants/animation_constants.dart';
import '../constants/capsule_colors.dart';

/// 波纹扩散效果
/// Story 3-3: 状态机与动画系统
/// 从中心向外扩散的圆形波纹，Scale 1.0->3.0，Opacity 0.5->0.0
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
    with TickerProviderStateMixin {
  late List<AnimationController> _controllers;
  late List<Animation<double>> _scaleAnimations;
  late List<Animation<double>> _opacityAnimations;

  @override
  void initState() {
    super.initState();
    _initAnimations();
  }

  void _initAnimations() {
    _controllers = List.generate(widget.rippleCount, (index) {
      final controller = AnimationController(
        duration: AnimationConstants.rippleDuration,
        vsync: this,
      );

      return controller;
    });

    // 初始化动画 tweens
    _initTweens();

    // 错开每个波纹的起始时间并启动动画
    if (widget.animate) {
      _startStaggeredAnimations();
    }
  }

  void _startStaggeredAnimations() {
    for (int index = 0; index < _controllers.length; index++) {
      final controller = _controllers[index];
      // 设置初始偏移位置以错开波纹
      final offset = index / widget.rippleCount;
      controller.value = offset;
      controller.repeat();
    }
  }

  void _stopAnimations() {
    for (final controller in _controllers) {
      controller.stop();
      controller.reset();
    }
  }

  void _initTweens() {
    _scaleAnimations = _controllers.map((controller) {
      return Tween<double>(
        begin: AnimationConstants.rippleStartScale,
        end: AnimationConstants.rippleEndScale,
      ).animate(CurvedAnimation(
        parent: controller,
        curve: AnimationConstants.rippleCurve,
      ));
    }).toList();

    _opacityAnimations = _controllers.map((controller) {
      return Tween<double>(
        begin: AnimationConstants.rippleStartOpacity,
        end: AnimationConstants.rippleEndOpacity,
      ).animate(CurvedAnimation(
        parent: controller,
        curve: AnimationConstants.rippleCurve,
      ));
    }).toList();
  }

  @override
  void didUpdateWidget(RippleEffect oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.animate != oldWidget.animate) {
      if (widget.animate) {
        _startStaggeredAnimations();
      } else {
        _stopAnimations();
      }
    }
  }

  @override
  void dispose() {
    for (final controller in _controllers) {
      controller.dispose();
    }
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
          clipBehavior: Clip.none, // 允许波纹溢出容器
          children: List.generate(widget.rippleCount, (index) {
            return AnimatedBuilder(
              animation: _controllers[index],
              builder: (context, child) {
                return Transform.scale(
                  scale: _scaleAnimations[index].value,
                  child: Container(
                    width: widget.size,
                    height: widget.size,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      // 使用填充色代替边框，与参考项目一致
                      color: widget.color.withValues(
                        alpha: _opacityAnimations[index].value,
                      ),
                    ),
                  ),
                );
              },
            );
          }),
        ),
      ),
    );
  }
}



