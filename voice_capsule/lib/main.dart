import 'dart:async';
import 'package:flutter/material.dart';

import 'app/nextalk_app.dart';
import 'services/audio_capture.dart';
import 'services/audio_inference_pipeline.dart';
import 'services/fcitx_client.dart';
import 'services/hotkey_controller.dart';
import 'services/hotkey_service.dart';
import 'services/model_manager.dart';
import 'services/sherpa_service.dart';
import 'services/tray_service.dart';
import 'services/window_service.dart';
import 'state/capsule_state.dart';
import 'utils/diagnostic_logger.dart';

/// Nextalk Voice Capsule 入口
/// Story 3-6: 完整业务流串联
/// Story 3-7: 全局错误边界与诊断日志

/// 全局状态控制器 (用于 UI 更新)
final _stateController = StreamController<CapsuleStateData>.broadcast();

/// 全局服务实例
AudioCapture? _audioCapture;
SherpaService? _sherpaService;
AudioInferencePipeline? _pipeline;
FcitxClient? _fcitxClient;

Future<void> main() async {
  // Story 3-7: 使用 runZonedGuarded 捕获未处理异常 (AC17)
  runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();

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

    // 2. 初始化托盘服务 (必须在 WindowService 之后)
    await TrayService.instance.initialize();

    // 3. 初始化全局快捷键服务
    await HotkeyService.instance.initialize();

    // 4. 检查/下载模型
    final modelManager = ModelManager();
    if (!modelManager.isModelReady) {
      // TODO: 显示下载进度 UI (Post-MVP)
      // ignore: avoid_print
      print('[main] 模型未就绪，请先运行模型下载');
      DiagnosticLogger.instance.warn('main', '模型未就绪');
      // 暂时跳过，允许应用启动
    }

    // 5. 创建服务实例 (即使模型未就绪也创建，便于后续初始化)
    _audioCapture = AudioCapture();
    _sherpaService = SherpaService();

    // 6. 创建音频推理流水线
    _pipeline = AudioInferencePipeline(
      audioCapture: _audioCapture!,
      sherpaService: _sherpaService!,
      modelManager: modelManager,
      enableDebugLog: true, // 开发阶段启用日志
    );

    // 7. 创建 FcitxClient (延迟连接)
    _fcitxClient = FcitxClient();

    // 8. 初始化快捷键控制器 (核心集成点)
    await HotkeyController.instance.initialize(
      pipeline: _pipeline!,
      fcitxClient: _fcitxClient!,
      stateController: _stateController,
    );

    // 9. 设置托盘回调 (AC12: 释放所有资源, AC16: 重连 Fcitx5)
    TrayService.instance.onBeforeExit = () async {
      DiagnosticLogger.instance.info('main', '开始清理资源...');

      // 释放控制器
      await HotkeyController.instance.dispose();

      // 释放快捷键服务
      await HotkeyService.instance.dispose();

      // 释放流水线 (包含 AudioCapture + SherpaService)
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

    // 10. 启动应用
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
