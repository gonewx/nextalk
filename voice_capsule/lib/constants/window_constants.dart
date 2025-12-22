/// 窗口尺寸和位置常量
/// Story 3-1: 透明胶囊窗口基础
class WindowConstants {
  // 禁止实例化
  WindowConstants._();

  /// 窗口总尺寸 (包含阴影区域的画布) - AC3
  static const double windowWidth = 400.0;
  static const double windowHeight = 120.0;

  /// 胶囊内容区尺寸 (Story 3-2 使用)
  static const double capsuleWidth = 380.0; // Max
  static const double capsuleMinWidth = 280.0; // Min
  static const double capsuleHeight = 60.0;

  /// 圆角半径 (Story 3-2 使用)
  static const double capsuleRadius = 40.0;

  /// SharedPreferences 键名 (使用 nextalk_ 前缀避免与其他 Flutter 应用冲突)
  static const String positionXKey = 'nextalk_window_x';
  static const String positionYKey = 'nextalk_window_y';

  /// 位置边界校验常量 (支持多显示器配置)
  /// 允许窗口位置在合理范围内，防止窗口出现在屏幕外
  static const double positionMinX = -200.0;
  static const double positionMaxX = 4000.0;
  static const double positionMinY = -50.0;
  static const double positionMaxY = 2500.0;

  /// 验证位置是否在有效屏幕范围内
  static bool isValidPosition(double x, double y) {
    return x >= positionMinX &&
        x < positionMaxX &&
        y >= positionMinY &&
        y < positionMaxY;
  }
}
