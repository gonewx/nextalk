import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/hotkey_constants.dart';

/// Story 3-5: 快捷键常量测试 (重构版)
void main() {
  group('HotkeyConstants Tests', () {
    group('默认快捷键配置', () {
      test('defaultKey 应该是 v (Ctrl+Alt+V)', () {
        expect(
          HotkeyConstants.defaultKey,
          equals('v'),
        );
      });

      test('defaultModifiers 应该是 ctrl 和 alt', () {
        expect(HotkeyConstants.defaultModifiers, equals(['ctrl', 'alt']));
      });
    });

    group('keyToFcitx5 映射', () {
      test('应该包含 altRight', () {
        expect(HotkeyConstants.keyToFcitx5.containsKey('altRight'), isTrue);
        expect(
          HotkeyConstants.keyToFcitx5['altRight'],
          equals('Alt_R'),
        );
      });

      test('应该包含 space', () {
        expect(HotkeyConstants.keyToFcitx5.containsKey('space'), isTrue);
        expect(
          HotkeyConstants.keyToFcitx5['space'],
          equals('space'),
        );
      });

      test('应该包含 ctrl 系列', () {
        expect(HotkeyConstants.keyToFcitx5.containsKey('ctrl'), isTrue);
        expect(HotkeyConstants.keyToFcitx5.containsKey('ctrlLeft'), isTrue);
        expect(HotkeyConstants.keyToFcitx5.containsKey('ctrlRight'), isTrue);
      });

      test('应该包含所有 F1-F12 功能键', () {
        for (int i = 1; i <= 12; i++) {
          expect(
            HotkeyConstants.keyToFcitx5.containsKey('f$i'),
            isTrue,
            reason: 'keyToFcitx5 应该包含 f$i',
          );
          expect(
            HotkeyConstants.keyToFcitx5['f$i'],
            equals('F$i'),
            reason: 'f$i 应该映射到 F$i',
          );
        }
      });

      test('应该正确映射修饰键作为主键', () {
        expect(HotkeyConstants.keyToFcitx5['alt'], equals('Alt_L'));
        expect(HotkeyConstants.keyToFcitx5['altLeft'], equals('Alt_L'));
        expect(HotkeyConstants.keyToFcitx5['altRight'], equals('Alt_R'));
        expect(HotkeyConstants.keyToFcitx5['ctrl'], equals('Control_L'));
        expect(HotkeyConstants.keyToFcitx5['shift'], equals('Shift_L'));
        expect(HotkeyConstants.keyToFcitx5['meta'], equals('Super_L'));
      });
    });

    group('modifierToFcitx5 映射', () {
      test('应该包含 ctrl', () {
        expect(HotkeyConstants.modifierToFcitx5.containsKey('ctrl'), isTrue);
        expect(
          HotkeyConstants.modifierToFcitx5['ctrl'],
          equals('Control'),
        );
      });

      test('应该包含 shift', () {
        expect(HotkeyConstants.modifierToFcitx5.containsKey('shift'), isTrue);
        expect(
          HotkeyConstants.modifierToFcitx5['shift'],
          equals('Shift'),
        );
      });

      test('应该包含 alt', () {
        expect(HotkeyConstants.modifierToFcitx5.containsKey('alt'), isTrue);
        expect(
          HotkeyConstants.modifierToFcitx5['alt'],
          equals('Alt'),
        );
      });

      test('应该包含 meta', () {
        expect(HotkeyConstants.modifierToFcitx5.containsKey('meta'), isTrue);
        expect(
          HotkeyConstants.modifierToFcitx5['meta'],
          equals('Super'),
        );
      });

      test('control 和 ctrl 应该映射到同一个 Fcitx5 修饰键', () {
        expect(
          HotkeyConstants.modifierToFcitx5['ctrl'],
          equals(HotkeyConstants.modifierToFcitx5['control']),
        );
      });
    });

    group('Fcitx5 格式字符串', () {
      test('单键应该直接映射', () {
        expect(HotkeyConstants.keyToFcitx5['escape'], equals('Escape'));
        expect(HotkeyConstants.keyToFcitx5['tab'], equals('Tab'));
        expect(HotkeyConstants.keyToFcitx5['enter'], equals('Return'));
      });

      test('方向键应该正确映射', () {
        expect(HotkeyConstants.keyToFcitx5['arrowUp'], equals('Up'));
        expect(HotkeyConstants.keyToFcitx5['arrowDown'], equals('Down'));
        expect(HotkeyConstants.keyToFcitx5['arrowLeft'], equals('Left'));
        expect(HotkeyConstants.keyToFcitx5['arrowRight'], equals('Right'));
      });

      test('小键盘数字键应该正确映射', () {
        for (int i = 0; i <= 9; i++) {
          expect(
            HotkeyConstants.keyToFcitx5['numpad$i'],
            equals('KP_$i'),
            reason: 'numpad$i 应该映射到 KP_$i',
          );
        }
      });
    });
  });
}
