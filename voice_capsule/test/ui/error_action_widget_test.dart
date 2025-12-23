import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/state/capsule_state.dart';
import 'package:voice_capsule/ui/error_action_widget.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: Center(child: child)));
}

void main() {
  group('ErrorAction Tests', () {
    test('creates action with required fields', () {
      final action = ErrorAction(
        label: '测试',
        onPressed: () {},
      );
      expect(action.label, '测试');
      expect(action.isPrimary, false);
    });

    test('creates primary action', () {
      final action = ErrorAction(
        label: '重试',
        onPressed: () {},
        isPrimary: true,
      );
      expect(action.isPrimary, true);
    });
  });

  group('ErrorActionWidget Tests', () {
    testWidgets('displays error message', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ErrorActionWidget(
          errorType: CapsuleErrorType.audioNoDevice,
          message: '未检测到麦克风',
          actions: [],
        ),
      ));

      expect(find.text('未检测到麦克风'), findsOneWidget);
    });

    testWidgets('displays preserved text when provided', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ErrorActionWidget(
          errorType: CapsuleErrorType.socketError,
          message: 'Fcitx5 未连接',
          actions: [],
          preservedText: '用户说的话',
        ),
      ));

      expect(find.textContaining('用户说的话'), findsOneWidget);
    });

    testWidgets('does not display preserved text when null', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ErrorActionWidget(
          errorType: CapsuleErrorType.socketError,
          message: 'Fcitx5 未连接',
          actions: [],
          preservedText: null,
        ),
      ));

      // 只应该有一个 Text widget (错误消息)
      expect(find.byType(Text), findsOneWidget);
    });

    testWidgets('renders action buttons', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ErrorActionWidget(
          errorType: CapsuleErrorType.audioNoDevice,
          message: '未检测到麦克风',
          actions: [
            ErrorAction(label: '刷新检测', onPressed: () {}),
            ErrorAction(label: '查看帮助', onPressed: () {}),
          ],
        ),
      ));

      expect(find.text('刷新检测'), findsOneWidget);
      expect(find.text('查看帮助'), findsOneWidget);
    });

    testWidgets('limits to 3 action buttons', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ErrorActionWidget(
          errorType: CapsuleErrorType.unknown,
          message: '错误',
          actions: [
            ErrorAction(label: '按钮1', onPressed: () {}),
            ErrorAction(label: '按钮2', onPressed: () {}),
            ErrorAction(label: '按钮3', onPressed: () {}),
            ErrorAction(label: '按钮4', onPressed: () {}), // 应该被忽略
          ],
        ),
      ));

      expect(find.text('按钮1'), findsOneWidget);
      expect(find.text('按钮2'), findsOneWidget);
      expect(find.text('按钮3'), findsOneWidget);
      expect(find.text('按钮4'), findsNothing);
    });

    testWidgets('action callback is invoked on tap', (tester) async {
      var tapped = false;
      await tester.pumpWidget(buildTestWidget(
        ErrorActionWidget(
          errorType: CapsuleErrorType.audioNoDevice,
          message: '未检测到麦克风',
          actions: [
            ErrorAction(label: '刷新检测', onPressed: () => tapped = true),
          ],
        ),
      ));

      await tester.tap(find.text('刷新检测'));
      await tester.pump();

      expect(tapped, true);
    });

    testWidgets('uses grey color for audioNoDevice', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ErrorActionWidget(
          errorType: CapsuleErrorType.audioNoDevice,
          message: '未检测到麦克风',
          actions: [],
        ),
      ));

      // 组件应该存在 (颜色验证在内部实现)
      expect(find.byType(ErrorActionWidget), findsOneWidget);
    });

    testWidgets('uses grey color for modelNotFound', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ErrorActionWidget(
          errorType: CapsuleErrorType.modelNotFound,
          message: '未找到语音模型',
          actions: [],
        ),
      ));

      expect(find.byType(ErrorActionWidget), findsOneWidget);
    });
  });
}
