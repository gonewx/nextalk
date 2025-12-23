import 'package:flutter/animation.dart';

/// 动画参数常量
/// Story 3-3: 状态机与动画系统
/// [Source: docs/front-end-spec.md#5]
class AnimationConstants {
  AnimationConstants._();

  // ===== 波纹动画 (Ripple) =====
  /// 单次波纹周期
  static const Duration rippleDuration = Duration(milliseconds: 1500);

  /// 爆发感曲线
  static const Curve rippleCurve = Curves.easeOutQuad;

  /// 波纹起始尺寸
  static const double rippleStartScale = 1.0;

  /// 波纹结束尺寸 (扩散到 3 倍)
  static const double rippleEndScale = 3.0;

  /// 波纹起始透明度
  static const double rippleStartOpacity = 0.5;

  /// 波纹结束透明度 (完全透明)
  static const double rippleEndOpacity = 0.0;

  // ===== 光标动画 (Cursor) =====
  /// 闪烁周期
  static const Duration cursorDuration = Duration(milliseconds: 800);

  /// 平滑过渡曲线
  static const Curve cursorCurve = Curves.easeInOut;

  // ===== 呼吸动画 (Breathing) =====
  /// 呼吸公式基础值: 1.0 + amplitude * sin(t)
  static const double breathingBaseScale = 1.0;

  /// 呼吸动画振幅
  static const double breathingAmplitude = 0.1;

  /// 呼吸周期 (完整 sin 波)
  static const Duration breathingPeriod = Duration(milliseconds: 2000);

  // ===== 脉冲动画 (Pulse - Processing) =====
  /// 快速脉冲周期
  static const Duration pulseDuration = Duration(milliseconds: 400);

  /// 脉冲最大缩放值
  static const double pulseMaxScale = 1.2;
}





