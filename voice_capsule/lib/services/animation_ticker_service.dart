import 'dart:math' as math;

import 'package:flutter/scheduler.dart';

import '../constants/animation_constants.dart';

/// 全局动画 Ticker 服务
/// 在应用启动时预热，确保呼吸灯动画无延迟显示
///
/// 使用单例模式，所有动画组件共享同一个 ticker，
/// 即使窗口隐藏，ticker 也持续运行。
class AnimationTickerService {
  AnimationTickerService._();
  static final AnimationTickerService instance = AnimationTickerService._();

  Ticker? _ticker;
  Duration _elapsed = Duration.zero;
  bool _isRunning = false;

  /// 呼吸动画周期 (毫秒)
  int get _breathingPeriodMs => AnimationConstants.breathingPeriod.inMilliseconds;

  /// 波纹动画周期 (毫秒)
  int get _ripplePeriodMs => AnimationConstants.rippleDuration.inMilliseconds;

  /// 是否正在运行
  bool get isRunning => _isRunning;

  /// 获取呼吸动画当前值 [0.0, 1.0]
  double get breathingValue {
    if (!_isRunning) return 0.0;
    final ms = _elapsed.inMilliseconds % _breathingPeriodMs;
    return ms / _breathingPeriodMs;
  }

  /// 获取呼吸缩放值 (已计算好的 scale)
  double get breathingScale {
    final normalizedSin = (1 + math.sin(breathingValue * 2 * math.pi)) / 2;
    return AnimationConstants.breathingBaseScale +
        AnimationConstants.breathingAmplitude * normalizedSin;
  }

  /// 获取波纹动画当前值 [0.0, 1.0]，支持多层波纹偏移
  double rippleValue(int index, int totalCount) {
    if (!_isRunning) return 0.0;
    final offset = index / totalCount;
    final ms = _elapsed.inMilliseconds % _ripplePeriodMs;
    final baseValue = ms / _ripplePeriodMs;
    return (baseValue + offset) % 1.0;
  }

  /// 启动 ticker (在 main.dart 中调用)
  void start() {
    if (_isRunning) return;

    _ticker = Ticker(_onTick);
    _ticker!.start();
    _isRunning = true;
  }

  void _onTick(Duration elapsed) {
    _elapsed = elapsed;
  }

  /// 停止 ticker (应用退出时调用)
  void stop() {
    _ticker?.stop();
    _ticker?.dispose();
    _ticker = null;
    _isRunning = false;
    _elapsed = Duration.zero;
  }
}
