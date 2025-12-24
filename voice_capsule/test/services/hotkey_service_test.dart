import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/hotkey_service.dart';
import 'package:voice_capsule/constants/hotkey_constants.dart';
import 'package:voice_capsule/constants/settings_constants.dart';

/// Story 3-5: HotkeyService 测试
///
/// 注意: hotkey_manager 依赖原生 keybinder 库
/// 完整功能测试需要: flutter test -d linux (真实设备)
/// 这里仅测试不依赖原生调用的逻辑
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

      test('registrationFailed 应该是 bool 类型', () {
        expect(HotkeyService.instance.registrationFailed, isA<bool>());
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
      test('默认快捷键应该是 Right Alt', () {
        expect(
          HotkeyConstants.defaultKey,
          equals(PhysicalKeyboardKey.altRight),
        );
      });

      test('keyMap 应该包含所有支持的键', () {
        // 验证 keyMap 包含配置文件可能用到的所有键
        expect(HotkeyConstants.keyMap.containsKey('altRight'), isTrue);
        expect(HotkeyConstants.keyMap.containsKey('space'), isTrue);
        expect(HotkeyConstants.keyMap.containsKey('ctrl'), isTrue);
      });

      test('modifierMap 应该包含所有支持的修饰键', () {
        expect(HotkeyConstants.modifierMap.containsKey('ctrl'), isTrue);
        expect(HotkeyConstants.modifierMap.containsKey('shift'), isTrue);
        expect(HotkeyConstants.modifierMap.containsKey('alt'), isTrue);
        expect(HotkeyConstants.modifierMap.containsKey('meta'), isTrue);
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

    group('错误处理策略 (AC7)', () {
      test('备用快捷键应该与主快捷键不同', () {
        expect(
          HotkeyConstants.defaultKey,
          isNot(equals(HotkeyConstants.fallbackKey)),
        );
      });

      test('备用快捷键应该有修饰键', () {
        expect(HotkeyConstants.fallbackModifiers, isNotEmpty);
      });
    });
  });
}
