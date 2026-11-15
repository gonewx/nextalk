import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:voice_capsule/services/update_service.dart';

const deb = UpdateTarget('deb', 'amd64', '/usr/bin/apt-get');
const rpm = UpdateTarget('rpm', 'x86_64', '/usr/bin/dnf');
final bytes = utf8.encode('verified test package');
Map<String, dynamic> releaseJson({bool rpmPackage = false}) {
  final name =
      rpmPackage ? 'nextalk-0.5.0-1.x86_64.rpm' : 'nextalk_0.5.0-1_amd64.deb';
  return {
    'tag_name': 'v0.5.0',
    'draft': false,
    'prerelease': false,
    'body': '更新说明',
    'assets': [
      {
        'name': name,
        'browser_download_url':
            'https://github.com/gonewx/nextalk/releases/download/v0.5.0/$name',
        'size': bytes.length,
        'digest': 'sha256:${sha256.convert(bytes)}'
      }
    ],
  };
}

class FakeAdapter implements HttpClientAdapter {
  Map<String, dynamic> json = releaseJson();
  List<int> package = bytes;
  int status = 200;
  int calls = 0;
  Completer<void>? gate;
  @override
  Future<ResponseBody> fetch(RequestOptions options,
      Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    calls++;
    if (gate != null) await gate!.future;
    final api = options.uri.host == 'api.github.com';
    return ResponseBody.fromBytes(
        api ? utf8.encode(jsonEncode(json)) : package, status,
        headers: {
          Headers.contentTypeHeader: [
            api ? 'application/json' : 'application/octet-stream'
          ],
          if (!api) Headers.contentLengthHeader: ['${package.length}']
        });
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('版本按数字比较，拒绝开发版与预发布', () {
    expect(compareReleaseVersions('v0.10.0', '0.9.9'), greaterThan(0));
    expect(compareReleaseVersions('0.4.1', '0.4.1+1'), 0);
    expect(compareReleaseVersions('0.4.0', '0.4.1'), lessThan(0));
    for (final v in ['dev', '0.5.0-rc1', 'bad', '00.5.0']) {
      expect(compareReleaseVersions(v, '0.4.1'), isNull);
    }
  });
  test('DEB 与 RPM 精确匹配版本和架构', () {
    expect(
        UpdateRelease.parse(releaseJson(), '0.4.1', deb)!.canInstall, isTrue);
    expect(
        UpdateRelease.parse(releaseJson(rpmPackage: true), '0.4.1', rpm)!
            .canInstall,
        isTrue);
    expect(
        UpdateRelease.parse(releaseJson(), '0.4.1', rpm)!.canInstall, isFalse);
    expect(
        UpdateRelease.parse(releaseJson(), '0.4.1', null)!.canInstall, isFalse);
  });
  test('拒绝草稿、预发布、相同版本和降级', () {
    for (final key in ['draft', 'prerelease']) {
      expect(UpdateRelease.parse(releaseJson()..[key] = true, '0.4.1', deb),
          isNull);
    }
    expect(UpdateRelease.parse(releaseJson(), '0.5.0', deb), isNull);
    expect(UpdateRelease.parse(releaseJson(), '1.0.0', deb), isNull);
  });
  test('拒绝外部下载地址、错版本和缺失摘要', () {
    for (final url in [
      'http://github.com/gonewx/nextalk/releases/download/v0.5.0/nextalk_0.5.0-1_amd64.deb',
      'https://evil.test/package.deb',
      'https://github.com/other/nextalk/releases/download/v0.5.0/nextalk_0.5.0-1_amd64.deb',
      'https://github.com/gonewx/nextalk/releases/download/v0.6.0/nextalk_0.5.0-1_amd64.deb'
    ]) {
      final json = releaseJson();
      json['assets'][0]['browser_download_url'] = url;
      expect(UpdateRelease.parse(json, '0.4.1', deb)!.canInstall, isFalse);
    }
    final json = releaseJson();
    json['assets'][0].remove('digest');
    expect(UpdateRelease.parse(json, '0.4.1', deb)!.canInstall, isFalse);
  });

  late FakeAdapter adapter;
  late UpdateService service;
  late Directory temp;
  late List<List<String>> commands;
  late int installExit;
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    adapter = FakeAdapter();
    commands = [];
    installExit = 0;
    temp = await Directory.systemTemp.createTemp('nextalk-update-test-');
    service = UpdateService(
        dio: Dio()..httpClientAdapter = adapter,
        currentVersion: '0.4.1',
        detectTarget: () async => deb,
        createTemp: () => temp.createTemp('download-'),
        run: (exe, args) async {
          commands.add([exe, ...args]);
          expect(await File(args.last).readAsBytes(), bytes);
          return ProcessResult(1, installExit, '', '');
        });
  });
  tearDown(() async {
    service.dispose();
    await temp.delete(recursive: true);
  });

  test('校验成功后只执行固定包管理命令，完成后清理文件', () async {
    await service.check();
    expect(service.phase, UpdatePhase.available);
    await service.install(canInstall: () => true);
    expect(service.phase, UpdatePhase.installed);
    expect(commands.single.take(4),
        ['/usr/bin/pkexec', '/usr/bin/apt-get', 'install', '-y']);
    expect(await temp.list().toList(), isEmpty);
    await service.install(canInstall: () => true);
    expect(commands.length, 1);
  });
  test('SHA256 不一致禁止安装', () async {
    adapter.package = List.filled(bytes.length, 65);
    await service.check();
    await service.install(canInstall: () => true);
    expect(service.error, 'checksum');
    expect(commands, isEmpty);
    expect(await temp.list().toList(), isEmpty);
  });
  test('大小不一致禁止安装', () async {
    adapter.package = [1];
    await service.check();
    await service.install(canInstall: () => true);
    expect(service.error, 'checksum');
    expect(commands, isEmpty);
  });
  test('录音中拒绝下载；下载完成再次检查状态', () async {
    await service.check();
    await service.install(canInstall: () => false);
    expect(service.error, 'recording');
    expect(adapter.calls, 1);
    var checks = 0;
    await service.install(canInstall: () => ++checks == 1);
    expect(service.error, 'recording');
    expect(commands, isEmpty);
  });
  test('取消授权后可重试', () async {
    await service.check();
    installExit = 126;
    await service.install(canInstall: () => true);
    expect(service.error, 'authorization');
    installExit = 0;
    await service.install(canInstall: () => true);
    expect(service.phase, UpdatePhase.installed);
  });
  test('包管理器失败不报告成功', () async {
    await service.check();
    installExit = 100;
    await service.install(canInstall: () => true);
    expect(service.phase, UpdatePhase.failed);
    expect(service.error, 'install');
  });
  test('后台检查静默失败，手动检查展示错误', () async {
    adapter.status = 403;
    await service.check(background: true);
    expect(service.phase, UpdatePhase.idle);
    expect(service.error, isNull);
    await service.check();
    expect(service.error, 'check');
  });
  test('自动检查每日节流，手动检查可绕过；开关持久化', () async {
    await service.start();
    await service.check(background: true);
    await service.check(background: true);
    expect(adapter.calls, 1);
    await service.check();
    expect(adapter.calls, 2);
    await service.setAutoCheck(false);
    expect((await SharedPreferences.getInstance()).getBool('updates.autoCheck'),
        false);
    await service.check(background: true);
    expect(adapter.calls, 2);
  });
  test('并发检查不重复请求', () async {
    adapter.gate = Completer<void>();
    final first = service.check();
    await service.check();
    adapter.gate!.complete();
    await first;
    expect(adapter.calls, 1);
  });
  test('下载可取消，不进入安装', () async {
    await service.check();
    adapter.gate = Completer<void>();
    final install = service.install(canInstall: () => true);
    service.cancelDownload();
    adapter.gate!.complete();
    await install;
    expect(service.phase, UpdatePhase.available);
    expect(commands, isEmpty);
  });
  test('错误响应不能误报为最新版本', () async {
    adapter.json = {'message': 'unexpected response'};
    await service.check();
    expect(service.phase, UpdatePhase.failed);
    expect(service.error, 'check');
  });
  test('下载中重复安装不启动第二个任务', () async {
    await service.check();
    adapter.gate = Completer<void>();
    final first = service.install(canInstall: () => true);
    await service.install(canInstall: () => true);
    adapter.gate!.complete();
    await first;
    expect(commands.length, 1);
  });
}
