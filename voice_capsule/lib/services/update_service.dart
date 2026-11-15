import 'dart:async';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../constants/app_info.dart';

enum UpdatePhase {
  idle,
  checking,
  available,
  current,
  downloading,
  verifying,
  installing,
  installed,
  failed
}

typedef UpdateRunner = Future<ProcessResult> Function(String, List<String>);

/// 仅接受正式三段版本；开发构建不参与自动升级，避免覆盖源码运行环境。
int? compareReleaseVersions(String left, String right) {
  List<int>? parse(String value) {
    final match =
        RegExp(r'^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\+\d+)?$')
            .firstMatch(value);
    return match == null
        ? null
        : [for (var i = 1; i <= 3; i++) int.parse(match[i]!)];
  }

  final a = parse(left), b = parse(right);
  if (a == null || b == null) return null;
  for (var i = 0; i < 3; i++) {
    final result = a[i].compareTo(b[i]);
    if (result != 0) return result;
  }
  return 0;
}

class UpdateTarget {
  const UpdateTarget(this.extension, this.arch, this.installer);
  final String extension, arch, installer;

  static Future<UpdateTarget?> detect() async {
    if (!Platform.isLinux) return null;
    final machine =
        (await Process.run('uname', ['-m'])).stdout.toString().trim();
    // 当前发布流水线仅构建 x86_64。
    if (machine != 'x86_64') return null;
    final os = await File('/etc/os-release').readAsString();
    final ids = RegExp(r'^(?:ID|ID_LIKE)=(.*)$', multiLine: true)
        .allMatches(os)
        .expand((m) => m[1]!.replaceAll('"', '').replaceAll("'", '').split(' '))
        .toSet();
    if (ids.intersection({'debian', 'ubuntu'}).isNotEmpty &&
        await File('/usr/bin/apt-get').exists()) {
      return const UpdateTarget('deb', 'amd64', '/usr/bin/apt-get');
    }
    if (ids.intersection({'fedora', 'rhel', 'centos'}).isNotEmpty &&
        await File('/usr/bin/dnf').exists()) {
      return const UpdateTarget('rpm', 'x86_64', '/usr/bin/dnf');
    }
    return null;
  }
}

class UpdateRelease {
  const UpdateRelease(
      {required this.version,
      required this.notes,
      this.name,
      this.url,
      this.digest,
      this.size});
  final String version, notes;
  final String? name, url, digest;
  final int? size;
  bool get canInstall =>
      name != null && url != null && digest != null && size != null;

  static UpdateRelease? parse(
      Map<String, dynamic> json, String current, UpdateTarget? target) {
    final version = json['tag_name'];
    if (json['draft'] != false ||
        json['prerelease'] != false ||
        version is! String ||
        (compareReleaseVersions(version, current) ?? -1) <= 0) {
      return null;
    }
    final plain = version.replaceFirst(RegExp(r'^v'), '');
    Map<String, dynamic>? asset;
    if (target != null) {
      final pattern = target.extension == 'deb'
          ? RegExp(
              '^nextalk_${RegExp.escape(plain)}-[0-9]+_${target.arch}\\.deb\$')
          : RegExp(
              '^nextalk-${RegExp.escape(plain)}-[0-9]+\\.${target.arch}\\.rpm\$');
      for (final entry in (json['assets'] as List? ?? [])) {
        if (entry is Map<String, dynamic> &&
            entry['name'] is String &&
            pattern.hasMatch(entry['name'] as String)) {
          asset = entry;
          break;
        }
      }
    }
    final url = asset?['browser_download_url'] as String?;
    final uri = url == null ? null : Uri.tryParse(url);
    final trusted = uri != null &&
        uri.scheme == 'https' &&
        uri.host == 'github.com' &&
        uri.userInfo.isEmpty &&
        uri.port == 443 &&
        uri.pathSegments.length == 6 &&
        uri.pathSegments.take(4).join('/') ==
            'gonewx/nextalk/releases/download' &&
        uri.pathSegments[4] == version &&
        uri.pathSegments.last == asset?['name'];
    // GitHub REST release assets 的 digest 字段；缺少摘要时只提供手动更新。
    final digest = asset?['digest'];
    final validDigest = digest is String &&
        RegExp(r'^sha256:[a-fA-F0-9]{64}$').hasMatch(digest);
    return UpdateRelease(
      version: plain,
      notes: json['body'] as String? ?? '',
      name: trusted ? (asset?['name'] as String?) : null,
      url: trusted ? url : null,
      digest: validDigest ? digest.substring(7).toLowerCase() : null,
      size: asset?['size'] is int && (asset!['size'] as int) > 0
          ? asset['size'] as int
          : null,
    );
  }
}

/// 下载和提权分离：只有校验成功且用户点击升级后，才调用系统包管理器。
class UpdateService extends ChangeNotifier {
  UpdateService(
      {Dio? dio,
      this.currentVersion = appVersion,
      Future<UpdateTarget?> Function()? detectTarget,
      UpdateRunner? run,
      Future<Directory> Function()? createTemp})
      : _dio = dio ??
            Dio(BaseOptions(
                connectTimeout: const Duration(seconds: 15),
                receiveTimeout: const Duration(seconds: 30),
                headers: {'User-Agent': 'Nextalk-Updater'})),
        _detectTarget = detectTarget ?? UpdateTarget.detect,
        _run = run ?? ((exe, args) => Process.run(exe, args)),
        _createTemp = createTemp ??
            (() => Directory.systemTemp.createTemp('nextalk-update-'));

