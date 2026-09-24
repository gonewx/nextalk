import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/cancel_key_service.dart';

/// CancelKeyService 标记文件契约测试。
///
/// Fcitx5 插件只在标记文件存在且其中 PID 存活时才吞掉 Esc，
/// 因此"录音开始写入、结束删除、内容为本进程 PID"必须有回归护栏：
/// 漏删会让 Esc 在录音结束后仍被吞，写错 PID 则 Esc 取消完全失效。
void main() {
  late Directory tmpDir;
  late String markerPath;

  setUp(() async {
    tmpDir = await Directory.systemTemp.createTemp('nextalk_cancel_test_');
    markerPath = '${tmpDir.path}/nextalk-recording';
    // 隔离到临时路径，绝不碰用户正在运行的实例的标记文件
    CancelKeyService.markerPathOverride = markerPath;
    CancelKeyService.gnomeEnabled = false;
  });

  tearDown(() async {
    CancelKeyService.instance.disarm();
    CancelKeyService.markerPathOverride = null;
    CancelKeyService.gnomeEnabled = true;
    await tmpDir.delete(recursive: true);
  });

  test('arm 写入本进程 PID，disarm 删除标记', () {
    final service = CancelKeyService.instance;

    service.arm();
    expect(service.isArmed, isTrue);
    expect(File(markerPath).readAsStringSync().trim(), '$pid');

    service.disarm();
    expect(service.isArmed, isFalse);
    expect(File(markerPath).existsSync(), isFalse);
  });

  test('disarm 幂等', () {
    CancelKeyService.instance.disarm();
    CancelKeyService.instance.disarm();
    expect(File(markerPath).existsSync(), isFalse);
  });

  test('cleanupStale 删除异常退出残留的标记', () {
    File(markerPath).writeAsStringSync('999999\n');
    CancelKeyService.instance.cleanupStale();
    expect(File(markerPath).existsSync(), isFalse);
  });
}
