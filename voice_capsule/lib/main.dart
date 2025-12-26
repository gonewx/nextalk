import 'dart:async';
import 'package:flutter/material.dart';

import 'app/nextalk_app.dart';
import 'services/animation_ticker_service.dart';
import 'constants/settings_constants.dart';
import 'services/asr/asr_engine.dart';
import 'services/asr/asr_engine_factory.dart';
import 'services/asr/engine_initializer.dart';
import 'services/audio_capture.dart';
import 'services/audio_inference_pipeline.dart';
import 'services/command_server.dart';
import 'services/fcitx_client.dart';
import 'services/hotkey_controller.dart';
import 'services/hotkey_service.dart';
import 'services/language_service.dart';
import 'services/model_manager.dart';
import 'services/settings_service.dart';
import 'services/tray_service.dart';
import 'services/window_service.dart';
import 'state/capsule_state.dart';
import 'utils/diagnostic_logger.dart';

/// Nextalk Voice Capsule 入口
/// Story 3-6: 完整业务流串联
/// Story 3-7: 全局错误边界与诊断日志
/// Story 2-7: 支持多引擎 ASR

/// 将 EngineType 转换为 ASREngineType
ASREngineType _toASREngineType(EngineType type) {
  return switch (type) {
    EngineType.zipformer => ASREngineType.zipformer,
    EngineType.sensevoice => ASREngineType.sensevoice,
  };
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
    } else {
      DiagnosticLogger.instance.warn('main', '⚠️ ASR 引擎预初始化失败: $error');
    }
  }
}

/// 全局状态控制器 (用于 UI 更新)
final _stateController = StreamController<CapsuleStateData>.broadcast();

/// 全局服务实例
AudioCapture? _audioCapture;
ASREngine? _asrEngine;
AudioInferencePipeline? _pipeline;
FcitxClient? _fcitxClient;

Future<void> main() async {
  // Story 3-7: 使用 runZonedGuarded 捕获未处理异常 (AC17)
  runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();

    // 启动动画预热服务 (确保呼吸灯无延迟显示)
    AnimationTickerService.instance.start();

    // Story 3-7: 初始化诊断日志系统
    await DiagnosticLogger.instance.initialize();
    DiagnosticLogger.instance.info('main', '应用启动');

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
    await TrayService.instance.initialize();

    // 4. 初始化全局快捷键服务
    await HotkeyService.instance.initialize();

    // 4.1 启动命令服务器 (接收 Fcitx5 插件的快捷键命令，支持 Wayland)
    await CommandServer.instance.start();
    DiagnosticLogger.instance.info('main', '命令服务器启动完成');

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

    // 6.1 预热音频设备 (避免第一次录音时因设备初始化延迟导致丢失语音)
    final warmupError = await _audioCapture!.warmup();
    if (warmupError == AudioCaptureError.none) {
      DiagnosticLogger.instance.info('main', '✅ 音频设备预热完成');
    } else {
      DiagnosticLogger.instance.warn('main', '⚠️ 音频设备预热失败: $warmupError');
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

    // 9.1 设置命令服务器回调 (Wayland 快捷键支持)
    CommandServer.instance.onCommand = (command) {
      DiagnosticLogger.instance.info('main', '收到 Fcitx5 命令: $command');
      if (command == 'toggle') {
        // 触发与快捷键相同的动作
        HotkeyController.instance.toggle();
      } else if (command == 'show') {
        HotkeyController.instance.show();
      } else if (command == 'hide') {
        HotkeyController.instance.hide();
      }
    };

    // 10. 设置托盘回调 (AC12: 释放所有资源, AC16: 重连 Fcitx5)
    TrayService.instance.onBeforeExit = () async {
      DiagnosticLogger.instance.info('main', '开始清理资源...');

      // 停止动画预热服务
      AnimationTickerService.instance.stop();

      // 停止命令服务器
      await CommandServer.instance.dispose();

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
    runApp(NextalkApp(
      stateController: _stateController,
      modelManager: modelManager,
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
