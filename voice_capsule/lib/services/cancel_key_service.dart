import 'dart:async';
import 'dart:io';

import 'package:dbus/dbus.dart';
import 'package:flutter/foundation.dart';

import 'gnome_inject_client.dart';

/// Esc 取消键服务
///
/// 胶囊窗口不接受焦点 (gtk_window_set_accept_focus FALSE)，键盘事件始终
/// 发往用户正在输入的应用，Flutter 侧收不到 Esc。因此取消键由"看得到
/// 全局按键"的一方代为捕获，仅在录音期间生效，不影响 Esc 的日常用途：
///
/// - Fcitx5 插件: 录音期间本服务写入标记文件 `$XDG_RUNTIME_DIR/nextalk-recording`
///   (内容为本进程 PID)。插件在 Esc 按下时检查该文件且 PID 存活，才吞掉
///   这次 Esc 并向单实例 socket 发送 `cancel` 命令。应用崩溃残留的文件因
///   PID 已死而失效，不会永久吃掉 Esc。
/// - GNOME Shell 扩展 (无 fcitx5 的 GNOME/ibus 会话): 通过 D-Bus 调用
///   `GrabCancelKey(true)` 让扩展临时抢占 Esc 加速键，按下时发出
///   `CancelRequested` 信号，由本服务转发给 [onCancelRequested]。
///
/// 所有操作失败都静默降级：取消键只是便利功能，绝不能影响录音主流程。
class CancelKeyService {
  CancelKeyService._();
  static final CancelKeyService instance = CancelKeyService._();

  /// 测试专用的标记文件路径覆盖点 (避免碰到用户正在运行的实例)
  @visibleForTesting
  static String? markerPathOverride;

  /// 测试专用：禁用 GNOME D-Bus 路径
  @visibleForTesting
  static bool gnomeEnabled = true;

  /// GNOME 扩展报告 Esc 被按下时的回调 (由 main.dart 注入)
  void Function()? onCancelRequested;

  bool _armed = false;
  _GnomeCancelKeyGrab? _gnome;

  /// 当前是否处于捕获状态
  bool get isArmed => _armed;

  /// 标记文件路径 (与 Fcitx5 插件 nextalk.cpp 中的路径保持一致)
  static String get markerPath {
    final override = markerPathOverride;
    if (override != null) return override;
    final runtimeDir = Platform.environment['XDG_RUNTIME_DIR'];
    if (runtimeDir != null && runtimeDir.isNotEmpty) {
      return '$runtimeDir/nextalk-recording';
    }
    return '/tmp/nextalk-recording';
  }

  /// 开始捕获 Esc (进入录音状态时调用)
  void arm() {
    if (_armed) return;
    _armed = true;

    // 同步写入：录音一开始用户就可能按 Esc，不能让写文件落后于按键
    try {
      File(markerPath).writeAsStringSync('$pid\n', flush: true);
    } catch (e) {
      _log('写入录音标记失败: $e');
    }

    if (gnomeEnabled) {
      unawaited((_gnome ??= _GnomeCancelKeyGrab(_onGnomeCancel)).setGrab(true));
    }
  }

  /// 停止捕获 Esc (离开录音状态时调用，幂等)
  void disarm() {
    if (!_armed) return;
    _armed = false;
    _deleteMarker();
    unawaited(_gnome?.setGrab(false));
  }

  /// 清理上次异常退出残留的标记文件 (启动时调用)
  void cleanupStale() => _deleteMarker();

  /// 释放资源
  Future<void> dispose() async {
    disarm();
    await _gnome?.dispose();
    _gnome = null;
    onCancelRequested = null;
  }

  void _onGnomeCancel() {
    if (_armed) onCancelRequested?.call();
  }

  void _deleteMarker() {
    try {
      final file = File(markerPath);
      if (file.existsSync()) file.deleteSync();
    } catch (e) {
      _log('删除录音标记失败: $e');
    }
  }

  static void _log(String message) {
    // ignore: avoid_print
    print('[CancelKeyService] $message');
  }
}

/// GNOME Shell 扩展的 Esc 抢占通道
class _GnomeCancelKeyGrab {
  _GnomeCancelKeyGrab(this._onCancel);

  final void Function() _onCancel;

  /// 失败后的冷却期：非 GNOME 桌面或旧版扩展每次调用都会失败，
  /// 冷却期内不再尝试，避免每次录音都做一次无用的 D-Bus 往返
  static const Duration _retryCooldown = Duration(seconds: 60);

  DBusClient? _client;
  DBusRemoteObject? _object;
  StreamSubscription<DBusSignal>? _signalSub;
  DateTime? _failedAt;

  /// 串行化 grab/ungrab，避免快速开始/取消时乱序到达扩展
  Future<void> _chain = Future<void>.value();

  Future<void> setGrab(bool grab) {
    return _chain = _chain.then((_) => _setGrab(grab)).catchError((_) {});
  }

  Future<void> _setGrab(bool grab) async {
    final failedAt = _failedAt;
    if (failedAt != null &&
        DateTime.now().difference(failedAt) < _retryCooldown) {
      return;
    }

    try {
      final object = _ensureObject();
      if (grab) _ensureSignal(object);
      await object
          .callMethod(
            GnomeInjectConstants.interfaceName,
            'GrabCancelKey',
            [DBusBoolean(grab)],
            replySignature: DBusSignature('b'),
          )
          .timeout(const Duration(milliseconds: 500));
      _failedAt = null;
    } catch (e) {
      // 非 GNOME 桌面 / 扩展未安装或为旧版：静默降级
      _failedAt = DateTime.now();
    }
  }

  DBusRemoteObject _ensureObject() {
    return _object ??= DBusRemoteObject(
      _client ??= DBusClient.session(),
      name: GnomeInjectConstants.busName,
      path: DBusObjectPath(GnomeInjectConstants.objectPath),
    );
  }

  void _ensureSignal(DBusRemoteObject object) {
    _signalSub ??= DBusRemoteObjectSignalStream(
      object: object,
      interface: GnomeInjectConstants.interfaceName,
      name: 'CancelRequested',
    ).listen((_) => _onCancel(), onError: (_) {});
  }

  Future<void> dispose() async {
    // 等挂起的 ungrab 发出去再断开连接，否则扩展会一直抢着 Esc
    await _chain;
    await _signalSub?.cancel();
    _signalSub = null;
    await _client?.close();
    _client = null;
    _object = null;
  }
}
