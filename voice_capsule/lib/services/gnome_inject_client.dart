import 'dart:async';

import 'package:dbus/dbus.dart';

/// GNOME Shell 扩展注入客户端 (三级注入链的第二级)
///
/// 对应扩展 `addons/gnome/nextalk@gonewx.com`：扩展在 gnome-shell 进程内
/// 导出 D-Bus 方法 `CommitText(s)→(s)`，内部调用 `Main.inputMethod.commit()`
/// （GNOME OSK 的上屏通道，与输入法框架无关）。用于 fcitx5 socket 不可用的
/// GNOME/ibus 环境（如 Fedora 默认会话）直接上屏识别文本。
///
/// 设计要点（对齐 spec-fix-fedora-inject-clipboard-fallback）：
/// - dest 为 `org.gnome.Shell`（扩展挂在 gnome-shell 自身连接上，无自持 bus name）
/// - `isAvailable()` 用短超时（500ms）Introspect 探测，结果缓存避免每次提交都探测
/// - `commitText()` 失败时使可用性缓存失效，下次提交重新探测
/// - 非 GNOME 桌面 / 扩展未启用：探测失败静默降级，不抛异常

/// D-Bus 常量
class GnomeInjectConstants {
  GnomeInjectConstants._();

  static const String busName = 'org.gnome.Shell';
  static const String objectPath = '/com/gonewx/nextalk/Inject';
  static const String interfaceName = 'com.gonewx.nextalk.Inject';
}

/// GNOME 注入 D-Bus 交互抽象层
///
/// 抽出接口是为了在单测中注入 fake，不依赖真实 session bus
/// （对齐 portal_hotkey_service 的 GlobalShortcutsBackend 注入模式）。
abstract class GnomeInjectBackend {
  /// 探测扩展 D-Bus 接口是否已导出（短超时）。
  ///
  /// gnome-shell 对未知路径的 Introspect 会返回空节点而非报错，
  /// 因此实现必须检查返回的接口列表中是否包含目标接口。
  /// 非 GNOME 桌面（org.gnome.Shell 名字不存在）会抛 D-Bus 错误。
  Future<bool> probe();

  /// 调用扩展 CommitText，返回扩展的结果串（'OK' 或 'ERR: ...'）。
  Future<String> commitText(String text);

  /// 释放底层连接。
  Future<void> dispose();
}

/// 基于 package:dbus 的真实实现
class DBusGnomeInjectBackend implements GnomeInjectBackend {
  DBusGnomeInjectBackend({
    DBusClient? client,
    Duration? probeTimeout,
    Duration? commitTimeout,
  })  : _client = client ?? DBusClient.session(),
        _probeTimeout = probeTimeout ?? const Duration(milliseconds: 500),
        _commitTimeout = commitTimeout ?? const Duration(seconds: 2) {
    _object = DBusRemoteObject(
      _client,
      name: GnomeInjectConstants.busName,
      path: DBusObjectPath(GnomeInjectConstants.objectPath),
    );
  }

  final DBusClient _client;

  /// 可用性探测超时——短，快速判定接口缺失（spec: ≤500ms）
  final Duration _probeTimeout;

  /// CommitText 调用超时——commit 在 shell 内同步完成，略放宽兜底
  final Duration _commitTimeout;

  late final DBusRemoteObject _object;

  @override
  Future<bool> probe() async {
    final node = await _object.introspect().timeout(_probeTimeout);
    return node.interfaces
        .any((i) => i.name == GnomeInjectConstants.interfaceName);
  }

  @override
  Future<String> commitText(String text) async {
    final result = await _object
        .callMethod(
          GnomeInjectConstants.interfaceName,
          'CommitText',
          [DBusString(text)],
          replySignature: DBusSignature('s'),
        )
        .timeout(_commitTimeout);
    return result.returnValues[0].asString();
  }

  @override
  Future<void> dispose() async {
    await _client.close();
  }
}

/// GNOME 注入客户端（可用性缓存 + 失败降级语义）
class GnomeInjectClient {
  /// [backend] 可注入 fake 用于测试；缺省时首次使用才懒加载真实 D-Bus 连接
  /// （避免在无 session bus 的环境构造即抛异常）。
  /// [negativeCacheTtl] 负结果缓存有效期，测试可传 Duration.zero 立即过期。
  GnomeInjectClient({GnomeInjectBackend? backend, Duration? negativeCacheTtl})
      : _backend = backend,
        _negativeCacheTtl = negativeCacheTtl ?? const Duration(seconds: 60);

  GnomeInjectBackend? _backend;
  bool? _availableCache;
  DateTime? _negativeCachedAt;

  /// 负结果缓存 TTL：登录自启动时应用可能早于 gnome-shell 完成扩展加载，
  /// 首探 false 若永久缓存会导致"扩展已启用却一直剪贴板"直到重启应用；
  /// 过期重探即可自愈。正结果仍长期缓存（Wayland 下禁用扩展需重登，
  /// 应用随会话重启；运行中失效由 commitText 失败路径兜底）。
  final Duration _negativeCacheTtl;
  bool _isDisposed = false;

  /// 获取（懒加载）backend；构造失败（如无 session bus）时抛异常，
  /// 由调用处 catch 后视为不可用。
  GnomeInjectBackend _obtainBackend() =>
      _backend ??= DBusGnomeInjectBackend();

  /// 扩展是否可用（短超时探测，正结果长期缓存、负结果按 TTL 缓存）
  Future<bool> isAvailable() async {
    if (_isDisposed) return false;

    final cached = _availableCache;
    if (cached == true) return true;
    if (cached == false) {
      final at = _negativeCachedAt;
      if (at != null && DateTime.now().difference(at) < _negativeCacheTtl) {
        return false;
      }
      // 负缓存过期，重新探测
    }

    try {
      _availableCache = await _obtainBackend().probe();
    } catch (e) {
      // 非 GNOME 桌面 / 扩展未启用 / D-Bus 超时：静默降级
      // ignore: avoid_print
      print('[GnomeInjectClient] 探测失败，GNOME 注入不可用: $e');
      _availableCache = false;
    }
    if (_availableCache == false) {
      _negativeCachedAt = DateTime.now();
    }
    return _availableCache!;
  }

  /// 提交文本，返回是否成功
  ///
  /// 空文本不调用后端直接返回 false（由调用方收尾）；
  /// 任何失败（D-Bus 超时/异常/扩展返回 ERR）返回 false 并使可用性缓存失效，
  /// 调用方据此走剪贴板 fallback，文本不丢失。
  Future<bool> commitText(String text) async {
    if (_isDisposed || text.isEmpty) return false;

    try {
      final result = await _obtainBackend().commitText(text);
      if (result == 'OK') return true;
      // ignore: avoid_print
      print('[GnomeInjectClient] ❌ CommitText 返回失败: $result');
    } catch (e) {
      // ignore: avoid_print
      print('[GnomeInjectClient] ❌ CommitText 调用异常: $e');
    }
    _availableCache = null; // 失败使缓存失效，下次提交重新探测
    return false;
  }

  /// 释放资源（幂等）
  Future<void> dispose() async {
    if (_isDisposed) return;
    _isDisposed = true;
    await _backend?.dispose();
    _backend = null;
  }
}
