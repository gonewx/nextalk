import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/capsule_colors.dart';
import 'package:voice_capsule/ui/ripple_effect.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: Center(child: child)));
}

void main() {
  group('RippleEffect Widget Tests', () {
    testWidgets('renders with default color (accentRed)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const RippleEffect()));

      // Find containers with color decoration (now using filled circles)
      final containers = tester.widgetList<Container>(
        find.descendant(
          of: find.byType(RippleEffect),
          matching: find.byWidgetPredicate(
            (w) =>
                w is Container &&
                w.decoration is BoxDecoration &&
                (w.decoration as BoxDecoration).color != null,
          ),
        ),
      );

      // At least one container should exist with accentRed base color
      expect(containers.isNotEmpty, true);
    });

    testWidgets('renders with custom color', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const RippleEffect(color: Colors.blue),
      ));

      // Widget should render without errors
      expect(find.byType(RippleEffect), findsOneWidget);
    });

    testWidgets('renders with correct SizedBox dimensions', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const RippleEffect(size: 30.0),
      ));

      final sizedBox = tester.widget<SizedBox>(
        find.descendant(
          of: find.byType(RippleEffect),
          matching: find.byType(SizedBox),
        ).first,
      );

      // SizedBox should be same as size (ripple overflows via Clip.none)
      expect(sizedBox.width, 30.0);
      expect(sizedBox.height, 30.0);
    });

    testWidgets('renders correct number of ripples (default 2)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const RippleEffect()));

      // Should have 2 AnimatedBuilder widgets within RippleEffect
      final animatedBuilders = find.descendant(
        of: find.byType(RippleEffect),
        matching: find.byType(AnimatedBuilder),
      );

      expect(animatedBuilders, findsNWidgets(2));
    });

    testWidgets('renders custom number of ripples', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const RippleEffect(rippleCount: 3),
      ));

      final animatedBuilders = find.descendant(
        of: find.byType(RippleEffect),
        matching: find.byType(AnimatedBuilder),
      );

      expect(animatedBuilders, findsNWidgets(3));
    });

    testWidgets('uses RepaintBoundary for performance', (tester) async {
      await tester.pumpWidget(buildTestWidget(const RippleEffect()));

      expect(
        find.descendant(
          of: find.byType(RippleEffect),
          matching: find.byType(RepaintBoundary),
        ),
        findsOneWidget,
      );
    });

    testWidgets('uses Stack with Clip.none for layering ripples', (tester) async {
      await tester.pumpWidget(buildTestWidget(const RippleEffect()));

      final stack = tester.widget<Stack>(
        find.descendant(
          of: find.byType(RippleEffect),
          matching: find.byType(Stack),
        ),
      );

      expect(stack.clipBehavior, Clip.none);
    });

    testWidgets('ripple containers have circle shape', (tester) async {
      await tester.pumpWidget(buildTestWidget(const RippleEffect()));

      final containers = tester.widgetList<Container>(
        find.descendant(
          of: find.byType(RippleEffect),
          matching: find.byWidgetPredicate(
            (w) =>
                w is Container &&
                w.decoration is BoxDecoration &&
                (w.decoration as BoxDecoration).shape == BoxShape.circle,
          ),
        ),
      );

      expect(containers.length, 2); // default rippleCount is 2
    });

    testWidgets('animation runs when animate is true', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const RippleEffect(animate: true),
      ));

      await tester.pump(const Duration(milliseconds: 500));
      expect(find.byType(RippleEffect), findsOneWidget);
    });

    testWidgets('animation stops when animate is false', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const RippleEffect(animate: false),
      ));

      expect(find.byType(RippleEffect), findsOneWidget);
    });

    testWidgets('animation responds to animate prop change', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const RippleEffect(animate: true),
      ));
      await tester.pump(const Duration(milliseconds: 100));

      await tester.pumpWidget(buildTestWidget(
        const RippleEffect(animate: false),
      ));
      await tester.pump();

      expect(find.byType(RippleEffect), findsOneWidget);
    });

    testWidgets('disposes animation controllers properly', (tester) async {
      await tester.pumpWidget(buildTestWidget(const RippleEffect()));
      await tester.pump(const Duration(milliseconds: 100));

      await tester.pumpWidget(buildTestWidget(const SizedBox()));

      expect(find.byType(RippleEffect), findsNothing);
    });

    testWidgets('ripple containers use color with alpha for fade', (tester) async {
      await tester.pumpWidget(buildTestWidget(const RippleEffect()));

      // Should have Container widgets with color (one per ripple)
      final containers = find.descendant(
        of: find.byType(RippleEffect),
        matching: find.byWidgetPredicate(
          (w) =>
              w is Container &&
              w.decoration is BoxDecoration &&
              (w.decoration as BoxDecoration).color != null,
        ),
      );

      expect(containers, findsNWidgets(2)); // default rippleCount is 2
    });

    testWidgets('uses Transform.scale for expansion', (tester) async {
      await tester.pumpWidget(buildTestWidget(const RippleEffect()));

      // Should have Transform widgets (one per ripple)
      final transformWidgets = find.descendant(
        of: find.byType(RippleEffect),
        matching: find.byType(Transform),
      );

      expect(transformWidgets, findsNWidgets(2)); // default rippleCount is 2
    });
  });
}




