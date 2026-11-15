import 'dart:ui';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/settings_window_geometry.dart';

void main() {
  test('小屏和高缩放后的逻辑工作区不会被默认尺寸或最小尺寸撑破', () {
    for (final area in [
      const Size(1280, 720),
      const Size(640, 480),
      const Size(400, 300)
    ]) {
      final size = SettingsWindowGeometry.initial(area);
      final min = SettingsWindowGeometry.minimum(area);
      expect(size.width, lessThanOrEqualTo(area.width - 32));
      expect(size.height, lessThanOrEqualTo(area.height - 64));
      expect(min.width, lessThanOrEqualTo(size.width));
      expect(min.height, lessThanOrEqualTo(size.height));
    }
  });
  test('恢复用户尺寸，屏幕变小则缩回工作区', () {
    expect(
        SettingsWindowGeometry.initial(const Size(1920, 1080),
            preferred: const Size(1100, 900)),
        const Size(1100, 900));
    final smaller = SettingsWindowGeometry.initial(const Size(640, 480),
        preferred: const Size(1100, 900));
    expect(smaller, const Size(608, 416));
  });
  test('脏尺寸和未知工作区安全降级', () {
    final normal =
        SettingsWindowGeometry.initial(SettingsWindowGeometry.fallbackWorkArea);
    expect(
        SettingsWindowGeometry.initial(Size.zero,
            preferred: const Size(double.nan, -1)),
        normal);
  });
}
