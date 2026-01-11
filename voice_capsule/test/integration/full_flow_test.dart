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

/// Story 3-6: 完整业务流集成测试
///
/// 这些测试验证状态流转和 UI 绑定的正确性。
/// 涉及原生服务 (PortAudio, Sherpa-onnx, Fcitx5) 的完整端到端测试
/// 需要在真实 Linux 环境运行: flutter test -d linux
void main() {
  group('Full Business Flow Tests', () {
    late StreamController<CapsuleStateData> stateController;
    late ModelManager modelManager;

    setUp(() {
      stateController = StreamController<CapsuleStateData>.broadcast();
      modelManager = ModelManager();
    });

    tearDown(() async {
      await stateController.close();
    });

    group('状态流转测试', () {
      testWidgets('AC1: idle -> listening 时应显示呼吸动画状态', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // 切换到 listening 状态
        stateController.add(CapsuleStateData.listening());
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        // 验证 CapsuleWidget 存在
        expect(find.byType(CapsuleWidget), findsOneWidget);
        // 验证 hint 文本显示
        expect(find.text('正在聆听...'), findsOneWidget);
      });

      testWidgets('AC2: 识别文本应实时显示', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // 模拟识别过程中的文本更新
        stateController.add(CapsuleStateData.listening(text: '你'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '你');

        stateController.add(CapsuleStateData.listening(text: '你好'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '你好');

        stateController.add(CapsuleStateData.listening(text: '你好世界'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '你好世界');
      });

      testWidgets('AC4: listening -> processing 流转正确', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // listening 状态
        stateController.add(CapsuleStateData.listening(text: '测试文本'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '测试文本');

        // processing 状态 (VAD 触发)
        stateController.add(CapsuleStateData.processing(text: '测试文本'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        // processing 状态也用 GradientTextFlowWithFade 或普通 Text
        expectTextInCapsule(tester, '测试文本');
      });

      testWidgets('processing -> idle 流转正确 (提交完成)', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        stateController.add(CapsuleStateData.processing(text: '提交中'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '提交中');

        stateController.add(CapsuleStateData.idle());
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextNotInCapsule(tester, '提交中');
      });
    });

    group('错误处理测试', () {
      testWidgets('AC9, AC10: Socket 断开时显示错误消息', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // Socket 错误
        stateController
            .add(CapsuleStateData.error(CapsuleErrorType.socketError));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        expect(find.text('Fcitx5 连接错误'), findsOneWidget);
      });

      testWidgets('AC11: 错误状态 3 秒后应能恢复到 idle (模拟自动隐藏)', (tester) async {
        // AC11: 错误状态 3 秒后自动隐藏
        // 注意: 3 秒延迟逻辑在 HotkeyController._handleError 中实现
        // 此测试验证 UI 层面能够正确响应状态从 error -> idle 的变化
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // 进入错误状态
        stateController
            .add(CapsuleStateData.error(CapsuleErrorType.socketError));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expect(find.text('Fcitx5 连接错误'), findsOneWidget);

        // 模拟 3 秒后 HotkeyController 发送 idle 状态
        // 实际场景中这由 HotkeyController 的 Future.delayed(3s) 触发
        stateController.add(CapsuleStateData.idle());
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        // 错误消息应该消失
        expect(find.text('Fcitx5 连接错误'), findsNothing);
      });

      testWidgets('音频设备错误显示正确消息', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        stateController
            .add(CapsuleStateData.error(CapsuleErrorType.audioInitFailed));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        expect(find.text('音频设备初始化失败'), findsOneWidget);
      });

      testWidgets('模型错误显示正确消息', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        stateController
            .add(CapsuleStateData.error(CapsuleErrorType.modelLoadFailed));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        expect(find.text('模型加载失败'), findsOneWidget);
      });

      testWidgets('错误状态后可恢复到 idle', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // 先进入错误状态
        stateController
            .add(CapsuleStateData.error(CapsuleErrorType.socketError));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expect(find.text('Fcitx5 连接错误'), findsOneWidget);

        // 恢复到 idle
        stateController.add(CapsuleStateData.idle());
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expect(find.text('Fcitx5 连接错误'), findsNothing);
      });
    });

    group('UI 状态绑定测试', () {
      testWidgets('CapsuleWidget 正确接收 stateData', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // 验证 CapsuleWidget 被渲染
        expect(find.byType(CapsuleWidget), findsOneWidget);
      });

      testWidgets('多次状态更新正确处理', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // 快速连续更新
        for (var i = 1; i <= 5; i++) {
          stateController.add(CapsuleStateData.listening(text: '文本$i'));
          await tester.pump();
          await tester.pump(const Duration(milliseconds: 50));
        }

        // 最终状态应该是最后一次更新
        expectTextInCapsule(tester, '文本5');
      });

      testWidgets('StreamBuilder 初始状态为 listening', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        // listening 状态 (无文本) 应显示 hint
        expect(find.text('正在聆听...'), findsOneWidget);
      });
    });

    group('完整业务流程测试', () {
      testWidgets('完整录音流程: idle -> listening -> processing -> idle',
          (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        // 1. 初始状态 listening (无文本，显示 hint)
        expect(find.text('正在聆听...'), findsOneWidget);

        // 2. 开始说话 -> listening (有文本)
        stateController.add(CapsuleStateData.listening(text: '你好'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '你好');

        // 3. 继续说话
        stateController.add(CapsuleStateData.listening(text: '你好世界'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '你好世界');

        // 4. VAD 触发或手动停止 -> processing
        stateController.add(CapsuleStateData.processing(text: '你好世界'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '你好世界');

        // 5. 提交完成 -> idle
        stateController.add(CapsuleStateData.idle());
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextNotInCapsule(tester, '你好世界');
      });

      testWidgets('录音中遇到错误的流程', (tester) async {
        await tester.pumpWidget(NextalkApp(
            stateController: stateController, modelManager: modelManager));
        await tester.pump();

        // 1. 开始录音
        stateController.add(CapsuleStateData.listening(text: '正在说话'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expectTextInCapsule(tester, '正在说话');

        // 2. 遇到错误 (如 Socket 断开)
        stateController
            .add(CapsuleStateData.error(CapsuleErrorType.socketError));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expect(find.text('Fcitx5 连接错误'), findsOneWidget);

        // 3. 错误超时后恢复
        stateController.add(CapsuleStateData.idle());
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expect(find.text('Fcitx5 连接错误'), findsNothing);
      });
    });
  });
}
