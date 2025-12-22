import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/capsule_colors.dart';
import 'package:voice_capsule/constants/window_constants.dart';
import 'package:voice_capsule/ui/capsule_widget.dart';
import 'package:voice_capsule/ui/capsule_text_preview.dart';

// ⚠️ 注意: 这些测试专注于 Widget 渲染，不测试拖拽功能
// 拖拽功能需要 WindowService 环境，在集成测试中验证
// GestureDetector.onPanStart 调用 WindowService.startDragging()
// 在无窗口环境测试会静默失败 (WindowService 未初始化时返回)

/// 测试辅助函数 - 包装 Widget 用于测试
Widget buildTestWidget(Widget child) {
  return MaterialApp(
    home: Scaffold(body: child),
  );
}

void main() {
  group('CapsuleWidget Tests', () {
    testWidgets('has fixed height of 60px (AC1)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      // 使用更稳定的选择器 - 查找带 constraints 的 Container
      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(CapsuleWidget),
              matching: find.byWidgetPredicate(
                (widget) => widget is Container && widget.constraints != null,
              ),
            )
            .first,
      );
      // AC1: 高度固定 60px - 验证 min 和 max 都等于 capsuleHeight
      expect(container.constraints?.minHeight, WindowConstants.capsuleHeight);
      expect(container.constraints?.maxHeight, WindowConstants.capsuleHeight);
    });

    testWidgets('respects minWidth constraint', (tester) async {
      // AC1: 宽度 280-380px 自适应
      await tester.pumpWidget(buildTestWidget(
        const CapsuleWidget(text: 'A'), // 很短的文本
      ));

      // 验证 Container 的 BoxConstraints 设置正确
      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(CapsuleWidget),
              matching: find.byWidgetPredicate(
                (widget) => widget is Container && widget.constraints != null,
              ),
            )
            .first,
      );
      expect(container.constraints?.minWidth, WindowConstants.capsuleMinWidth);
      expect(container.constraints?.maxWidth, WindowConstants.capsuleWidth);
    });

    testWidgets('displays hint text when text is empty', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleWidget(
          text: '',
          showHint: true,
          hintText: '测试提示',
        ),
      ));

      expect(find.text('测试提示'), findsOneWidget);
    });

    testWidgets('displays actual text when provided', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleWidget(
          text: '你好世界',
          showHint: true,
        ),
      ));

      expect(find.text('你好世界'), findsOneWidget);
    });

    testWidgets('has correct decoration (background, radius)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      // 查找带 BoxDecoration 的 Container
      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(CapsuleWidget),
              matching: find.byWidgetPredicate(
                (widget) => widget is Container && widget.decoration != null,
              ),
            )
            .first,
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.color, CapsuleColors.background);
      expect(decoration.borderRadius,
          BorderRadius.circular(WindowConstants.capsuleRadius));
    });

    testWidgets('has correct border glow color', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(CapsuleWidget),
              matching: find.byWidgetPredicate(
                (widget) => widget is Container && widget.decoration != null,
              ),
            )
            .first,
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.border, isNotNull);
      final border = decoration.border as Border;
      expect(border.top.color, CapsuleColors.borderGlow);
    });

    testWidgets('has box shadow for floating effect', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(CapsuleWidget),
              matching: find.byWidgetPredicate(
                (widget) => widget is Container && widget.decoration != null,
              ),
            )
            .first,
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.boxShadow, isNotNull);
      expect(decoration.boxShadow!.isNotEmpty, true);
      expect(decoration.boxShadow!.first.color, CapsuleColors.shadow);
    });

    testWidgets('contains indicator placeholder', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      // 查找圆形的红色指示器
      final indicator = find.descendant(
        of: find.byType(CapsuleWidget),
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is Container &&
              widget.decoration is BoxDecoration &&
              (widget.decoration as BoxDecoration).shape == BoxShape.circle,
        ),
      );
      expect(indicator, findsOneWidget);
    });

    testWidgets('has correct horizontal padding (AC9)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      // 查找带 padding 的 Container (内容容器)
      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(CapsuleWidget),
              matching: find.byWidgetPredicate(
                (widget) => widget is Container && widget.padding != null,
              ),
            )
            .first,
      );

      // AC9: 内边距左右各 25px
      final padding = container.padding as EdgeInsets;
      expect(padding.left, 25.0);
      expect(padding.right, 25.0);
    });
  });

  group('CapsuleTextPreview Tests', () {
    testWidgets('uses primary style for actual text', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleTextPreview(text: '测试文本', showHint: false),
      ));

      final textWidget = tester.widget<Text>(find.byType(Text));
      expect(textWidget.style?.color, CapsuleColors.textWhite);
    });

    testWidgets('uses hint style for hint text', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleTextPreview(text: '', showHint: true, hintText: '提示'),
      ));

      final textWidget = tester.widget<Text>(find.byType(Text));
      expect(textWidget.style?.color, CapsuleColors.textHint);
    });

    testWidgets('has ellipsis overflow and single line', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleTextPreview(text: '这是一段非常长的文本用于测试省略功能'),
      ));

      final textWidget = tester.widget<Text>(find.byType(Text));
      expect(textWidget.overflow, TextOverflow.ellipsis);
      expect(textWidget.maxLines, 1);
    });

    testWidgets('displays hint when text is empty and showHint is true',
        (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleTextPreview(
          text: '',
          showHint: true,
          hintText: '自定义提示',
        ),
      ));

      expect(find.text('自定义提示'), findsOneWidget);
    });

    testWidgets('displays empty with primaryText style when showHint is false',
        (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleTextPreview(
          text: '',
          showHint: false,
        ),
      ));

      final textWidget = tester.widget<Text>(find.byType(Text));
      expect(textWidget.data, '');
      // 当 showHint=false 且 text 为空时，应使用 primaryText 样式 (白色)
      expect(textWidget.style?.color, CapsuleColors.textWhite);
    });
  });

  group('CapsuleColors Tests', () {
    test('background has correct RGBA values', () {
      // 使用新的 Color API 访问 RGBA 分量
      expect((CapsuleColors.background.r * 255).round(), 25);
      expect((CapsuleColors.background.g * 255).round(), 25);
      expect((CapsuleColors.background.b * 255).round(), 25);
      expect(CapsuleColors.background.a, closeTo(0.95, 0.01));
    });

    test('accentRed has correct hex value', () {
      expect(CapsuleColors.accentRed, const Color(0xFFFF4757));
    });

    test('textWhite is pure white', () {
      expect(CapsuleColors.textWhite, const Color(0xFFFFFFFF));
    });

    test('textHint has correct hex value', () {
      expect(CapsuleColors.textHint, const Color(0xFFA4B0BE));
    });

    test('borderGlow has correct RGBA values', () {
      expect((CapsuleColors.borderGlow.r * 255).round(), 255);
      expect((CapsuleColors.borderGlow.g * 255).round(), 255);
      expect((CapsuleColors.borderGlow.b * 255).round(), 255);
      expect(CapsuleColors.borderGlow.a, closeTo(0.2, 0.01));
    });

    test('shadow has correct RGBA values', () {
      expect((CapsuleColors.shadow.r * 255).round(), 0);
      expect((CapsuleColors.shadow.g * 255).round(), 0);
      expect((CapsuleColors.shadow.b * 255).round(), 0);
      expect(CapsuleColors.shadow.a, closeTo(0.3, 0.01));
    });
  });

  group('CapsuleTextStyles Tests', () {
    test('primaryText has correct properties', () {
      expect(CapsuleTextStyles.primaryText.color, CapsuleColors.textWhite);
      expect(CapsuleTextStyles.primaryText.fontSize, 18.0);
      expect(CapsuleTextStyles.primaryText.fontWeight, FontWeight.w500);
    });

    test('hintText has correct properties', () {
      expect(CapsuleTextStyles.hintText.color, CapsuleColors.textHint);
      expect(CapsuleTextStyles.hintText.fontSize, 18.0);
      expect(CapsuleTextStyles.hintText.fontWeight, FontWeight.w500);
    });

    test('processingText has correct properties', () {
      expect(
          CapsuleTextStyles.processingText.color, CapsuleColors.textProcessing);
      expect(CapsuleTextStyles.processingText.fontSize, 18.0);
      expect(CapsuleTextStyles.processingText.fontWeight, FontWeight.w500);
    });
  });
}
