import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/app/nextalk_app.dart';
import 'package:voice_capsule/services/model_manager.dart';
import 'package:voice_capsule/state/capsule_state.dart';
import 'package:voice_capsule/ui/capsule_widget.dart';
import 'package:voice_capsule/ui/gradient_text_flow.dart';

/// 辅助函数: 查找文本 (支持普通 Text 和 GradientTextFlowWithFade)
Finder findTextInCapsule(String text) {
  return find.byWidgetPredicate((widget) {
    if (widget is GradientTextFlowWithFade) {
      return widget.text == text;
    }
    return false;
  });
}

/// 辅助函数: 验证文本是否显示在胶囊中
void expectTextInCapsule(WidgetTester tester, String text) {
  // 先尝试普通 Text
  final textFinder = find.text(text);
  if (textFinder.evaluate().isNotEmpty) {
    expect(textFinder, findsOneWidget);
    return;
  }
  // 再尝试 GradientTextFlowWithFade
  final gradientFinder = findTextInCapsule(text);
  expect(gradientFinder, findsOneWidget,
      reason: '文本 "$text" 未在普通 Text 或 GradientTextFlowWithFade 中找到');
}

/// 辅助函数: 验证文本不存在
void expectTextNotInCapsule(WidgetTester tester, String text) {
  expect(find.text(text), findsNothing);
  expect(findTextInCapsule(text), findsNothing);
}

/// 测试用 ModelManager，模拟模型已就绪状态
class TestModelManager extends ModelManager {
  final bool _modelReady;

  TestModelManager({bool modelReady = true}) : _modelReady = modelReady;

  @override
  bool get isModelReady => _modelReady;
}

void main() {
  group('NextalkApp', () {
    late StreamController<CapsuleStateData> stateController;
    late TestModelManager testModelManager;

    setUp(() {
      stateController = StreamController<CapsuleStateData>.broadcast();
      // 默认模拟模型已就绪，显示正常胶囊 UI
      testModelManager = TestModelManager(modelReady: true);
    });

    tearDown(() async {
      await stateController.close();
    });

    testWidgets('应该正确渲染 CapsuleWidget', (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.byType(CapsuleWidget), findsOneWidget);
    });

    testWidgets('初始状态应该是 listening (便于开发调试)', (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      // listening 状态 (无文本) 应该显示 hint
      expect(find.text('正在聆听...'), findsOneWidget);
    });

    testWidgets('listening 状态 (无文本) 应该显示 hint', (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump(); // 首帧

      stateController.add(CapsuleStateData.listening());
      await tester.pump(); // 等待 StreamBuilder 更新
      await tester.pump(const Duration(milliseconds: 100)); // 等待动画第一帧

      expect(find.text('正在聆听...'), findsOneWidget);
    });

    testWidgets('listening 状态 (有文本) 应该显示识别文本', (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump();

      stateController.add(CapsuleStateData.listening(text: '你好'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expectTextInCapsule(tester, '你好');
    });

    testWidgets('processing 状态应该继续显示文本', (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump();

      stateController.add(CapsuleStateData.processing(text: '你好世界'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expectTextInCapsule(tester, '你好世界');
    });

    testWidgets('error 状态 (socketError) 应该显示错误消息', (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump();

      stateController.add(CapsuleStateData.error(CapsuleErrorType.socketError));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Fcitx5 连接错误'), findsOneWidget);
    });

    testWidgets('error 状态 (audioInitFailed) 应该显示错误消息', (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump();

      stateController
          .add(CapsuleStateData.error(CapsuleErrorType.audioInitFailed));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('音频设备初始化失败'), findsOneWidget);
    });

    testWidgets('状态流转: idle -> listening -> processing -> idle',
        (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump();

      // idle -> listening (无文本)
      stateController.add(CapsuleStateData.listening());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.text('正在聆听...'), findsOneWidget);

      // listening (有文本)
      stateController.add(CapsuleStateData.listening(text: '你好'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expectTextInCapsule(tester, '你好');

      // listening -> processing
      stateController.add(CapsuleStateData.processing(text: '你好世界'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expectTextInCapsule(tester, '你好世界');

      // processing -> idle
      stateController.add(CapsuleStateData.idle());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      // idle 状态文本清空
      expectTextNotInCapsule(tester, '你好世界');
    });

    testWidgets('StreamBuilder 应该自动管理订阅生命周期', (tester) async {
      await tester.pumpWidget(NextalkApp(
        stateController: stateController,
        modelManager: testModelManager,
      ));
      await tester.pump();

      // 发送多个状态更新，确保 StreamBuilder 正常工作
      stateController.add(CapsuleStateData.listening(text: '测试1'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expectTextInCapsule(tester, '测试1');

      stateController.add(CapsuleStateData.listening(text: '测试2'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expectTextInCapsule(tester, '测试2');
    });
  });
}
