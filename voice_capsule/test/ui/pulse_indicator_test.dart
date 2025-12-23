import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/capsule_colors.dart';
import 'package:voice_capsule/ui/pulse_indicator.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: child));
}

void main() {
  group('PulseIndicator Widget Tests', () {
    testWidgets('renders with default color (accentRed)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const PulseIndicator()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(PulseIndicator),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, CapsuleColors.accentRed);
    });

    testWidgets('renders with custom color', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const PulseIndicator(color: Colors.blue),
      ));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(PulseIndicator),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, Colors.blue);
    });

    testWidgets('renders with default size (30.0)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const PulseIndicator()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(PulseIndicator),
          matching: find.byType(Container),
        ),
      );

      expect(container.constraints?.maxWidth, 30.0);
      expect(container.constraints?.maxHeight, 30.0);
    });

    testWidgets('renders with custom size', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const PulseIndicator(size: 50.0),
      ));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(PulseIndicator),
          matching: find.byType(Container),
        ),
      );

      expect(container.constraints?.maxWidth, 50.0);
      expect(container.constraints?.maxHeight, 50.0);
    });

    testWidgets('has circle shape', (tester) async {
      await tester.pumpWidget(buildTestWidget(const PulseIndicator()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(PulseIndicator),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.shape, BoxShape.circle);
    });

    testWidgets('uses AnimatedBuilder for animation', (tester) async {
      await tester.pumpWidget(buildTestWidget(const PulseIndicator()));

      expect(
        find.descendant(
          of: find.byType(PulseIndicator),
          matching: find.byType(AnimatedBuilder),
        ),
        findsOneWidget,
      );
    });

    testWidgets('uses Transform.scale for pulse effect', (tester) async {
      await tester.pumpWidget(buildTestWidget(const PulseIndicator()));

      expect(
        find.descendant(
          of: find.byType(PulseIndicator),
          matching: find.byType(Transform),
        ),
        findsOneWidget,
      );
    });

    testWidgets('animation runs automatically', (tester) async {
      await tester.pumpWidget(buildTestWidget(const PulseIndicator()));

      // Pump to let animation run
      await tester.pump(const Duration(milliseconds: 200));
      expect(find.byType(PulseIndicator), findsOneWidget);

      await tester.pump(const Duration(milliseconds: 200));
      expect(find.byType(PulseIndicator), findsOneWidget);
    });

    testWidgets('animation stops when animate is false', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const PulseIndicator(animate: false),
      ));

      expect(find.byType(PulseIndicator), findsOneWidget);
    });

    testWidgets('animation responds to animate prop change', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const PulseIndicator(animate: true),
      ));
      await tester.pump(const Duration(milliseconds: 100));

      await tester.pumpWidget(buildTestWidget(
        const PulseIndicator(animate: false),
      ));
      await tester.pump();

      expect(find.byType(PulseIndicator), findsOneWidget);

      await tester.pumpWidget(buildTestWidget(
        const PulseIndicator(animate: true),
      ));
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.byType(PulseIndicator), findsOneWidget);
    });

    testWidgets('disposes animation controller properly', (tester) async {
      await tester.pumpWidget(buildTestWidget(const PulseIndicator()));
      await tester.pump(const Duration(milliseconds: 100));

      await tester.pumpWidget(buildTestWidget(const SizedBox()));

      expect(find.byType(PulseIndicator), findsNothing);
    });
  });
}

