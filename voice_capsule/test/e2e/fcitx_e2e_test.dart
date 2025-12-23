// voice_capsule/test/e2e/fcitx_e2e_test.dart
//
// 端到端测试脚本 - 需要在桌面环境中手动运行
// 前置条件:
//   1. Fcitx5 已安装并运行
//   2. Nextalk 插件已安装 (scripts/install_addon.sh --user)
//   3. 打开一个文本编辑器（如 gedit）并获取焦点
//
// 运行方式:
//   cd voice_capsule && dart run test/e2e/fcitx_e2e_test.dart
//

import 'dart:io';
import 'package:voice_capsule/services/fcitx_client.dart';

Future<void> main() async {
  print('=== Nextalk Fcitx5 Client E2E Test ===\n');

  // 检查 Socket 是否存在
  final xdgRuntimeDir = Platform.environment['XDG_RUNTIME_DIR'];
  if (xdgRuntimeDir == null) {
    print('[ERROR] XDG_RUNTIME_DIR not set. Are you in a desktop session?');
    exit(1);
  }

  final socketPath = '$xdgRuntimeDir/nextalk-fcitx5.sock';
  if (!await File(socketPath).exists()) {
    print('[ERROR] Socket not found: $socketPath');
    print('Make sure:');
    print('  1. Fcitx5 is running');
    print(
        '  2. Nextalk addon is installed (run: scripts/install_addon.sh --user)');
    print('  3. Restart Fcitx5 (fcitx5 -r)');
    exit(1);
  }

  print('[OK] Socket found: $socketPath\n');

  final client = FcitxClient();

  try {
    print('[1/3] Connecting to Fcitx5...');
    await client.connect();
    print('[OK] Connected! State: ${client.state}\n');

    print('[2/3] Sending test text...');
    print('>>> Please focus on a text editor (gedit, kate, etc.) NOW');
    print('>>> Text will be sent in 3 seconds...');
    await Future.delayed(Duration(seconds: 3));

    const testText = '你好世界 Hello World! 测试成功 ✓';
    await client.sendText(testText);
    print('[OK] Text sent: "$testText"\n');

    print('[3/3] Check the text editor for the injected text.');
    print('\n=== E2E Test Complete ===');
    print('If you see "$testText" in your editor, the test passed!');
  } on FcitxError catch (e) {
    print('[ERROR] FcitxError: ${e.localizedMessage}');
    exit(1);
  } catch (e) {
    print('[ERROR] Unexpected error: $e');
    exit(1);
  } finally {
    await client.dispose();
  }
}
