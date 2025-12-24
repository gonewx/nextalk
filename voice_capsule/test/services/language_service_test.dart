import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:voice_capsule/services/language_service.dart';

/// Story 3-8: LanguageService 单元测试
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('LanguageService', () {
    setUp(() async {
      // 重置 SharedPreferences
      SharedPreferences.setMockInitialValues({});
    });

    group('tr() 翻译方法', () {
      test('返回中文托盘菜单文本', () {
        // 设置为中文
        LanguageService.instance.localeNotifier.value = const Locale('zh');

        expect(
          LanguageService.instance.tr('tray_show_hide'),
          equals('显示 / 隐藏'),
        );
        expect(
          LanguageService.instance.tr('tray_exit'),
          equals('退出'),
        );
        expect(
          LanguageService.instance.tr('tray_model_int8'),
          equals('int8 模型 (更快)'),
        );
      });

      test('返回英文托盘菜单文本', () {
        // 设置为英文
        LanguageService.instance.localeNotifier.value = const Locale('en');

        expect(
          LanguageService.instance.tr('tray_show_hide'),
          equals('Show / Hide'),
        );
        expect(
          LanguageService.instance.tr('tray_exit'),
          equals('Exit'),
        );
        expect(
          LanguageService.instance.tr('tray_model_int8'),
          equals('int8 Model (Faster)'),
        );
      });

      test('返回中文错误消息', () {
        LanguageService.instance.localeNotifier.value = const Locale('zh');

        expect(
          LanguageService.instance.tr('error_mic_no_device'),
          equals('未检测到麦克风'),
        );
        expect(
          LanguageService.instance.tr('error_fcitx_not_running'),
          equals('Fcitx5 未运行，请先启动输入法'),
        );
      });

      test('返回英文错误消息', () {
        LanguageService.instance.localeNotifier.value = const Locale('en');

        expect(
          LanguageService.instance.tr('error_mic_no_device'),
          equals('Microphone Not Detected'),
        );
        expect(
          LanguageService.instance.tr('error_fcitx_not_running'),
          equals('Fcitx5 Not Running, Please Start Input Method'),
        );
      });

      test('未知 key 返回原始 key', () {
        expect(
          LanguageService.instance.tr('unknown_key'),
          equals('unknown_key'),
        );
      });
    });

    group('语言切换', () {
      test('switchLanguage 更新 localeNotifier', () async {
        SharedPreferences.setMockInitialValues({});

        LanguageService.instance.localeNotifier.value = const Locale('zh');
        expect(LanguageService.instance.languageCode, equals('zh'));

        await LanguageService.instance.switchLanguage('en');
        expect(LanguageService.instance.languageCode, equals('en'));
        expect(LanguageService.instance.isZh, isFalse);

        await LanguageService.instance.switchLanguage('zh');
        expect(LanguageService.instance.languageCode, equals('zh'));
        expect(LanguageService.instance.isZh, isTrue);
      });

      test('忽略无效的语言代码', () async {
        SharedPreferences.setMockInitialValues({});

        LanguageService.instance.localeNotifier.value = const Locale('zh');
        await LanguageService.instance.switchLanguage('fr'); // 不支持的语言

        // 应该保持原来的语言
        expect(LanguageService.instance.languageCode, equals('zh'));
      });

      test('相同语言不触发更新', () async {
        SharedPreferences.setMockInitialValues({});

        LanguageService.instance.localeNotifier.value = const Locale('zh');
        int notifyCount = 0;
        LanguageService.instance.localeNotifier.addListener(() {
          notifyCount++;
        });

        await LanguageService.instance.switchLanguage('zh'); // 同样的语言

        expect(notifyCount, equals(0));
      });
    });

    group('isZh getter', () {
      test('中文返回 true', () {
        LanguageService.instance.localeNotifier.value = const Locale('zh');
        expect(LanguageService.instance.isZh, isTrue);
      });

      test('英文返回 false', () {
        LanguageService.instance.localeNotifier.value = const Locale('en');
        expect(LanguageService.instance.isZh, isFalse);
      });
    });
  });
}
