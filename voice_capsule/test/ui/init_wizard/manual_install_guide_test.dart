import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/ui/init_wizard/manual_install_guide.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: Center(child: child)));
}

void main() {
  group('ManualInstallGuide Tests', () {
    testWidgets('displays title', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () {},
          onOpenDirectory: () {},
          onVerifyModel: () {},
          onSwitchToAuto: () {},
        ),
      ));

      expect(find.textContaining('手动安装'), findsOneWidget);
    });

    testWidgets('displays step 1 download link', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () {},
          onOpenDirectory: () {},
          onVerifyModel: () {},
          onSwitchToAuto: () {},
        ),
      ));

      expect(find.textContaining('下载'), findsWidgets);
    });

    testWidgets('displays step 2 target path', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () {},
          onOpenDirectory: () {},
          onVerifyModel: () {},
          onSwitchToAuto: () {},
        ),
      ));

      expect(find.textContaining('解压'), findsOneWidget);
    });

    testWidgets('has copy link button', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () {},
          onOpenDirectory: () {},
          onVerifyModel: () {},
          onSwitchToAuto: () {},
        ),
      ));

      expect(find.textContaining('复制链接'), findsOneWidget);
    });

    testWidgets('has open directory button', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () {},
          onOpenDirectory: () {},
          onVerifyModel: () {},
          onSwitchToAuto: () {},
        ),
      ));

      expect(find.textContaining('打开目录'), findsOneWidget);
    });

    testWidgets('has verify model button', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () {},
          onOpenDirectory: () {},
          onVerifyModel: () {},
          onSwitchToAuto: () {},
        ),
      ));

      expect(find.textContaining('检测模型'), findsOneWidget);
    });

    testWidgets('has switch to auto button', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () {},
          onOpenDirectory: () {},
          onVerifyModel: () {},
          onSwitchToAuto: () {},
        ),
      ));

      expect(find.textContaining('自动下载'), findsOneWidget);
    });

    testWidgets('copy link callback works', (tester) async {
      var copied = false;
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () => copied = true,
          onOpenDirectory: () {},
          onVerifyModel: () {},
          onSwitchToAuto: () {},
        ),
      ));

      await tester.tap(find.textContaining('复制链接'));
      await tester.pump();

      expect(copied, true);
    });

    testWidgets('verify model callback works', (tester) async {
      var verified = false;
      await tester.pumpWidget(buildTestWidget(
        ManualInstallGuide(
          onCopyLink: () {},
          onOpenDirectory: () {},
          onVerifyModel: () => verified = true,
          onSwitchToAuto: () {},
        ),
      ));

      await tester.tap(find.textContaining('检测模型'));
      await tester.pump();

      expect(verified, true);
    });
  });
}
