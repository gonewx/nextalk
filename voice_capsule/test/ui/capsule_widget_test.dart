import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/capsule_colors.dart';
import 'package:voice_capsule/constants/window_constants.dart';
import 'package:voice_capsule/state/capsule_state.dart';
import 'package:voice_capsule/ui/capsule_widget.dart';
import 'package:voice_capsule/ui/capsule_text_preview.dart';
import 'package:voice_capsule/ui/cursor_blink.dart';
import 'package:voice_capsule/ui/state_indicator.dart';

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

    testWidgets('contains StateIndicator (Story 3-3)', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      // Story 3-3: 指示器现在使用 StateIndicator 组合组件
      // 查找圆形的红色指示器 (现在由 BreathingDot + RippleEffect 组成)
      final indicator = find.descendant(
        of: find.byType(CapsuleWidget),
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is Container &&
              widget.decoration is BoxDecoration &&
              (widget.decoration as BoxDecoration).shape == BoxShape.circle,
        ),
      );
      // 默认 listening 状态: BreathingDot(1) + RippleEffect(2 borders) = 至少 1 个
      expect(indicator, findsAtLeastNWidgets(1));
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

  // Story 3-3: 状态机与动画系统测试
  group('CapsuleWidget State Machine Tests (Story 3-3)', () {
    testWidgets('contains StateIndicator component', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      expect(find.byType(StateIndicator), findsOneWidget);
    });

    testWidgets('shows CursorBlink in default (listening) state', (tester) async {
      await tester.pumpWidget(buildTestWidget(const CapsuleWidget()));

      expect(find.byType(CursorBlink), findsOneWidget);
    });

    testWidgets('hides CursorBlink in processing state', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        CapsuleWidget(
          stateData: CapsuleStateData.processing(text: '处理中'),
        ),
      ));

      expect(find.byType(CursorBlink), findsNothing);
    });

    testWidgets('shows error message in error state', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        CapsuleWidget(
          stateData: CapsuleStateData.error(CapsuleErrorType.audioInitFailed),
        ),
      ));

      expect(find.text('音频设备初始化失败'), findsOneWidget);
    });

    testWidgets('uses processing style in processing state', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        CapsuleWidget(
          text: '处理中文本',
          stateData: CapsuleStateData.processing(text: '处理中文本'),
        ),
      ));

      final textWidget = tester.widget<Text>(find.text('处理中文本'));
      expect(textWidget.style?.color, CapsuleColors.textProcessing);
    });

    testWidgets('backward compatible when stateData is null', (tester) async {
      // 不传入 stateData 时应该使用默认的 listening 状态
      await tester.pumpWidget(buildTestWidget(
        const CapsuleWidget(text: '你好'),
      ));

      expect(find.byType(StateIndicator), findsOneWidget);
      expect(find.byType(CursorBlink), findsOneWidget);
      expect(find.text('你好'), findsOneWidget);
    });
  });

  group('CapsuleTextPreview Processing Style Tests (Story 3-3)', () {
    testWidgets('uses processing style when isProcessing is true', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleTextPreview(
          text: '处理中',
          isProcessing: true,
        ),
      ));

      final textWidget = tester.widget<Text>(find.byType(Text));
      expect(textWidget.style?.color, CapsuleColors.textProcessing);
    });

    testWidgets('processing style overrides hint style', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        const CapsuleTextPreview(
          text: '',
          showHint: true,
          hintText: '提示',
          isProcessing: true,
        ),
      ));

      final textWidget = tester.widget<Text>(find.byType(Text));
      // 处理中样式优先级高于提示样式
      expect(textWidget.style?.color, CapsuleColors.textProcessing);
    });
  });
}

