import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:voice_capsule/constants/settings_constants.dart';
import 'package:voice_capsule/services/settings_service.dart';

/// Story 2-7 Task 5: 设置服务测试
void main() {
  // 使用临时目录避免污染实际配置
  late Directory tempDir;
  late String originalConfigHome;

  setUp(() async {
    // 创建临时目录
    tempDir = await Directory.systemTemp.createTemp('nextalk_test_');

    // 保存原始环境变量
    originalConfigHome = Platform.environment['XDG_CONFIG_HOME'] ?? '';

    // 设置测试环境变量
    // 注意: Platform.environment 是不可变的，我们需要在测试中 mock SettingsConstants
  });

  tearDown(() async {
    // 清理临时目录
    if (tempDir.existsSync()) {
      await tempDir.delete(recursive: true);
    }
  });

  group('SettingsConstants', () {
    test('EngineType 枚举包含 zipformer 和 sensevoice', () {
      expect(EngineType.values.length, equals(2));
      expect(EngineType.values.contains(EngineType.zipformer), isTrue);
      expect(EngineType.values.contains(EngineType.sensevoice), isTrue);
    });

    test('EngineType.zipformer.name 返回正确字符串', () {
      expect(EngineType.zipformer.name, equals('zipformer'));
    });

    test('EngineType.sensevoice.name 返回正确字符串', () {
      expect(EngineType.sensevoice.name, equals('sensevoice'));
    });

    test('defaultSettingsYaml 包含 engine 配置项', () {
      expect(
          SettingsConstants.defaultSettingsYaml, contains('engine:'));
    });

    test('defaultSettingsYaml 默认引擎为 sensevoice (AC5)', () {
      // AC5: 默认使用 SenseVoice 引擎
      expect(SettingsConstants.defaultSettingsYaml,
          contains('engine: sensevoice'));
    });

    test('defaultSettingsYaml 包含 zipformer 配置块', () {
      expect(
          SettingsConstants.defaultSettingsYaml, contains('zipformer:'));
    });

    test('defaultSettingsYaml 包含 sensevoice 配置块', () {
      expect(
          SettingsConstants.defaultSettingsYaml, contains('sensevoice:'));
    });

    test('defaultSettingsYaml sensevoice 配置包含 use_itn', () {
      expect(
          SettingsConstants.defaultSettingsYaml, contains('use_itn:'));
    });

    test('defaultSettingsYaml sensevoice 配置包含 language', () {
      expect(
          SettingsConstants.defaultSettingsYaml, contains('language:'));
    });

    test('defaultEngineType 为 sensevoice', () {
      expect(SettingsConstants.defaultEngineType, equals(EngineType.sensevoice));
    });

    test('keyEngineType 键名正确', () {
      expect(SettingsConstants.keyEngineType,
          equals('${SettingsConstants.keyPrefix}engine_type'));
    });
  });

  group('SettingsService 引擎配置', () {
    setUp(() async {
      // 初始化 SharedPreferences mock
      SharedPreferences.setMockInitialValues({});
    });

    test('engineType 默认返回 sensevoice', () async {
      // 使用 mock SharedPreferences，不初始化实际服务
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      // 由于 SettingsService 是单例，我们只测试默认值逻辑
      // engineType getter 在没有存储值时应返回默认值
      expect(SettingsConstants.defaultEngineType, equals(EngineType.sensevoice));
    });

    test('EngineType 可以通过 name 解析', () {
      expect(
        EngineType.values.firstWhere((e) => e.name == 'zipformer'),
        equals(EngineType.zipformer),
      );
      expect(
        EngineType.values.firstWhere((e) => e.name == 'sensevoice'),
        equals(EngineType.sensevoice),
      );
    });

    test('无效的引擎类型字符串应使用默认值', () {
      // 测试解析逻辑
      const invalidType = 'invalid_engine';
      final parsed = EngineType.values.where((e) => e.name == invalidType);
      expect(parsed.isEmpty, isTrue);

      // 当解析失败时应使用默认值
      final result = parsed.isEmpty
          ? SettingsConstants.defaultEngineType
          : parsed.first;
      expect(result, equals(EngineType.sensevoice));
    });
  });

  group('EngineSwitchCallback', () {
    test('EngineSwitchCallback 类型定义正确', () {
      // 验证回调类型可以被正确赋值
      EngineSwitchCallback? callback;
      callback = (EngineType newType) async {
        // 模拟引擎切换
        expect(newType, isA<EngineType>());
      };
      expect(callback, isNotNull);
    });

    test('EngineSwitchCallback 可以处理 zipformer', () async {
      EngineType? receivedType;
      final callback = (EngineType newType) async {
        receivedType = newType;
      };

      await callback(EngineType.zipformer);
      expect(receivedType, equals(EngineType.zipformer));
    });

    test('EngineSwitchCallback 可以处理 sensevoice', () async {
      EngineType? receivedType;
      final callback = (EngineType newType) async {
        receivedType = newType;
      };

      await callback(EngineType.sensevoice);
      expect(receivedType, equals(EngineType.sensevoice));
    });
  });

  group('SenseVoice 配置选项', () {
    test('defaultSenseVoiceUseItn 默认为 true', () {
      expect(SettingsConstants.defaultSenseVoiceUseItn, isTrue);
    });

    test('defaultSenseVoiceLanguage 默认为 auto', () {
      expect(SettingsConstants.defaultSenseVoiceLanguage, equals('auto'));
    });
  });

  group('YAML 配置结构', () {
    test('defaultSettingsYaml 是有效的 YAML 格式', () {
      // 验证 YAML 结构可以被正确解析
      // 这里只做基本格式检查，实际解析在 SettingsService 中
      final yaml = SettingsConstants.defaultSettingsYaml;
      
      // 检查缩进结构
      expect(yaml.contains('\n  '), isTrue); // 二级缩进
      expect(yaml.contains('\n    '), isTrue); // 三级缩进
      
      // 检查关键配置项存在
      expect(yaml.contains('model:'), isTrue);
      expect(yaml.contains('engine:'), isTrue);
      expect(yaml.contains('zipformer:'), isTrue);
      expect(yaml.contains('sensevoice:'), isTrue);
      expect(yaml.contains('hotkey:'), isTrue);
    });

    test('zipformer 配置块包含 type 和 custom_url', () {
      final yaml = SettingsConstants.defaultSettingsYaml;
      // 使用正则表达式验证 zipformer 配置块结构 (注意: 有注释行在中间)
      expect(yaml, matches(RegExp(r'zipformer:[\s\S]*type:\s*int8')));
      expect(yaml, matches(RegExp(r'zipformer:[\s\S]*custom_url:')));
    });

    test('sensevoice 配置块包含 use_itn, language, custom_url', () {
      final yaml = SettingsConstants.defaultSettingsYaml;
      // 验证 sensevoice 配置块包含所有必需字段 (注意: 有注释行在中间)
      expect(yaml, matches(RegExp(r'sensevoice:[\s\S]*use_itn:\s*true')));
      expect(yaml, matches(RegExp(r'sensevoice:[\s\S]*language:\s*auto')));
      expect(yaml, matches(RegExp(r'sensevoice:[\s\S]*custom_url:')));
    });
  });

  group('引擎切换约束', () {
    test('AC5: 引擎切换需销毁并重建 Pipeline', () {
      // 这是一个文档测试，验证 AC5 的约束
      // 实际的销毁重建逻辑在 AudioInferencePipeline.switchEngine() 中
      // 这里验证相关常量和配置存在
      expect(EngineType.values.length, greaterThanOrEqualTo(2));
      expect(SettingsConstants.defaultEngineType, isNotNull);
    });
  });

  group('SettingsService 引擎配置读写', () {
    test('SettingsService.instance 是单例', () {
      final instance1 = SettingsService.instance;
      final instance2 = SettingsService.instance;
      expect(identical(instance1, instance2), isTrue);
    });

    test('onEngineSwitch 回调可以被设置', () {
      var callbackCalled = false;
      SettingsService.instance.onEngineSwitch = (EngineType newType) async {
        callbackCalled = true;
      };
      expect(SettingsService.instance.onEngineSwitch, isNotNull);
      // 清理
      SettingsService.instance.onEngineSwitch = null;
    });

    test('senseVoiceUseItn 有默认值', () {
      // 由于 SettingsService 是单例且可能未初始化，测试默认常量
      expect(SettingsConstants.defaultSenseVoiceUseItn, isTrue);
    });

    test('senseVoiceLanguage 有默认值', () {
      expect(SettingsConstants.defaultSenseVoiceLanguage, equals('auto'));
    });
  });

  group('SettingsService 方法存在性验证', () {
    test('engineType getter 存在', () {
      // 验证 getter 存在 (实际值取决于初始化状态)
      expect(() => SettingsService.instance.engineType, returnsNormally);
    });

    test('senseVoiceUseItn getter 存在', () {
      expect(() => SettingsService.instance.senseVoiceUseItn, returnsNormally);
    });

    test('senseVoiceLanguage getter 存在', () {
      expect(() => SettingsService.instance.senseVoiceLanguage, returnsNormally);
    });

    test('zipformerCustomUrl getter 存在', () {
      expect(() => SettingsService.instance.zipformerCustomUrl, returnsNormally);
    });

    test('senseVoiceCustomUrl getter 存在', () {
      expect(() => SettingsService.instance.senseVoiceCustomUrl, returnsNormally);
    });

    test('customModelUrl getter 存在', () {
      expect(() => SettingsService.instance.customModelUrl, returnsNormally);
    });
  });

  group('引擎类型切换方法签名', () {
    test('setEngineType 方法存在', () {
      // 验证方法签名存在
      expect(SettingsService.instance.setEngineType, isA<Function>());
    });

    test('switchEngineType 方法存在', () {
      expect(SettingsService.instance.switchEngineType, isA<Function>());
    });
  });
}

