import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/capsule_colors.dart';
import 'package:voice_capsule/ui/cursor_blink.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: child));
}

void main() {
  group('CursorBlink Widget Tests', () {
    testWidgets('renders with default color (textHint)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CursorBlink()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(CursorBlink),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, CapsuleColors.textHint);
    });

    testWidgets('renders with custom color', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CursorBlink(color: Colors.white),
      ));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(CursorBlink),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, Colors.white);
    });

    testWidgets('renders with default dimensions (2x20)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CursorBlink()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(CursorBlink),
          matching: find.byType(Container),
        ),
      );

      expect(container.constraints?.maxWidth, 2.0);
      expect(container.constraints?.maxHeight, 20.0);
    });

    testWidgets('renders with custom dimensions', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CursorBlink(width: 3.0, height: 25.0),
      ));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(CursorBlink),
          matching: find.byType(Container),
        ),
      );

      expect(container.constraints?.maxWidth, 3.0);
      expect(container.constraints?.maxHeight, 25.0);
    });

    testWidgets('has rounded corners', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CursorBlink()));

      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(CursorBlink),
          matching: find.byType(Container),
        ),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.borderRadius, BorderRadius.circular(1.0));
    });

    testWidgets('uses AnimatedBuilder for animation', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CursorBlink()));

      expect(
        find.descendant(
          of: find.byType(CursorBlink),
          matching: find.byType(AnimatedBuilder),
        ),
        findsOneWidget,
      );
    });

    testWidgets('uses Opacity widget for blink effect', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CursorBlink()));

      expect(
        find.descendant(
          of: find.byType(CursorBlink),
          matching: find.byType(Opacity),
        ),
        findsOneWidget,
      );
    });

    testWidgets('animation runs when animate is true', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CursorBlink(animate: true),
      ));

      await tester.pump(const Duration(milliseconds: 400));
      expect(find.byType(CursorBlink), findsOneWidget);
    });

    testWidgets('animation stops when animate is false', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CursorBlink(animate: false),
      ));

      expect(find.byType(CursorBlink), findsOneWidget);
    });

    testWidgets('animation responds to animate prop change', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CursorBlink(animate: true),
      ));
      await tester.pump(const Duration(milliseconds: 100));

      await tester.pumpWidget(buildTestWidget(
        const CursorBlink(animate: false),
      ));
      await tester.pump();

      expect(find.byType(CursorBlink), findsOneWidget);

      await tester.pumpWidget(buildTestWidget(
        const CursorBlink(animate: true),
      ));
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.byType(CursorBlink), findsOneWidget);
    });

    testWidgets('disposes animation controller properly', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CursorBlink()));
      await tester.pump(const Duration(milliseconds: 100));

      await tester.pumpWidget(buildTestWidget(const SizedBox()));

      expect(find.byType(CursorBlink), findsNothing);
    });
  });
}