  static final instance = UpdateService();
  final Dio _dio;
  final String currentVersion;
  final Future<UpdateTarget?> Function() _detectTarget;
  final UpdateRunner _run;
  final Future<Directory> Function() _createTemp;
  UpdatePhase phase = UpdatePhase.idle;
  UpdateRelease? release;
  UpdateTarget? _target;
  String? error;
  double? progress;
  bool autoCheck = true;
  bool _disposed = false;
  Timer? _timer, _startup;
  CancelToken? _cancel;
  SharedPreferences? _prefs;
  bool get busy => {
        UpdatePhase.checking,
        UpdatePhase.downloading,
        UpdatePhase.verifying,
        UpdatePhase.installing
      }.contains(phase);
  bool get installing => {
        UpdatePhase.downloading,
        UpdatePhase.verifying,
        UpdatePhase.installing
      }.contains(phase);
  bool get development =>
      compareReleaseVersions(currentVersion, currentVersion) == null;

  void _emit() {
    if (!_disposed) notifyListeners();
  }

  Future<void> start() async {
    if (_disposed || _timer != null || development) return;
    _prefs = await SharedPreferences.getInstance();
    if (_disposed) return;
    autoCheck = _prefs!.getBool('updates.autoCheck') ?? true;
    _startup =
        Timer(const Duration(seconds: 20), () => check(background: true));
    _timer = Timer.periodic(
        const Duration(hours: 1), (_) => check(background: true));
    _emit();
  }

  Future<void> setAutoCheck(bool value) async {
    autoCheck = value;
    _emit();
    _prefs ??= await SharedPreferences.getInstance();
    await _prefs!.setBool('updates.autoCheck', value);
  }

  Future<void> check({bool background = false}) async {
    if (_disposed || busy || phase == UpdatePhase.installed || development) {
      return;
    }
    if (background) {
      if (!autoCheck) return;
      final last = _prefs?.getInt('updates.lastAttempt') ?? 0;
      if (DateTime.now().millisecondsSinceEpoch - last <
          const Duration(hours: 24).inMilliseconds) {
        return;
      }
    }
    final previous = phase;
    phase = UpdatePhase.checking;
    error = null;
    _emit();
    try {
      await _prefs?.setInt(
          'updates.lastAttempt', DateTime.now().millisecondsSinceEpoch);
      // 发行版探测失败仍可展示版本和手动下载入口。
      try {
        _target = await _detectTarget();
      } catch (_) {
        _target = null;
      }
      final response = await _dio.get<Map<String, dynamic>>(
          'https://api.github.com/repos/gonewx/nextalk/releases/latest',
          options: Options(headers: {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
          }));
      final data = response.data;
      if (data == null ||
          data['tag_name'] is! String ||
          data['assets'] is! List ||
          data['draft'] is! bool ||
          data['prerelease'] is! bool) {
        throw const FormatException('Invalid release response');
      }
      release = UpdateRelease.parse(data, currentVersion, _target);
      phase = release == null ? UpdatePhase.current : UpdatePhase.available;
    } catch (e) {
      if (background) {
        phase = previous;
      } else {
        phase = UpdatePhase.failed;
        error = 'check';
      }
      debugPrint('Update check failed: $e');
    }
    _emit();
  }

  void cancelDownload() {
    if (phase == UpdatePhase.downloading) _cancel?.cancel();
  }

  Future<void> install({required bool Function() canInstall}) async {
    final selected = release;
    final target = _target;
    if (_disposed ||
        busy ||
        phase == UpdatePhase.installed ||
        selected == null ||
        !selected.canInstall ||
        target == null) {
      return;
    }
    if (!canInstall()) {
      error = 'recording';
      phase = UpdatePhase.failed;
      _emit();
      return;
    }
    phase = UpdatePhase.downloading;
    error = null;
    progress = null;
    _cancel = CancelToken();
    _emit();
    Directory? directory;
    try {
      directory = await _createTemp();
      final package = File('${directory.path}/${selected.name}');
      await _dio.download(selected.url!, package.path, cancelToken: _cancel,
          onReceiveProgress: (received, total) {
        if (received > selected.size!) {
          _cancel?.cancel('size');
          return;
        }
        progress = total > 0 ? (received / total).clamp(0.0, 1.0) : null;
        _emit();
      });
      phase = UpdatePhase.verifying;
      _emit();
      if (await package.length() != selected.size ||
          (await sha256.bind(package.openRead()).first).toString() !=
              selected.digest) {
        throw const FormatException('checksum');
      }
      if (_disposed) return;
      if (!canInstall()) {
        error = 'recording';
        throw StateError('recording');
      }
      phase = UpdatePhase.installing;
      _emit();
      // 不运行 shell，不接受远端命令；系统认证由 polkit 处理。
      final result = await _run(
          '/usr/bin/pkexec', [target.installer, 'install', '-y', package.path]);
      if (result.exitCode != 0) {
        error = result.exitCode == 126 || result.exitCode == 127
            ? 'authorization'
            : 'install';
        throw StateError('installer exit ${result.exitCode}');
      }
      phase = UpdatePhase.installed;
    } catch (e) {
      if (e is DioException && CancelToken.isCancel(e) && e.error != 'size') {
        phase = UpdatePhase.available;
        error = null;
      } else {
        error ??= e is FormatException
            ? 'checksum'
            : phase == UpdatePhase.installing
                ? 'install'
                : 'download';
        phase = UpdatePhase.failed;
      }
      debugPrint('Update install failed: $e');
    } finally {
      _cancel = null;
      if (directory != null) {
        try {
          await directory.delete(recursive: true);
        } catch (_) {/* 不覆盖安装结果 */}
      }
      _emit();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _timer?.cancel();
    _startup?.cancel();
    _cancel?.cancel();
    _dio.close();
    super.dispose();
  }
}
