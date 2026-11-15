import 'dart:math' as math;
import 'dart:ui';

/// 工作区与 Flutter 窗口均使用逻辑像素，不重复乘除缩放系数。
class SettingsWindowGeometry {
  static const widthKey = 'settings.window.width';
  static const heightKey = 'settings.window.height';
  static const fallbackWorkArea = Size(1024, 768);

  static bool valid(Size size) =>
      size.width.isFinite &&
      size.height.isFinite &&
      size.width > 0 &&
      size.height > 0;

  /// 为系统标题栏和屏幕边缘留余量；小工作区的最小尺寸也同步缩小。
  static Size available(Size workArea) {
    final area = valid(workArea) ? workArea : fallbackWorkArea;
    return Size(math.max(1, area.width - 32), math.max(1, area.height - 64));
  }

  static Size minimum(Size workArea) {
    final limit = available(workArea);
    return Size(math.min(420, limit.width), math.min(360, limit.height));
  }

  static Size initial(Size workArea, {Size? preferred}) {
    final limit = available(workArea);
    final min = minimum(workArea);
    final desired = preferred != null && valid(preferred)
        ? preferred
        : Size(
            (limit.width * .75).clamp(640, 960),
            (limit.height * .9).clamp(560, 820),
          );
    return Size(desired.width.clamp(min.width, limit.width),
        desired.height.clamp(min.height, limit.height));
  }
}
