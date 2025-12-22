import 'package:flutter/material.dart';

import 'constants/window_constants.dart';
import 'services/window_service.dart';

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
        // 确保 Scaffold 背景透明 - AC2
        scaffoldBackgroundColor: Colors.transparent,
      ),
      home: const TransparentCapsule(),
    );
  }
}

/// 透明胶囊测试 Widget
/// 临时实现用于验证透明效果，Story 3-2 将替换为完整 UI
class TransparentCapsule extends StatelessWidget {
  const TransparentCapsule({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: GestureDetector(
        // 拖拽移动支持 - AC9
        onPanStart: (_) => WindowService.instance.startDragging(),
        child: Center(
          child: Container(
            width: WindowConstants.capsuleWidth,
            height: WindowConstants.capsuleHeight,
            decoration: BoxDecoration(
              // 半透明黑色背景用于测试
              color: const Color.fromRGBO(0, 0, 0, 0.7),
              borderRadius: BorderRadius.circular(WindowConstants.capsuleRadius),
              // 添加边框以便在透明背景上可见
              border: Border.all(
                color: const Color.fromRGBO(255, 255, 255, 0.3),
                width: 1,
              ),
              // 添加阴影效果
              boxShadow: const [
                BoxShadow(
                  color: Color.fromRGBO(0, 0, 0, 0.3),
                  blurRadius: 20,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: const Center(
              child: Text(
                '🎤 Nextalk',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
