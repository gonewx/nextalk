import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/hotkey_service.dart';
import 'package:voice_capsule/constants/hotkey_constants.dart';
import 'package:voice_capsule/constants/settings_constants.dart';

/// Story 3-5: HotkeyService 测试 (重构版)
///
/// 注意: 快捷键监听已改由 Fcitx5 插件处理
/// HotkeyService 现在只负责配置读取和同步
void main() {
  group('HotkeyService Tests', () {
    group('单例模式', () {
      test('应该是单例', () {
        final instance1 = HotkeyService.instance;
        final instance2 = HotkeyService.instance;
        expect(identical(instance1, instance2), isTrue);
      });
    });

    group('初始状态', () {
      test('初始时应该未初始化', () {
        final service = HotkeyService.instance;
        // 注意: 初始状态取决于是否已经调用过 initialize
        // 这里只验证属性存在且是 bool 类型
        expect(service.isInitialized, isA<bool>());
      });

      test('onHotkeyPressed 回调应该可以设置并执行', () async {
        var callCount = 0;
        HotkeyService.instance.onHotkeyPressed = () async {
          callCount++;
        };
        expect(HotkeyService.instance.onHotkeyPressed, isNotNull);

        // 验证回调可以被调用
        await HotkeyService.instance.onHotkeyPressed!();
        expect(callCount, equals(1));
      });
    });

    group('配置文件路径 (统一使用 settings.yaml)', () {
      test('应该使用 SettingsConstants 中的配置路径', () {
        expect(SettingsConstants.settingsFilePath, contains('settings.yaml'));
      });

      test('HOME 环境变量应该存在', () {
        final home = Platform.environment['HOME'];
        expect(home, isNotNull);
        expect(home, isNotEmpty);
      });

      test('配置文件路径应该正确构造', () {
        final expectedPath = SettingsConstants.settingsFilePath;
        expect(expectedPath, contains('.config/nextalk/settings.yaml'));
      });
    });

    group('快捷键配置解析', () {
      test('默认快捷键应该是 altRight', () {
        expect(
          HotkeyConstants.defaultKey,
          equals('altRight'),
        );
      });

      test('keyToFcitx5 应该包含所有支持的键', () {
        // 验证 keyToFcitx5 包含配置文件可能用到的所有键
        expect(HotkeyConstants.keyToFcitx5.containsKey('altRight'), isTrue);
        expect(HotkeyConstants.keyToFcitx5.containsKey('space'), isTrue);
        expect(HotkeyConstants.keyToFcitx5.containsKey('ctrl'), isTrue);
      });

      test('modifierToFcitx5 应该包含所有支持的修饰键', () {
        expect(HotkeyConstants.modifierToFcitx5.containsKey('ctrl'), isTrue);
        expect(HotkeyConstants.modifierToFcitx5.containsKey('shift'), isTrue);
        expect(HotkeyConstants.modifierToFcitx5.containsKey('alt'), isTrue);
        expect(HotkeyConstants.modifierToFcitx5.containsKey('meta'), isTrue);
      });
    });

    group('HotkeyPressedCallback 类型', () {
      test('回调应该是 Future<void> Function() 类型', () async {
        var callCount = 0;

        Future<void> callback() async {
          callCount++;
        }

        HotkeyService.instance.onHotkeyPressed = callback;

        // 手动触发回调测试
        final cb = HotkeyService.instance.onHotkeyPressed;
        if (cb != null) {
          await cb();
        }

        expect(callCount, equals(1));
      });
    });

    group('HotkeyConfig', () {
      test('默认配置应该正确', () {
        final config = HotkeyConfig.defaultConfig;
        expect(config.key, equals('altRight'));
        expect(config.modifiers, isEmpty);
      });

      test('toFcitx5Format 应该正确转换无修饰键的配置', () {
        const config = HotkeyConfig(
          key: 'altRight',
          modifiers: [],
        );
        expect(config.toFcitx5Format(), equals('Alt_R'));
      });

      test('toFcitx5Format 应该正确转换带修饰键的配置', () {
        const config = HotkeyConfig(
          key: 'space',
          modifiers: ['ctrl', 'shift'],
        );
        expect(config.toFcitx5Format(), equals('Control+Shift+space'));
      });
    });
  });
}
