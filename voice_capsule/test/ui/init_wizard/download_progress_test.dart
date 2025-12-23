import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/model_manager.dart';
import 'package:voice_capsule/state/init_state.dart';
import 'package:voice_capsule/ui/init_wizard/download_progress.dart';

Widget buildTestWidget(Widget child) {
  return MaterialApp(home: Scaffold(body: Center(child: child)));
}

void main() {
  group('DownloadProgress Tests', () {
    testWidgets('displays progress percentage', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.downloading(
            progress: 0.45,
            downloaded: 68 * 1024 * 1024,
            total: 150 * 1024 * 1024,
          ),
          onSwitchToManual: () {},
          onCancel: () {},
        ),
      ));

      expect(find.textContaining('45'), findsOneWidget);
    });

    testWidgets('displays download size', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.downloading(
            progress: 0.45,
            downloaded: 68 * 1024 * 1024,
            total: 150 * 1024 * 1024,
          ),
          onSwitchToManual: () {},
          onCancel: () {},
        ),
      ));

      expect(find.textContaining('68MB'), findsOneWidget);
      expect(find.textContaining('150MB'), findsOneWidget);
    });

    testWidgets('has progress indicator', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.downloading(
            progress: 0.45,
            downloaded: 68 * 1024 * 1024,
            total: 150 * 1024 * 1024,
          ),
          onSwitchToManual: () {},
          onCancel: () {},
        ),
      ));

      expect(find.byType(LinearProgressIndicator), findsOneWidget);
    });

    testWidgets('has switch to manual button', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.downloading(
            progress: 0.45,
            downloaded: 68 * 1024 * 1024,
            total: 150 * 1024 * 1024,
          ),
          onSwitchToManual: () {},
          onCancel: () {},
        ),
      ));

      expect(find.textContaining('手动安装'), findsOneWidget);
    });

    testWidgets('has cancel button', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.downloading(
            progress: 0.45,
            downloaded: 68 * 1024 * 1024,
            total: 150 * 1024 * 1024,
          ),
          onSwitchToManual: () {},
          onCancel: () {},
        ),
      ));

      expect(find.textContaining('取消'), findsOneWidget);
    });

    testWidgets('switch to manual callback works', (tester) async {
      var switched = false;
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.downloading(
            progress: 0.45,
            downloaded: 68 * 1024 * 1024,
            total: 150 * 1024 * 1024,
          ),
          onSwitchToManual: () => switched = true,
          onCancel: () {},
        ),
      ));

      await tester.tap(find.textContaining('手动安装'));
      await tester.pump();

      expect(switched, true);
    });

    testWidgets('cancel callback works', (tester) async {
      var cancelled = false;
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.downloading(
            progress: 0.45,
            downloaded: 68 * 1024 * 1024,
            total: 150 * 1024 * 1024,
          ),
          onSwitchToManual: () {},
          onCancel: () => cancelled = true,
        ),
      ));

      await tester.tap(find.textContaining('取消'));
      await tester.pump();

      expect(cancelled, true);
    });

    testWidgets('shows retry button on error', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.error(ModelError.networkError),
          onSwitchToManual: () {},
          onCancel: () {},
          onRetry: () {},
        ),
      ));

      expect(find.textContaining('重试'), findsOneWidget);
    });

    testWidgets('shows error message on error', (tester) async {
      await tester.pumpWidget(buildTestWidget(
        DownloadProgress(
          state: InitStateData.error(ModelError.networkError),
          onSwitchToManual: () {},
          onCancel: () {},
          onRetry: () {},
        ),
      ));

      expect(find.textContaining('网络错误'), findsOneWidget);
    });
  });
}
