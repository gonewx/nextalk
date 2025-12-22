import 'package:flutter/material.dart';

import 'services/hotkey_service.dart';
import 'services/tray_service.dart';
import 'services/window_service.dart';
import 'ui/capsule_widget.dart';

/// Nextalk Voice Capsule 入口
/// Story 3-1: 透明胶囊窗口基础
/// Story 3-4: 系统托盘集成
/// Story 3-5: 全局快捷键监听
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 初始化窗口管理服务 (配置透明、无边框等，但不显示)
  // Story 3-4: showOnStartup: false - 默认托盘驻留
  await WindowService.instance.initialize(showOnStartup: false);

  // 初始化托盘服务 (必须在 WindowService 之后)
  await TrayService.instance.initialize();

  // Story 3-5 AC8: 初始化全局快捷键服务
  // 注意: 完整的 HotkeyController 集成将在 Story 3-6 完成
  await HotkeyService.instance.initialize();

  // AC7: 检查快捷键注册状态并记录日志
  if (HotkeyService.instance.registrationFailed) {
    // ignore: avoid_print
    print('[main] ⚠️ 快捷键注册失败，请检查是否被其他应用占用');
  } else if (HotkeyService.instance.currentHotkey != null) {
    // ignore: avoid_print
    print('[main] ✅ 快捷键已注册');
  }

  // TODO(Story 3-6): 设置 onBeforeExit 回调释放 Epic 2 资源
  // TrayService.instance.onBeforeExit = () async {
  //   await pipeline.dispose();  // 释放 AudioCapture + SherpaService
  //   fcitxClient.close();       // 关闭 Socket 连接
  // };

  runApp(const NextalkApp());
}

/// Nextalk 应用根 Widget
class NextalkApp extends StatelessWidget {
  const NextalkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Nextalk Voice Capsule',
      theme: ThemeData.dark().copyWith(
        // 确保 Scaffold 背景透明 - Story 3-1 AC2
        scaffoldBackgroundColor: Colors.transparent,
      ),
      home: const Scaffold(
        backgroundColor: Colors.transparent,
        body: CapsuleWidget(
          text: '', // Story 3-6 将绑定实际 ASR 文本
          showHint: true,
          hintText: '正在聆听...',
        ),
      ),
    );
  }
}
