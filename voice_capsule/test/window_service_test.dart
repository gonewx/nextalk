import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:voice_capsule/constants/window_constants.dart';

/// Story 3-1: WindowService 单元测试
///
/// 注意: WindowService 的核心功能依赖 window_manager 原生插件，
/// 只能在 Linux 环境下进行集成测试。
/// 这里测试可独立验证的部分：常量值和持久化逻辑。
void main() {
  group('WindowConstants', () {
    test('should have correct window dimensions', () {
      expect(WindowConstants.windowWidth, 400.0);
      expect(WindowConstants.windowHeight, 120.0);
    });

    test('should have correct capsule dimensions', () {
      expect(WindowConstants.capsuleWidth, 380.0);
      expect(WindowConstants.capsuleMinWidth, 280.0);
      expect(WindowConstants.capsuleHeight, 60.0);
    });

    test('should have correct capsule radius', () {
      expect(WindowConstants.capsuleRadius, 40.0);
    });

    test('should have correct SharedPreferences keys with prefix', () {
      // 确保键名使用 nextalk_ 前缀避免冲突
      expect(WindowConstants.positionXKey, startsWith('nextalk_'));
      expect(WindowConstants.positionYKey, startsWith('nextalk_'));
      expect(WindowConstants.positionXKey, 'nextalk_window_x');
      expect(WindowConstants.positionYKey, 'nextalk_window_y');
    });
  });

  group('WindowPosition Persistence Logic', () {
    setUp(() {
      // 设置 SharedPreferences mock
      SharedPreferences.setMockInitialValues({});
    });

    test('should save and restore position via SharedPreferences', () async {
      final prefs = await SharedPreferences.getInstance();

      // 模拟保存位置
      const testX = 100.0;
      const testY = 200.0;
      await prefs.setDouble(WindowConstants.positionXKey, testX);
      await prefs.setDouble(WindowConstants.positionYKey, testY);

      // 验证恢复
      final restoredX = prefs.getDouble(WindowConstants.positionXKey);
      final restoredY = prefs.getDouble(WindowConstants.positionYKey);

      expect(restoredX, testX);
      expect(restoredY, testY);
    });

    test('should handle missing position gracefully', () async {
      final prefs = await SharedPreferences.getInstance();

      // 不保存任何位置
      final x = prefs.getDouble(WindowConstants.positionXKey);
      final y = prefs.getDouble(WindowConstants.positionYKey);

      // 应返回 null
      expect(x, isNull);
      expect(y, isNull);
    });

    test('should validate position bounds using WindowConstants', () async {
      // 使用 WindowConstants.isValidPosition 方法进行测试
      // 有效范围: x in [positionMinX, positionMaxX), y in [positionMinY, positionMaxY)

      // 有效位置
      expect(WindowConstants.isValidPosition(0, 0), true);
      expect(WindowConstants.isValidPosition(100, 200), true);
      expect(
          WindowConstants.isValidPosition(WindowConstants.positionMinX + 1,
              WindowConstants.positionMinY + 1),
          true);
      expect(
          WindowConstants.isValidPosition(WindowConstants.positionMaxX - 1,
              WindowConstants.positionMaxY - 1),
          true);

      // 无效位置 (屏幕外)
      expect(
          WindowConstants.isValidPosition(WindowConstants.positionMinX - 1, 0),
          false);
      expect(WindowConstants.isValidPosition(WindowConstants.positionMaxX, 0),
          false);
      expect(
          WindowConstants.isValidPosition(0, WindowConstants.positionMinY - 1),
          false);
      expect(WindowConstants.isValidPosition(0, WindowConstants.positionMaxY),
          false);
      expect(WindowConstants.isValidPosition(-1000, 0), false);
      expect(WindowConstants.isValidPosition(0, 5000), false);
    });
  });
}
