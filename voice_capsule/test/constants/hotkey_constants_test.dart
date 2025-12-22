import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hotkey_manager/hotkey_manager.dart';
import 'package:voice_capsule/constants/hotkey_constants.dart';

/// Story 3-5: 快捷键常量测试
void main() {
  group('HotkeyConstants Tests', () {
    group('默认快捷键配置', () {
      test('defaultKey 应该是 altRight', () {
        expect(
          HotkeyConstants.defaultKey,
          equals(PhysicalKeyboardKey.altRight),
        );
      });

      test('defaultModifiers 应该为空列表', () {
        expect(HotkeyConstants.defaultModifiers, isEmpty);
      });
    });

    group('备用快捷键配置', () {
      test('fallbackKey 应该是 space', () {
        expect(
          HotkeyConstants.fallbackKey,
          equals(PhysicalKeyboardKey.space),
        );
      });

      test('fallbackModifiers 应该包含 ctrl 和 shift', () {
        expect(HotkeyConstants.fallbackModifiers, hasLength(2));
        expect(
          HotkeyConstants.fallbackModifiers,
          contains(HotKeyModifier.control),
        );
        expect(
          HotkeyConstants.fallbackModifiers,
          contains(HotKeyModifier.shift),
        );
      });
    });

    group('配置文件常量', () {
      test('configDirName 应该是 nextalk', () {
        expect(HotkeyConstants.configDirName, equals('nextalk'));
      });

      test('configFileName 应该是 config.yaml', () {
        expect(HotkeyConstants.configFileName, equals('config.yaml'));
      });
    });

    group('键位映射 keyMap', () {
      test('应该包含 altRight', () {
        expect(HotkeyConstants.keyMap.containsKey('altRight'), isTrue);
        expect(
          HotkeyConstants.keyMap['altRight'],
          equals(PhysicalKeyboardKey.altRight),
        );
      });

      test('应该包含 space', () {
        expect(HotkeyConstants.keyMap.containsKey('space'), isTrue);
        expect(
          HotkeyConstants.keyMap['space'],
          equals(PhysicalKeyboardKey.space),
        );
      });

      test('应该包含 ctrl 系列', () {
        expect(HotkeyConstants.keyMap.containsKey('ctrl'), isTrue);
        expect(HotkeyConstants.keyMap.containsKey('ctrlLeft'), isTrue);
        expect(HotkeyConstants.keyMap.containsKey('ctrlRight'), isTrue);
      });

      test('应该包含所有 F1-F12 功能键', () {
        for (int i = 1; i <= 12; i++) {
          expect(
            HotkeyConstants.keyMap.containsKey('f$i'),
            isTrue,
            reason: 'keyMap 应该包含 f$i',
          );
        }
      });
    });

    group('修饰键映射 modifierMap', () {
      test('应该包含 ctrl', () {
        expect(HotkeyConstants.modifierMap.containsKey('ctrl'), isTrue);
        expect(
          HotkeyConstants.modifierMap['ctrl'],
          equals(HotKeyModifier.control),
        );
      });

      test('应该包含 shift', () {
        expect(HotkeyConstants.modifierMap.containsKey('shift'), isTrue);
        expect(
          HotkeyConstants.modifierMap['shift'],
          equals(HotKeyModifier.shift),
        );
      });

      test('应该包含 alt', () {
        expect(HotkeyConstants.modifierMap.containsKey('alt'), isTrue);
        expect(
          HotkeyConstants.modifierMap['alt'],
          equals(HotKeyModifier.alt),
        );
      });

      test('应该包含 meta', () {
        expect(HotkeyConstants.modifierMap.containsKey('meta'), isTrue);
        expect(
          HotkeyConstants.modifierMap['meta'],
          equals(HotKeyModifier.meta),
        );
      });

      test('control 和 ctrl 应该映射到同一个修饰键', () {
        expect(
          HotkeyConstants.modifierMap['ctrl'],
          equals(HotkeyConstants.modifierMap['control']),
        );
      });
    });

    group('HotKey 集成测试', () {
      test('可以使用默认快捷键创建 HotKey', () {
        final hotkey = HotKey(
          key: HotkeyConstants.defaultKey,
          modifiers: HotkeyConstants.defaultModifiers.isEmpty
              ? null
              : HotkeyConstants.defaultModifiers,
        );

        expect(hotkey.key, equals(HotkeyConstants.defaultKey));
        expect(hotkey.modifiers, isNull);
      });

      test('可以使用备用快捷键创建 HotKey', () {
        final hotkey = HotKey(
          key: HotkeyConstants.fallbackKey,
          modifiers: HotkeyConstants.fallbackModifiers,
        );

        expect(hotkey.key, equals(HotkeyConstants.fallbackKey));
        expect(hotkey.modifiers, isNotNull);
        expect(hotkey.modifiers, hasLength(2));
      });
    });
  });
}
