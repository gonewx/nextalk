import 'dart:async';
import 'dart:ffi';
import 'dart:io';
import 'package:ffi/ffi.dart';
import 'package:flutter/material.dart';

import 'app/nextalk_app.dart';
import 'services/animation_ticker_service.dart';
import 'constants/settings_constants.dart';
import 'services/asr/asr_engine.dart';
import 'services/asr/asr_engine_factory.dart';
import 'services/asr/engine_initializer.dart';
import 'services/audio_capture.dart';
import 'services/audio_inference_pipeline.dart';
import 'services/fcitx_client.dart';
import 'services/hotkey_controller.dart';
import 'services/hotkey_service.dart';
import 'services/language_service.dart';
import 'services/model_manager.dart';
import 'services/portal_hotkey_service.dart';
import 'services/settings_service.dart';
import 'services/single_instance.dart';
import 'services/tray_service.dart';
import 'services/window_service.dart';
import 'state/capsule_state.dart';
import 'utils/diagnostic_logger.dart';
import 'cli/audio_command.dart';

/// Nextalk Voice Capsule 入口
/// Story 3-6: 完整业务流串联
/// Story 3-7: 全局错误边界与诊断日志
/// Story 2-7: 支持多引擎 ASR
/// SCP-002: 极简架构 - 系统快捷键 + --toggle 参数

/// 将 EngineType 转换为 ASREngineType
ASREngineType _toASREngineType(EngineType type) {
  return switch (type) {
    EngineType.zipformer => ASREngineType.zipformer,
    EngineType.sensevoice => ASREngineType.sensevoice,
  };
}

/// 处理命令行参数
///
/// 支持的命令：
/// help: 显示帮助信息
/// audio [...]: 音频设备配置命令 (Story 3-9)
/// --toggle: 切换窗口/录音状态
/// --show: 显示窗口并开始录音
/// --hide: 隐藏窗口并停止录音
///
/// 返回 true 表示应用应该继续运行，false 表示应该退出
Future<bool> _handleCommandLineArgs(List<String> args) async {
  if (args.isEmpty) {
    return true; // 无参数，正常启动
  }

  final command = args[0];

  // help / --help / -h: 显示帮助
  if (command == 'help' || command == '--help' || command == '-h') {
    _printHelp();
    exit(0);
  }

  // version / --version / -v: 显示版本
  if (command == 'version' || command == '--version' || command == '-v') {
    _printVersion();
    exit(0);
  }

  // Story 3-9: audio 子命令
  if (command == 'audio') {
    final subArgs = args.length > 1 ? args.sublist(1) : <String>[];
    final exitCode = await AudioCommand.execute(subArgs);
    exit(exitCode);
  }

  // 检查是否是命令参数
  if (command == '--toggle' || command == '--show' || command == '--hide') {
    final cmdName = command.substring(2); // 移除 '--' 前缀

    // 尝试发送命令给运行中的实例
    final sent = await SingleInstance.instance.sendCommandToRunningInstance(cmdName);

    if (sent) {
      // 命令已发送，退出当前进程
      // ignore: avoid_print
      print('[main] 命令已发送到运行中的实例: $cmdName');
      return false;
    } else {
      // 没有运行中的实例
      if (command == '--toggle' || command == '--show') {
        // 启动应用并显示窗口
        // ignore: avoid_print
        print('[main] 无运行实例，启动应用');
        return true;
      } else {
        // --hide 但没有运行实例，直接退出
        // ignore: avoid_print
        print('[main] 无运行实例，忽略 hide 命令');
        return false;
      }
    }
  }

  // 未知命令，显示帮助
  // ignore: avoid_print
  print('未知命令: $command\n');
  _printHelp();
  exit(1);
}

/// 打印帮助信息
void _printHelp() {
  // ignore: avoid_print
  print('''
Nextalk - Linux 离线语音输入

用法:
  nextalk                    启动应用
  nextalk help               显示此帮助
  nextalk version            显示版本信息
  nextalk audio [子命令]      音频设备配置

  nextalk --toggle           切换窗口/录音状态
  nextalk --show             显示窗口并开始录音
  nextalk --hide             隐藏窗口并停止录音

音频子命令:
  nextalk audio              交互模式选择设备
  nextalk audio <序号>       设置指定设备
  nextalk audio default      恢复默认设备
  nextalk audio list         列出所有设备
  nextalk audio help         显示音频命令帮助

更多信息: https://github.com/anthropics/nextalk
''');
}

