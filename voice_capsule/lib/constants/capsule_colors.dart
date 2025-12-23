import 'package:flutter/material.dart';

/// 胶囊 UI 颜色常量
/// Story 3-2: 胶囊 UI 组件
class CapsuleColors {
  CapsuleColors._();

  /// 胶囊主背景 - 深灰微透 [Source: docs/front-end-spec.md#2.1]
  static const Color background = Color.fromRGBO(25, 25, 25, 0.95);

  /// Story 3-7: 深色背景 (用于对话框)
  static const Color backgroundDark = Color(0xFF1A1A1A);

  /// 核心状态色 - 录音中/呼吸灯 [用于 Story 3-3]
  static const Color accentRed = Color(0xFFFF4757);

  /// Story 3-7: 录音红 (与 accentRed 相同，兼容别名)
  static const Color recordingRed = accentRed;

  /// 主文字颜色
  static const Color textWhite = Color(0xFFFFFFFF);

  /// 提示文字/光标颜色
  static const Color textHint = Color(0xFFA4B0BE);

  /// 内发光描边
  static const Color borderGlow = Color.fromRGBO(255, 255, 255, 0.2);

  /// 外部阴影
  static const Color shadow = Color.fromRGBO(0, 0, 0, 0.3);

  /// 处理中文字 - 降低透明度 [Story 3-3 状态机使用]
  static const Color textProcessing = Color.fromRGBO(255, 255, 255, 0.8);

  /// 警告色 - 错误状态 [Story 3-3 状态机使用]
  static const Color warning = Color(0xFFFFA502);

  /// 禁用色 - 无设备 [Story 3-3 状态机使用]
  static const Color disabled = Color(0xFF636E72);
}

/// 胶囊 UI 文本样式
class CapsuleTextStyles {
  CapsuleTextStyles._();

  /// 主文字样式 - 18px Medium [Source: docs/front-end-spec.md#2.2]
  static const TextStyle primaryText = TextStyle(
    color: CapsuleColors.textWhite,
    fontSize: 18.0,
    fontWeight: FontWeight.w500,
    height: 1.0,
  );

  /// 提示文字样式
  static const TextStyle hintText = TextStyle(
    color: CapsuleColors.textHint,
    fontSize: 18.0,
    fontWeight: FontWeight.w500,
    height: 1.0,
  );

  /// 处理中文字样式
  static const TextStyle processingText = TextStyle(
    color: CapsuleColors.textProcessing,
    fontSize: 18.0,
    fontWeight: FontWeight.w500,
    height: 1.0,
  );
}





