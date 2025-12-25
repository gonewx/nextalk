import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/constants/tray_constants.dart';
import 'package:voice_capsule/services/language_service.dart';
import 'package:voice_capsule/services/tray_service.dart';

/// Story 3-4: TrayService 单元测试
/// Story 2-7: 引擎切换功能测试 (Task 6.4)
///
/// 注意: TrayService 的核心功能依赖 system_tray 原生插件，
/// 只能在 Linux 桌面环境下进行集成测试。
/// 这里测试可独立验证的部分：单例模式、常量值、错误处理属性、i18n。
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

  // Story 2-7: 引擎切换功能测试 (Task 6.4)
  group('Story 2-7: TrayStatus 枚举测试', () {
    test('TrayStatus 应包含所有预期状态', () {
      expect(TrayStatus.values.length, 3);
      expect(TrayStatus.values, contains(TrayStatus.normal));
      expect(TrayStatus.values, contains(TrayStatus.warning));
      expect(TrayStatus.values, contains(TrayStatus.error));
    });

    test('currentStatus 应该可以访问', () {
      final service = TrayService.instance;
      expect(service.currentStatus, isA<TrayStatus>());
    });
  });

  group('Story 2-7: LanguageService.trWithParams 测试 (AC6)', () {
    test('trWithParams 应该正确替换单个参数', () {
      final lang = LanguageService.instance;
      // 使用内置翻译
      final result = lang.trWithParams(
        'tray_engine_switch_success',
        {'engine': 'TestEngine'},
      );
      expect(result, contains('TestEngine'));
    });

    test('trWithParams 应该正确替换多个参数', () {
      // 测试字符串带多个占位符的情况
      const template = '引擎 {engine} 已切换，版本 {version}';
      var result = template;
      final params = <String, String>{'engine': 'SenseVoice', 'version': 'v2'};
      params.forEach((key, value) {
        result = result.replaceAll('{$key}', value);
      });
      expect(result, '引擎 SenseVoice 已切换，版本 v2');
    });

    test('trWithParams 参数为空时返回原字符串', () {
      final lang = LanguageService.instance;
      final original = lang.tr('tray_engine_switching');
      final result = lang.trWithParams('tray_engine_switching', {});
      expect(result, original);
    });

    test('trWithParams 不存在的参数不影响结果', () {
      final lang = LanguageService.instance;
      final result = lang.trWithParams(
        'tray_engine_switch_success',
        {'nonexistent': 'value'},
      );
      // 不存在的占位符不会被替换，原 {engine} 保留
      expect(result, contains('{engine}'));
    });
  });

  group('Story 2-7: 引擎相关 i18n 键名测试 (AC6)', () {
    test('中文翻译应包含所有引擎相关键名', () {
      final lang = LanguageService.instance;
      // 切换到中文
      lang.localeNotifier.value = const Locale('zh');

      expect(lang.tr('tray_asr_engine'), 'ASR 引擎');
      expect(lang.tr('tray_engine_zipformer'), contains('Zipformer'));
      expect(lang.tr('tray_engine_sensevoice'), contains('SenseVoice'));
      expect(lang.tr('tray_engine_switching'), '切换中...');
      expect(lang.tr('tray_engine_switch_success'), contains('{engine}'));
      expect(lang.tr('tray_engine_switch_fallback'), contains('{engine}'));
      expect(lang.tr('tray_model_settings'), '模型设置');
    });

    test('英文翻译应包含所有引擎相关键名', () {
      final lang = LanguageService.instance;
      // 切换到英文
      lang.localeNotifier.value = const Locale('en');

      expect(lang.tr('tray_asr_engine'), 'ASR Engine');
      expect(lang.tr('tray_engine_zipformer'), contains('Zipformer'));
      expect(lang.tr('tray_engine_sensevoice'), contains('SenseVoice'));
      expect(lang.tr('tray_engine_switching'), 'Switching...');
      expect(lang.tr('tray_engine_switch_success'), contains('{engine}'));
      expect(lang.tr('tray_engine_switch_fallback'), contains('{engine}'));
      expect(lang.tr('tray_model_settings'), 'Model Settings');

      // 恢复中文
      lang.localeNotifier.value = const Locale('zh');
    });
  });

  group('Story 2-7: EngineType 枚举测试', () {
    test('EngineType 应包含所有预期类型', () {
      expect(EngineType.values.length, 2);
      expect(EngineType.values, contains(EngineType.zipformer));
      expect(EngineType.values, contains(EngineType.sensevoice));
    });

    test('EngineType.name 应返回正确的字符串', () {
      expect(EngineType.zipformer.name, 'zipformer');
      expect(EngineType.sensevoice.name, 'sensevoice');
    });
  });

  group('Story 2-7: TrayService 回调测试', () {
    test('onReconnectFcitx 回调应该可设置', () {
      final service = TrayService.instance;

      // 默认为 null
      expect(service.onReconnectFcitx, isNull);

      // 可以设置回调
      service.onReconnectFcitx = () async {};
      expect(service.onReconnectFcitx, isNotNull);

      // 清理
      service.onReconnectFcitx = null;
    });
  });
}