/// 应用版本号 (构建时通过 --dart-define=APP_VERSION=x.x.x 注入)
const String appVersion = String.fromEnvironment(
  'APP_VERSION',
  defaultValue: 'dev',
);

/// 打印版本信息
void _printVersion() {
  // ignore: avoid_print
  print('Nextalk v$appVersion');
}

/// 预初始化 ASR 引擎
///
/// 在应用启动时预先初始化引擎，触发 onnxruntime JIT 编译，
/// 避免第一次录音时因编译延迟导致丢失语音。
Future<void> _preInitializeEngine(ModelManager modelManager) async {
  if (_asrEngine == null || !_asrEngine!.isInitialized) {
    // 根据引擎类型创建配置
    ASRConfig config;
    if (_asrEngine!.engineType == ASREngineType.zipformer) {
      config = ZipformerConfig(
        modelDir: modelManager.modelPath,
        useInt8Model: SettingsService.instance.modelType == ModelType.int8,
      );
    } else {
      config = SenseVoiceConfig(
        modelDir: modelManager.getModelPathForEngine(EngineType.sensevoice),
        vadModelPath: modelManager.vadModelFilePath,
      );
    }

    // 预初始化引擎
    final error = await _asrEngine!.initialize(config);
    if (error == ASRError.none) {
      DiagnosticLogger.instance.info('main', '✅ ASR 引擎预初始化完成');
      _warmupEngineWithSilence();
    } else {
      DiagnosticLogger.instance.warn('main', '⚠️ ASR 引擎预初始化失败: $error');
    }
  }
}

/// 用静音数据跑一轮真实推理，触发 onnxruntime 的懒初始化
/// (内存 arena 分配、图优化、量化 kernel 选择均发生在首次 Run)，
/// 避免用户第一次按快捷键时首块推理明显偏慢。
void _warmupEngineWithSilence() {
  final engine = _asrEngine;
  if (engine == null || !engine.isInitialized) return;

  const warmupSamples = 12800; // 0.8s @ 16kHz，足以凑满流式模型首个 chunk
  final silence = calloc<Float>(warmupSamples); // calloc 归零即静音
  try {
    final sw = Stopwatch()..start();
    engine.acceptWaveform(16000, silence, warmupSamples);
    while (engine.isReady()) {
      engine.decode();
    }
    engine.reset(); // 清空流状态，不影响首次真实识别
    sw.stop();
    DiagnosticLogger.instance
        .info('main', '✅ 引擎推理预热完成 (${sw.elapsedMilliseconds}ms)');
  } catch (e) {
    DiagnosticLogger.instance.warn('main', '⚠️ 引擎推理预热失败(不影响使用): $e');
  } finally {
    calloc.free(silence);
  }
}

/// 全局状态控制器 (用于 UI 更新)
final _stateController = StreamController<CapsuleStateData>.broadcast();

/// 全局服务实例
AudioCapture? _audioCapture;
ASREngine? _asrEngine;
AudioInferencePipeline? _pipeline;
FcitxClient? _fcitxClient;

/// Story 3-10: Portal 全局快捷键服务 (可选，backend 不支持时保持 null)
PortalHotkeyService? _portalHotkeyService;

/// Story 3-10: 在后台非阻塞地探测并注册 Portal 全局快捷键。
///
/// 关键约束：**不能拖慢启动主路径**——portal backend 可能挂起，因此整个流程
/// 放在后台 Future 中，失败静默降级到系统快捷键 + nextalk-toggle 回退方案
/// (AC4)。注册结果只影响 HotkeyService.hotkeyMode 的展示，不影响业务可用性。
Future<void> _setupPortalHotkey() async {
  try {
    final service = PortalHotkeyService();
    _portalHotkeyService = service;
    final result = await service.register();

    if (result == PortalRegistrationResult.registered) {
      HotkeyService.instance.hotkeyMode = HotkeyMode.portal;
      DiagnosticLogger.instance
          .info('main', 'Portal 全局快捷键已启用 (Alt+Space)');
    } else {
      // 降级：保持系统快捷键模式，记录原因 (AC4)
      HotkeyService.instance.hotkeyMode = HotkeyMode.system;
      DiagnosticLogger.instance.info(
        'main',
        'Portal 不可用，使用系统快捷键回退 (原因: ${service.fallbackReason})',
      );
      // 已降级则无需保活连接，释放
      await service.dispose();
      _portalHotkeyService = null;
    }

    // 刷新托盘菜单以展示最终快捷键模式 (AC4；rebuildMenu 自带初始化守卫)
    await TrayService.instance.rebuildMenu();
  } catch (e) {
    // 探测/注册意外异常也不能影响启动
    HotkeyService.instance.hotkeyMode = HotkeyMode.system;
    DiagnosticLogger.instance
        .warn('main', 'Portal 快捷键装配异常，回退到系统快捷键: $e');
  }
}

