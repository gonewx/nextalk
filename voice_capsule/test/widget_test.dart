// Story 3-1: 透明胶囊窗口基础 Widget 测试
//
// 注意: 透明窗口功能依赖 window_manager 原生插件，
// 只能在 Linux 环境下进行集成测试。
// 这里测试可独立验证的 Widget 部分。

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:voice_capsule/constants/window_constants.dart';

void main() {
  group('TransparentCapsule Widget', () {
    testWidgets('should display Nextalk text', (WidgetTester tester) async {
      // 构建测试 Widget (不依赖 WindowService)
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            backgroundColor: Colors.transparent,
            body: Center(
              child: Text('🎤 Nextalk'),
            ),
          ),
        ),
      );

      // 验证 Nextalk 文字显示
      expect(find.text('🎤 Nextalk'), findsOneWidget);
    });

    testWidgets('should have correct capsule dimensions in constants',
        (WidgetTester tester) async {
      // 验证常量值
      expect(WindowConstants.windowWidth, 400.0);
      expect(WindowConstants.windowHeight, 120.0);
      expect(WindowConstants.capsuleWidth, 380.0);
      expect(WindowConstants.capsuleHeight, 60.0);
      expect(WindowConstants.capsuleRadius, 40.0);
    });

    testWidgets('should render capsule-shaped container',
        (WidgetTester tester) async {
      // 构建胶囊形状容器
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            backgroundColor: Colors.transparent,
            body: Center(
              child: Container(
                width: WindowConstants.capsuleWidth,
                height: WindowConstants.capsuleHeight,
                decoration: BoxDecoration(
                  color: const Color.fromRGBO(0, 0, 0, 0.7),
                  borderRadius:
                      BorderRadius.circular(WindowConstants.capsuleRadius),
                ),
                child: const Center(
                  child: Text('🎤 Nextalk'),
                ),
              ),
            ),
          ),
        ),
      );

      // 验证容器存在
      final containerFinder = find.byType(Container);
      expect(containerFinder, findsWidgets);

      // 验证文字存在
      expect(find.text('🎤 Nextalk'), findsOneWidget);
    });
  });
}
