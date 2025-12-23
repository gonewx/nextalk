import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/utils/clipboard_helper.dart';

void main() {
  group('ClipboardHelper Tests', () {
    TestWidgetsFlutterBinding.ensureInitialized();

    setUp(() {
      // 设置 mock clipboard
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
        SystemChannels.platform,
        (MethodCall methodCall) async {
          if (methodCall.method == 'Clipboard.setData') {
            return null;
          }
          if (methodCall.method == 'Clipboard.getData') {
            return <String, dynamic>{'text': '测试文本'};
          }
          return null;
        },
      );
    });

    tearDown(() {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(SystemChannels.platform, null);
    });

    test('copyText returns true for non-empty text', () async {
      final result = await ClipboardHelper.copyText('你好世界');
      expect(result, true);
    });

    test('copyText returns false for empty text', () async {
      final result = await ClipboardHelper.copyText('');
      expect(result, false);
    });

    test('getText returns text from clipboard', () async {
      final text = await ClipboardHelper.getText();
      expect(text, '测试文本');
    });
  });
}