Future<void> main(List<String> args) async {
  // SCP-002: 处理命令行参数 (--toggle, --show, --hide)
  final shouldContinue = await _handleCommandLineArgs(args);
  if (!shouldContinue) {
    exit(0);
  }

  // Story 3-7: 使用 runZonedGuarded 捕获未处理异常 (AC17)
  runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();

    // SCP-002: 单实例检测
    final isMainInstance = await SingleInstance.instance.tryBecomeMainInstance();
    if (!isMainInstance) {
      // ignore: avoid_print
      print('[main] 已有实例运行，退出');
      exit(0);
    }

    // 启动动画预热服务 (确保呼吸灯无延迟显示)
    AnimationTickerService.instance.start();

    // Story 3-7: 初始化诊断日志系统
    await DiagnosticLogger.instance.initialize();
    DiagnosticLogger.instance.info('main', '应用启动 (SCP-002 极简架构)');

    // Story 3-7: 设置 Flutter 错误处理
    FlutterError.onError = (FlutterErrorDetails details) {
      DiagnosticLogger.instance.exception(
        'FlutterError',
        details.exception,
        details.stack,
      );
      FlutterError.presentError(details);
    };

    // 1. 初始化窗口管理服务 (配置透明、无边框等，但不显示)
    await WindowService.instance.initialize(showOnStartup: false);

    // 2. 初始化设置服务 (必须在托盘服务之前)
    await SettingsService.instance.initialize();
    DiagnosticLogger.instance.info('main', '设置服务初始化完成');

    // Story 3-8: 初始化语言服务 (必须在托盘服务之前)
    await LanguageService.instance.initialize();
    DiagnosticLogger.instance.info('main', '语言服务初始化完成');

    // 3. 初始化托盘服务 (必须在 WindowService 和 SettingsService 之后)
    // 如果设置了 NEXTALK_NO_TRAY=1 环境变量，跳过托盘初始化 (解决某些环境下的段错误)
    final noTray = Platform.environment['NEXTALK_NO_TRAY'] == '1';
    if (noTray) {
      DiagnosticLogger.instance.warn('main', '⚠️ NEXTALK_NO_TRAY=1，跳过托盘初始化');
    } else {
      await TrayService.instance.initialize();
    }

    // 4. 初始化全局快捷键服务 (SCP-002: 简化版，不再同步配置到 Fcitx5)
    await HotkeyService.instance.initialize();

    // 5. 检查/下载模型
    final modelManager = ModelManager();
    if (!modelManager.hasAnyEngineReady) {
      // TODO: 显示下载进度 UI (Post-MVP)
      // ignore: avoid_print
      print('[main] 模型未就绪，请先运行模型下载');
      DiagnosticLogger.instance.warn('main', '模型未就绪');
      // 暂时跳过，允许应用启动
    }

    // 6. 创建服务实例 (即使模型未就绪也创建，便于后续初始化)
    _audioCapture = AudioCapture();

    // 6.1 Story 3-9: 预热音频设备，使用配置的设备名称 (AC2, AC3)
    final configuredDevice = SettingsService.instance.audioInputDevice;
    final warmupError = await _audioCapture!.warmup(deviceName: configuredDevice);
    String? audioErrorDetail;
    if (warmupError == AudioCaptureError.none) {
      DiagnosticLogger.instance.info('main', '✅ 音频设备预热完成');
      // Story 3-9 AC18: 检测设备回退
      if (_audioCapture!.lastDeviceFallback) {
        DiagnosticLogger.instance.warn('main', '⚠️ 配置的设备不存在，已回退到默认设备');
        // 发送桌面通知
        final lang = LanguageService.instance;
        try {
          await Process.run('notify-send', [
            '-a',
            'Nextalk',
            '-i',
            'dialog-warning',
            'Nextalk',
            lang.isZh
                ? '配置的音频设备"$configuredDevice"不存在，已使用默认设备'
                : 'Configured audio device "$configuredDevice" not found, using default device',
          ]);
        } catch (e) {
          DiagnosticLogger.instance.warn('main', '发送通知失败: $e');
        }
      }
    } else {
      DiagnosticLogger.instance.warn('main', '⚠️ 音频设备预热失败: $warmupError');
      audioErrorDetail = _audioCapture!.lastErrorDetail;
      if (audioErrorDetail != null) {
        DiagnosticLogger.instance.warn('main', '📋 $audioErrorDetail');
        DiagnosticLogger.instance.warn('main', '💡 可能原因: 1) PulseAudio/PipeWire 未运行 2) 设备被占用 3) 权限不足');
      }
    }

    // Story 2-7: 使用 EngineInitializer 初始化引擎 (带回退逻辑)
    final engineInitializer = EngineInitializer(modelManager);
    final configuredEngineType = SettingsService.instance.engineType;

    try {
      final initResult = await engineInitializer.initialize(
        preferredType: configuredEngineType,
        enableDebugLog: false,
      );

      _asrEngine = initResult.engine;
      // Story 2-7: 更新实际引擎类型 (单一来源: SettingsService)
      SettingsService.instance.setActualEngineType(initResult.actualEngineType);

      if (initResult.fallbackOccurred) {
        DiagnosticLogger.instance.warn(
          'main',
          '引擎回退: $configuredEngineType → ${initResult.actualEngineType}, '
          '原因: ${initResult.fallbackReason}',
        );
        // 重建托盘菜单以显示实际引擎标记
        await TrayService.instance.rebuildMenu();
      } else {
        DiagnosticLogger.instance.info('main', '创建 ASR 引擎: $configuredEngineType');
      }
    } on EngineNotAvailableException catch (e) {
      // 所有引擎都不可用，创建一个空壳引擎 (实际使用配置的类型)
      DiagnosticLogger.instance.warn('main', '${e.message}, 尝试的引擎: ${e.triedEngines}');
      _asrEngine = ASREngineFactory.create(_toASREngineType(configuredEngineType), enableDebugLog: false);
      SettingsService.instance.setActualEngineType(configuredEngineType);
      // 注意：此时应用会在后续尝试使用引擎时显示下载引导
    }

    // 7. 创建音频推理流水线
    // PTT 模式：VAD 检测停顿但不停止录音，文本跨停顿累积
    _pipeline = AudioInferencePipeline(
      audioCapture: _audioCapture!,
      asrEngine: _asrEngine!,
      modelManager: modelManager,
      enableDebugLog: false,
      vadConfig: const VadConfig(
        autoStopOnEndpoint: false, // 不自动停止，等待用户松开按钮
        autoReset: false, // 不重置，跨停顿累积文本
      ),
    );

    // 7.1 预初始化 ASR 引擎 (触发 onnxruntime JIT 编译，避免第一次录音延迟)
    await _preInitializeEngine(modelManager);


    // 8. 创建 FcitxClient (延迟连接)
    _fcitxClient = FcitxClient();

    // 9. 初始化快捷键控制器 (核心集成点)
    await HotkeyController.instance.initialize(
      pipeline: _pipeline!,
      fcitxClient: _fcitxClient!,
      stateController: _stateController,
    );

    // 9.1 设置单实例命令回调 (SCP-002: 系统快捷键 + --toggle 参数支持)
    SingleInstance.instance.onCommand = (command) {
      DiagnosticLogger.instance.info('main', '收到命令: $command');
      if (command == 'toggle') {
        // 触发与快捷键相同的动作
        HotkeyController.instance.toggle();
      } else if (command == 'show') {
        HotkeyController.instance.show();
      } else if (command == 'hide') {
        HotkeyController.instance.hide();
      }
    };

    // 9.2 Story 3-10: 后台非阻塞装配 Portal 全局快捷键 (AC1/AC4)
    // 放在 HotkeyController.initialize 之后发起，但不 await——portal backend
    // 可能挂起，绝不能拖慢启动主路径 (延迟优化不倒退)。失败静默降级。
    unawaited(_setupPortalHotkey());

    // 10. 设置托盘回调 (AC12: 释放所有资源, AC16: 重连 Fcitx5)
    TrayService.instance.onBeforeExit = () async {
      DiagnosticLogger.instance.info('main', '开始清理资源...');

      // 停止动画预热服务
      AnimationTickerService.instance.stop();

      // 停止单实例服务
      await SingleInstance.instance.dispose();

      // Story 3-10: 关闭 Portal session 与 D-Bus 连接 (AC7)
      await _portalHotkeyService?.dispose();
      _portalHotkeyService = null;

      // 释放控制器
      await HotkeyController.instance.dispose();

      // 释放快捷键服务
      await HotkeyService.instance.dispose();

      // 释放流水线 (包含 AudioCapture + ASREngine)
      await _pipeline?.dispose();

      // 释放 FcitxClient
      await _fcitxClient?.dispose();

      // 关闭状态控制器
      await _stateController.close();

      DiagnosticLogger.instance.info('main', '资源清理完成');
    };

    // Story 3-7: 设置重连 Fcitx5 回调 (AC16)
    TrayService.instance.onReconnectFcitx = () async {
      if (_fcitxClient != null) {
        _fcitxClient!.resetDegradedMode();
        await _fcitxClient!.connect();
        DiagnosticLogger.instance.info('main', 'Fcitx5 重连成功');
      }
    };

    // 设置 TrayService 的 ModelManager 引用 (用于切换引擎时检查模型状态)
    TrayService.instance.setModelManager(modelManager);

    // 11. 设置模型切换回调 (热切换模型版本)
    SettingsService.instance.onModelSwitch = (newType) async {
      if (_pipeline != null) {
        DiagnosticLogger.instance.info('main', '切换模型类型: $newType');
        await _pipeline!.switchModelType(newType);
        DiagnosticLogger.instance.info('main', '模型切换完成');
      }
    };

    // Story 2-7: 设置引擎切换回调 (AC5: 销毁旧 Pipeline → 创建新 Pipeline)
    SettingsService.instance.onEngineSwitch = (newEngineType) async {
      if (_pipeline != null) {
        DiagnosticLogger.instance.info('main', '切换 ASR 引擎: $newEngineType');

        // 创建新引擎实例
        final newEngine = ASREngineFactory.create(_toASREngineType(newEngineType), enableDebugLog: false);

        // 切换引擎 (销毁旧引擎，使用新引擎)
        await _pipeline!.switchEngine(newEngine);

        // 更新全局引擎引用
        _asrEngine = newEngine;

        // 更新实际引擎类型 (单一来源: SettingsService)
        SettingsService.instance.setActualEngineType(newEngineType);

        // 重建托盘菜单以更新选中状态
        await TrayService.instance.rebuildMenu();

        // 切换成功，恢复托盘状态为正常
        await TrayService.instance.updateStatus(TrayStatus.normal);

        DiagnosticLogger.instance.info('main', 'ASR 引擎切换完成: $newEngineType');
      }
    };

    // 12. 启动应用
    // Story 3-7: 传递 modelManager 以便 NextalkApp 根据模型状态路由 UI
    // Story 3-9 AC16: 传递音频设备错误以便显示错误对话框
    runApp(NextalkApp(
      stateController: _stateController,
      modelManager: modelManager,
      audioDeviceError: warmupError != AudioCaptureError.none ? warmupError : null,
      audioDeviceName: configuredDevice,
      audioErrorDetail: audioErrorDetail,
    ));

    DiagnosticLogger.instance.info('main', '应用初始化完成');
  }, (error, stackTrace) {
    // Story 3-7: 捕获未处理异常 (AC17, AC18)
    DiagnosticLogger.instance.exception('Unhandled', error, stackTrace);

    // ignore: avoid_print
    print('[main] 致命错误: $error');
    print(stackTrace);

    // 注意: 这里无法显示 FatalErrorDialog，因为可能在 runApp 之前崩溃
    // 真正的致命错误对话框需要在 MaterialApp 的 builder 中处理
  });
}
