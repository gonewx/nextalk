import 'package:flutter/material.dart';

import 'services/window_service.dart';
import 'ui/capsule_widget.dart';

/// Nextalk Voice Capsule 入口
/// Story 3-1: 透明胶囊窗口基础
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 初始化窗口管理服务 (配置透明、无边框、固定尺寸等)
  await WindowService.instance.initialize();

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
          text: '', // Story 3-3 将绑定实际文本
          showHint: true,
          hintText: '正在聆听...',
        ),
      ),
    );
  }
}
