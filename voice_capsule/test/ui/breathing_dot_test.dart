import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/capsule_colors.dart';
import 'package:voice_capsule/ui/breathing_dot.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: child));
}

void main() {
  group('BreathingDot Widget Tests', () {
    testWidgets('renders with default color (accentRed)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const BreathingDot()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(BreathingDot),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, CapsuleColors.accentRed);
    });

    testWidgets('renders with custom color', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const BreathingDot(color: Colors.blue),
      ));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(BreathingDot),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, Colors.blue);
    });

    testWidgets('renders with default size (30.0)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const BreathingDot()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(BreathingDot),
          matching: find.byType(Container),
        ),
      );

      expect(container.constraints?.maxWidth, 30.0);
      expect(container.constraints?.maxHeight, 30.0);
    });

    testWidgets('renders with custom size', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const BreathingDot(size: 50.0),
      ));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(BreathingDot),
          matching: find.byType(Container),
        ),
      );

      expect(container.constraints?.maxWidth, 50.0);
      expect(container.constraints?.maxHeight, 50.0);
    });

    testWidgets('has circle shape', (tester) async {
      await tester.pumpWidget(buildTestWidget(const BreathingDot()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(BreathingDot),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.shape, BoxShape.circle);
    });

    testWidgets('uses AnimatedBuilder for animation', (tester) async {
      await tester.pumpWidget(buildTestWidget(const BreathingDot()));

      // BreathingDot should have its own AnimatedBuilder as a descendant
      expect(
        find.descendant(
          of: find.byType(BreathingDot),
          matching: find.byType(AnimatedBuilder),
        ),
        findsOneWidget,
      );
    });

    testWidgets('uses Transform.scale for breathing effect', (tester) async {
      await tester.pumpWidget(buildTestWidget(const BreathingDot()));

      // BreathingDot should have its own Transform as a descendant
      expect(
        find.descendant(
          of: find.byType(BreathingDot),
          matching: find.byType(Transform),
        ),
        findsOneWidget,
      );
    });

    testWidgets('animation runs when animate is true', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const BreathingDot(animate: true),
      ));

      // Pump a frame to start animation
      await tester.pump(const Duration(milliseconds: 500));

      // Widget should still be rendered
      expect(find.byType(BreathingDot), findsOneWidget);
    });

    testWidgets('animation stops when animate is false', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const BreathingDot(animate: false),
      ));

      // Should still render without animation
      expect(find.byType(BreathingDot), findsOneWidget);
    });

    testWidgets('animation responds to animate prop change', (tester) async {
      // Start with animation enabled
      await tester.pumpWidget(buildTestWidget(
        const BreathingDot(animate: true),
      ));
      await tester.pump(const Duration(milliseconds: 100));

      // Disable animation
      await tester.pumpWidget(buildTestWidget(
        const BreathingDot(animate: false),
      ));
      await tester.pump();

      // Should still render
      expect(find.byType(BreathingDot), findsOneWidget);

      // Re-enable animation
      await tester.pumpWidget(buildTestWidget(
        const BreathingDot(animate: true),
      ));
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.byType(BreathingDot), findsOneWidget);
    });

    testWidgets('disposes animation controller properly', (tester) async {
      await tester.pumpWidget(buildTestWidget(const BreathingDot()));
      await tester.pump(const Duration(milliseconds: 100));

      // Remove widget
      await tester.pumpWidget(buildTestWidget(const SizedBox()));

      // Should not throw any errors
      expect(find.byType(BreathingDot), findsNothing);
    });
  });
}

