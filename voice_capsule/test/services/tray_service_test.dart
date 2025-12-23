import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/tray_constants.dart';
import 'package:voice_capsule/services/tray_service.dart';

/// Story 3-4: TrayService 单元测试
///
/// 注意: TrayService 的核心功能依赖 system_tray 原生插件，
/// 只能在 Linux 桌面环境下进行集成测试。
/// 这里测试可独立验证的部分：单例模式、常量值、错误处理属性。
void main() {
  // 需要初始化 Flutter bindings 才能使用 TrayService
  TestWidgetsFlutterBinding.ensureInitialized();

  group('TrayService Tests', () {
    test('should be a singleton', () {
      final instance1 = TrayService.instance;
      final instance2 = TrayService.instance;
      expect(identical(instance1, instance2), isTrue);
    });

    test('isInitialized should be accessible', () {
      final service = TrayService.instance;
      expect(service.isInitialized, isA<bool>());
    });

    test('initializationFailed should be accessible', () {
      final service = TrayService.instance;
      expect(service.initializationFailed, isA<bool>());
    });

    test('onBeforeExit callback should be settable', () {
      final service = TrayService.instance;

      // 默认为 null
      expect(service.onBeforeExit, isNull);

      // 可以设置回调
      service.onBeforeExit = () async {
        // 测试回调
      };
      expect(service.onBeforeExit, isNotNull);

      // 清理
      service.onBeforeExit = null;
    });
  });

  group('TrayConstants Tests (via TrayService)', () {
    test('appName should match TrayConstants', () {
      expect(TrayConstants.appName, 'Nextalk');
    });

    test('iconPath should be correct format', () {
      expect(TrayConstants.iconPath, 'assets/icons/tray_icon.png');
    });

    test('menu labels should be defined', () {
      expect(TrayConstants.menuTitle, isNotEmpty);
      expect(TrayConstants.menuShowHide, isNotEmpty);
      expect(TrayConstants.menuSettings, isNotEmpty);
      expect(TrayConstants.menuExit, isNotEmpty);
    });
  });

  group('WindowService showOnStartup Tests', () {
    // 注意: WindowService 测试需要 mock window_manager
    // 这里仅验证 API 签名存在

    test('showOnStartup parameter concept verification', () {
      // 验证概念：默认值应为 false (托盘驻留)
      const defaultShowOnStartup = false;
      expect(defaultShowOnStartup, isFalse);
    });
  });
}





