import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/app/nextalk_app.dart';
import 'package:voice_capsule/state/capsule_state.dart';
import 'package:voice_capsule/ui/capsule_widget.dart';

void main() {
  group('NextalkApp', () {
    late StreamController<CapsuleStateData> stateController;

    setUp(() {
      stateController = StreamController<CapsuleStateData>.broadcast();
    });

    tearDown(() async {
      await stateController.close();
    });

    testWidgets('应该正确渲染 CapsuleWidget', (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.byType(CapsuleWidget), findsOneWidget);
    });

    testWidgets('初始状态应该是 listening (便于开发调试)', (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      // listening 状态 (无文本) 应该显示 hint
      expect(find.text('正在聆听...'), findsOneWidget);
    });

    testWidgets('listening 状态 (无文本) 应该显示 hint', (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
      await tester.pump(); // 首帧

      stateController.add(CapsuleStateData.listening());
      await tester.pump(); // 等待 StreamBuilder 更新
      await tester.pump(const Duration(milliseconds: 100)); // 等待动画第一帧

      expect(find.text('正在聆听...'), findsOneWidget);
    });

    testWidgets('listening 状态 (有文本) 应该显示识别文本', (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
      await tester.pump();

      stateController.add(CapsuleStateData.listening(text: '你好'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('你好'), findsOneWidget);
    });

    testWidgets('processing 状态应该继续显示文本', (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
      await tester.pump();

      stateController.add(CapsuleStateData.processing(text: '你好世界'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('你好世界'), findsOneWidget);
    });

    testWidgets('error 状态 (socketError) 应该显示错误消息',
        (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
      await tester.pump();

      stateController
          .add(CapsuleStateData.error(CapsuleErrorType.socketError));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Fcitx5 连接错误'), findsOneWidget);
    });

    testWidgets('error 状态 (audioInitFailed) 应该显示错误消息',
        (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
      await tester.pump();

      stateController
          .add(CapsuleStateData.error(CapsuleErrorType.audioInitFailed));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('音频设备初始化失败'), findsOneWidget);
    });

    testWidgets('状态流转: idle -> listening -> processing -> idle',
        (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
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
      expect(find.text('你好'), findsOneWidget);

      // listening -> processing
      stateController.add(CapsuleStateData.processing(text: '你好世界'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.text('你好世界'), findsOneWidget);

      // processing -> idle
      stateController.add(CapsuleStateData.idle());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      // idle 状态文本清空
      expect(find.text('你好世界'), findsNothing);
    });

    testWidgets('StreamBuilder 应该自动管理订阅生命周期', (tester) async {
      await tester.pumpWidget(NextalkApp(stateController: stateController));
      await tester.pump();

      // 发送多个状态更新，确保 StreamBuilder 正常工作
      stateController.add(CapsuleStateData.listening(text: '测试1'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.text('测试1'), findsOneWidget);

      stateController.add(CapsuleStateData.listening(text: '测试2'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.text('测试2'), findsOneWidget);
    });
  });
}
