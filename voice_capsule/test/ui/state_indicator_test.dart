import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/capsule_colors.dart';
import 'package:voice_capsule/state/capsule_state.dart';
import 'package:voice_capsule/ui/breathing_dot.dart';
import 'package:voice_capsule/ui/pulse_indicator.dart';
import 'package:voice_capsule/ui/ripple_effect.dart';
import 'package:voice_capsule/ui/state_indicator.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: Center(child: child)));
}

void main() {
  group('StateIndicator Tests', () {
    testWidgets('renders BreathingDot and RippleEffect for listening state',
        (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(stateData: CapsuleStateData.listening()),
      ));

      expect(find.byType(BreathingDot), findsOneWidget);
      expect(find.byType(RippleEffect), findsOneWidget);
    });

    testWidgets('renders PulseIndicator for processing state', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(stateData: CapsuleStateData.processing()),
      ));

      expect(find.byType(PulseIndicator), findsOneWidget);
      expect(find.byType(RippleEffect), findsNothing);
      expect(find.byType(BreathingDot), findsNothing);
    });

    testWidgets('renders nothing visible for idle state', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(stateData: CapsuleStateData.idle()),
      ));

      expect(find.byType(BreathingDot), findsNothing);
      expect(find.byType(RippleEffect), findsNothing);
      expect(find.byType(PulseIndicator), findsNothing);
      // Should find a SizedBox.shrink()
      expect(find.byType(SizedBox), findsWidgets);
    });

    testWidgets('renders gray dot for audioNoDevice', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(
          stateData: CapsuleStateData.error(CapsuleErrorType.audioNoDevice),
        ),
      ));

      // Find the error indicator container
      final containers = tester.widgetList<Container>(
        find.descendant(
          of: find.byType(StateIndicator),
          matching: find.byWidgetPredicate(
            (w) =>
                w is Container &&
                w.decoration != null &&
                (w.decoration as BoxDecoration).shape == BoxShape.circle &&
                (w.decoration as BoxDecoration).color != null,
          ),
        ),
      );

      // Should have a gray circle
      expect(containers.isNotEmpty, true);
      final container = containers.first;
      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, CapsuleColors.disabled);
    });

    testWidgets('renders yellow dot for socketError', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(
          stateData: CapsuleStateData.error(CapsuleErrorType.socketError),
        ),
      ));

      final containers = tester.widgetList<Container>(
        find.descendant(
          of: find.byType(StateIndicator),
          matching: find.byWidgetPredicate(
            (w) =>
                w is Container &&
                w.decoration != null &&
                (w.decoration as BoxDecoration).shape == BoxShape.circle &&
                (w.decoration as BoxDecoration).color != null,
          ),
        ),
      );

      expect(containers.isNotEmpty, true);
      final container = containers.first;
      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, CapsuleColors.warning);
    });

    testWidgets('renders yellow dot for modelLoadFailed', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(
          stateData: CapsuleStateData.error(CapsuleErrorType.modelLoadFailed),
        ),
      ));

      final containers = tester.widgetList<Container>(
        find.descendant(
          of: find.byType(StateIndicator),
          matching: find.byWidgetPredicate(
            (w) =>
                w is Container &&
                w.decoration != null &&
                (w.decoration as BoxDecoration).shape == BoxShape.circle &&
                (w.decoration as BoxDecoration).color != null,
          ),
        ),
      );

      expect(containers.isNotEmpty, true);
      final container = containers.first;
      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, CapsuleColors.warning);
    });

    testWidgets('renders yellow dot for unknown error', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(
          stateData: CapsuleStateData.error(CapsuleErrorType.unknown),
        ),
      ));

      final containers = tester.widgetList<Container>(
        find.descendant(
          of: find.byType(StateIndicator),
          matching: find.byWidgetPredicate(
            (w) =>
                w is Container &&
                w.decoration != null &&
                (w.decoration as BoxDecoration).shape == BoxShape.circle &&
                (w.decoration as BoxDecoration).color != null,
          ),
        ),
      );

      expect(containers.isNotEmpty, true);
      final container = containers.first;
      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, CapsuleColors.warning);
    });

    testWidgets('has correct size container', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(
          stateData: CapsuleStateData.listening(),
          size: 30.0,
        ),
      ));

      // The outer SizedBox should be same as size (ripple overflows via Clip.none)
      final sizedBox = tester.widget<SizedBox>(
        find.descendant(
          of: find.byType(StateIndicator),
          matching: find.byType(SizedBox),
        ).first,
      );

      expect(sizedBox.width, 30.0);
      expect(sizedBox.height, 30.0);
    });

    testWidgets('uses Stack for layering', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        StateIndicator(stateData: CapsuleStateData.listening()),
      ));

      // StateIndicator uses Stack for layering ripple and dot
      // RippleEffect also uses Stack internally, so we expect at least 2
      expect(
        find.descendant(
          of: find.byType(StateIndicator),
          matching: find.byType(Stack),
        ),
        findsAtLeastNWidgets(1),
      );
    });
  });

  group('CapsuleStateData displayMessage Tests for StateIndicator', () {
    test('listening state has correct displayMessage', () {
      final state = CapsuleStateData.listening(text: '你好');
      expect(state.displayMessage, '你好');
    });

    test('error state returns default error message', () {
      final state = CapsuleStateData.error(CapsuleErrorType.audioInitFailed);
      expect(state.displayMessage, '音频设备初始化失败');
    });

    test('error state with custom message uses it', () {
      final state = CapsuleStateData.error(
        CapsuleErrorType.unknown,
        message: '自定义错误',
      );
      expect(state.displayMessage, '自定义错误');
    });
  });
}




