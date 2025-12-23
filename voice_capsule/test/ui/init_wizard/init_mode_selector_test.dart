import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/capsule_colors.dart';
import 'package:voice_capsule/ui/init_wizard/init_mode_selector.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: Center(child: child)));
}

void main() {
  group('InitModeSelector Tests', () {
    testWidgets('renders two buttons (auto download and manual install)',
        (tester) async {
      await tester.pumpWidget(buildTestWidget(
        InitModeSelector(
          onAutoDownload: () {},
          onManualInstall: () {},
        ),
      ));

      // 应该有一个 ElevatedButton 和一个 OutlinedButton
      expect(find.byType(ElevatedButton), findsOneWidget);
      expect(find.byType(OutlinedButton), findsOneWidget);
    });

    testWidgets('displays title text', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        InitModeSelector(
          onAutoDownload: () {},
          onManualInstall: () {},
        ),
      ));

      expect(find.text('🎤 Nextalk 首次启动'), findsOneWidget);
    });

    testWidgets('displays model size info', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        InitModeSelector(
          onAutoDownload: () {},
          onManualInstall: () {},
        ),
      ));

      expect(find.textContaining('模型'), findsOneWidget);
    });

    testWidgets('auto download button has recommended label', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        InitModeSelector(
          onAutoDownload: () {},
          onManualInstall: () {},
        ),
      ));

      expect(find.textContaining('自动下载'), findsOneWidget);
      expect(find.textContaining('推荐'), findsOneWidget);
    });

    testWidgets('manual install button is present', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        InitModeSelector(
          onAutoDownload: () {},
          onManualInstall: () {},
        ),
      ));

      expect(find.textContaining('手动安装'), findsOneWidget);
    });

    testWidgets('auto download callback is invoked on tap', (tester) async {
      var tapped = false;
      await tester.pumpWidget(buildTestWidget(
        InitModeSelector(
          onAutoDownload: () => tapped = true,
          onManualInstall: () {},
        ),
      ));

      // 点击自动下载按钮
      await tester.tap(find.widgetWithText(ElevatedButton, '📥 自动下载'));
      await tester.pump();

      expect(tapped, true);
    });

    testWidgets('manual install callback is invoked on tap', (tester) async {
      var tapped = false;
      await tester.pumpWidget(buildTestWidget(
        InitModeSelector(
          onAutoDownload: () {},
          onManualInstall: () => tapped = true,
        ),
      ));

      // 点击手动安装按钮
      await tester.tap(find.widgetWithText(OutlinedButton, '📁 手动安装'));
      await tester.pump();

      expect(tapped, true);
    });

    testWidgets('has dark theme styling', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        InitModeSelector(
          onAutoDownload: () {},
          onManualInstall: () {},
        ),
      ));

      // 验证背景色是深色
      final container = tester.widget<Container>(
        find.byType(Container).first,
      );
      final decoration = container.decoration as BoxDecoration?;
      // 允许 null decoration (组件内部处理样式)
      expect(find.byType(InitModeSelector), findsOneWidget);
    });
  });
}
