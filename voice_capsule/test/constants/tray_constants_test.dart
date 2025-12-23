import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/tray_constants.dart';

/// Story 3-4: TrayConstants 单元测试
void main() {
  group('TrayConstants Tests', () {
    test('appName should be Nextalk', () {
      expect(TrayConstants.appName, 'Nextalk');
    });

    test('iconPath should point to assets', () {
      expect(TrayConstants.iconPath, contains('assets'));
      expect(TrayConstants.iconPath, endsWith('.png'));
      expect(TrayConstants.iconPath, 'assets/icons/tray_icon.png');
    });

    test('menu labels should be in Chinese', () {
      expect(TrayConstants.menuTitle, 'Nextalk');
      expect(TrayConstants.menuShowHide, '显示 / 隐藏');
      expect(TrayConstants.menuSettings, '设置...');
      expect(TrayConstants.menuExit, '退出');
    });

    test('menu labels should not be empty', () {
      expect(TrayConstants.menuTitle.isNotEmpty, true);
      expect(TrayConstants.menuShowHide.isNotEmpty, true);
      expect(TrayConstants.menuSettings.isNotEmpty, true);
      expect(TrayConstants.menuExit.isNotEmpty, true);
    });
  });
}

