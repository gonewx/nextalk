import 'package:flutter/material.dart';

import '../constants/capsule_colors.dart';
import '../state/capsule_state.dart';
import 'breathing_dot.dart';
import 'pulse_indicator.dart';
import 'ripple_effect.dart';

/// 状态指示器组合组件
/// Story 3-3: 状态机与动画系统
/// 根据 CapsuleState 渲染不同的指示器组件:
/// - listening: BreathingDot + RippleEffect
/// - processing: PulseIndicator
/// - error: 静态圆点 (黄色/灰色)
/// - idle: 无显示
class StateIndicator extends StatelessWidget {
  const StateIndicator({
    super.key,
    required this.stateData,
    this.size = 30.0,
  });

  /// 当前状态数据
  final CapsuleStateData stateData;

  /// 指示器尺寸
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        clipBehavior: Clip.none, // 允许波纹溢出容器
        children: [
          // 波纹效果 (仅 listening 状态)
          if (stateData.state == CapsuleState.listening)
            RippleEffect(
              color: CapsuleColors.accentRed,
              size: size,
              animate: true,
            ),

          // 核心指示器
          _buildCoreIndicator(),
        ],
      ),
    );
  }

  Widget _buildCoreIndicator() {
    switch (stateData.state) {
      case CapsuleState.listening:
        return BreathingDot(
          color: CapsuleColors.accentRed,
          size: size,
          animate: true,
        );

      case CapsuleState.processing:
        return PulseIndicator(
          color: CapsuleColors.accentRed,
          size: size,
        );

      case CapsuleState.error:
        return _buildErrorIndicator();

      case CapsuleState.idle:
        return const SizedBox.shrink();

      // Story 3-7: 新增初始化状态显示
      case CapsuleState.initializing:
      case CapsuleState.downloading:
      case CapsuleState.extracting:
        // 初始化过程中显示脉冲指示器
        return PulseIndicator(
          color: CapsuleColors.warning,
          size: size,
        );
    }
  }

  Widget _buildErrorIndicator() {
    final color = _getErrorColor();
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
      ),
    );
  }

  Color _getErrorColor() {
    switch (stateData.errorType) {
      // 灰色 - 无设备
      case CapsuleErrorType.audioNoDevice:
        return CapsuleColors.disabled;
      // 黄色 - 警告 (所有其他错误)
      case CapsuleErrorType.audioDeviceBusy:
      case CapsuleErrorType.audioPermissionDenied:
      case CapsuleErrorType.audioDeviceLost:
      case CapsuleErrorType.audioInitFailed:
      case CapsuleErrorType.modelNotFound:
      case CapsuleErrorType.modelIncomplete:
      case CapsuleErrorType.modelCorrupted:
      case CapsuleErrorType.modelLoadFailed:
      case CapsuleErrorType.socketError:
      case CapsuleErrorType.unknown:
      case null:
        return CapsuleColors.warning;
    }
  }
}




