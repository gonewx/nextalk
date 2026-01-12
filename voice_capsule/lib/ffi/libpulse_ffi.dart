// ignore_for_file: constant_identifier_names
import 'dart:ffi';
import 'package:ffi/ffi.dart';

// ===== PulseAudio 常量 =====

/// pa_context_state_t
const int paContextUnconnected = 0;
const int paContextConnecting = 1;
const int paContextAuthorizing = 2;
const int paContextSettingName = 3;
const int paContextReady = 4;
const int paContextFailed = 5;
const int paContextTerminated = 6;

/// 无效的 sink 索引，用于判断是否为 monitor
const int paInvalidIndex = 0xFFFFFFFF;

// ===== FFI 类型定义 =====

/// Opaque 类型
final class PaMainloop extends Opaque {}

final class PaMainloopApi extends Opaque {}

final class PaContext extends Opaque {}

final class PaOperation extends Opaque {}

/// pa_source_info 结构体（简化版）
final class PaSourceInfo extends Struct {
  external Pointer<Utf8> name;
  @Uint32()
  external int index;
  external Pointer<Utf8> description;
}

// ===== C 函数签名 =====

// pa_mainloop
typedef PaMainloopNewC = Pointer<PaMainloop> Function();
typedef PaMainloopNewDart = Pointer<PaMainloop> Function();

typedef PaMainloopFreeC = Void Function(Pointer<PaMainloop>);
typedef PaMainloopFreeDart = void Function(Pointer<PaMainloop>);

typedef PaMainloopGetApiC = Pointer<PaMainloopApi> Function(
    Pointer<PaMainloop>);
typedef PaMainloopGetApiDart = Pointer<PaMainloopApi> Function(
    Pointer<PaMainloop>);

typedef PaMainloopIterateC = Int32 Function(
    Pointer<PaMainloop>, Int32 block, Pointer<Int32> retval);
typedef PaMainloopIterateDart = int Function(
    Pointer<PaMainloop>, int block, Pointer<Int32> retval);

// pa_context
typedef PaContextNewC = Pointer<PaContext> Function(
    Pointer<PaMainloopApi>, Pointer<Utf8>);
typedef PaContextNewDart = Pointer<PaContext> Function(
    Pointer<PaMainloopApi>, Pointer<Utf8>);

typedef PaContextUnrefC = Void Function(Pointer<PaContext>);
typedef PaContextUnrefDart = void Function(Pointer<PaContext>);

typedef PaContextConnectC = Int32 Function(
    Pointer<PaContext>, Pointer<Utf8>, Int32, Pointer<Void>);
typedef PaContextConnectDart = int Function(
    Pointer<PaContext>, Pointer<Utf8>, int, Pointer<Void>);

typedef PaContextDisconnectC = Void Function(Pointer<PaContext>);
typedef PaContextDisconnectDart = void Function(Pointer<PaContext>);

typedef PaContextGetStateC = Int32 Function(Pointer<PaContext>);
typedef PaContextGetStateDart = int Function(Pointer<PaContext>);

// 回调类型
typedef PaContextNotifyCbC = Void Function(
    Pointer<PaContext>, Pointer<Void>);
typedef PaSourceInfoCbC = Void Function(
    Pointer<PaContext>, Pointer<PaSourceInfo>, Int32, Pointer<Void>);

typedef PaContextSetStateCallbackC = Void Function(
  Pointer<PaContext>,
  Pointer<NativeFunction<PaContextNotifyCbC>>,
  Pointer<Void>,
);
typedef PaContextSetStateCallbackDart = void Function(
  Pointer<PaContext>,
  Pointer<NativeFunction<PaContextNotifyCbC>>,
  Pointer<Void>,
);

typedef PaContextGetSourceInfoListC = Pointer<PaOperation> Function(
  Pointer<PaContext>,
  Pointer<NativeFunction<PaSourceInfoCbC>>,
  Pointer<Void>,
);
typedef PaContextGetSourceInfoListDart = Pointer<PaOperation> Function(
  Pointer<PaContext>,
  Pointer<NativeFunction<PaSourceInfoCbC>>,
  Pointer<Void>,
);

// pa_operation
typedef PaOperationUnrefC = Void Function(Pointer<PaOperation>);
typedef PaOperationUnrefDart = void Function(Pointer<PaOperation>);

typedef PaOperationGetStateC = Int32 Function(Pointer<PaOperation>);
typedef PaOperationGetStateDart = int Function(Pointer<PaOperation>);

// ===== 全局状态（用于回调） =====
List<PulseSourceInfo> _globalSources = [];
bool _globalDone = false;

// ===== 回调函数（必须是顶层函数） =====
void _stateCallback(Pointer<PaContext> ctx, Pointer<Void> userdata) {
  // 状态变化在 mainloop 中处理
}

void _sourceInfoCallback(
    Pointer<PaContext> ctx, Pointer<PaSourceInfo> info, int eol, Pointer<Void> userdata) {
  if (eol > 0) {
    _globalDone = true;
    return;
  }

  if (info.address == 0) return;

  final sourceInfo = info.ref;
  final name =
      sourceInfo.name.address != 0 ? sourceInfo.name.toDartString() : '';
  final description = sourceInfo.description.address != 0
      ? sourceInfo.description.toDartString()
      : name;

  // 通过名称判断是否为 monitor
  final isMonitor = name.contains('.monitor');

  _globalSources.add(PulseSourceInfo(
    name: name,
    description: description,
    index: sourceInfo.index,
    isMonitor: isMonitor,
  ));
}

// ===== PulseAudio 绑定类 =====

class LibPulseBindings {
  late final DynamicLibrary _lib;

  // mainloop
  late final PaMainloopNewDart mainloopNew;
  late final PaMainloopFreeDart mainloopFree;
  late final PaMainloopGetApiDart mainloopGetApi;
  late final PaMainloopIterateDart mainloopIterate;

  // context
  late final PaContextNewDart contextNew;
  late final PaContextUnrefDart contextUnref;
  late final PaContextConnectDart contextConnect;
  late final PaContextDisconnectDart contextDisconnect;
  late final PaContextGetStateDart contextGetState;
  late final PaContextSetStateCallbackDart contextSetStateCallback;
  late final PaContextGetSourceInfoListDart contextGetSourceInfoList;

  // operation
  late final PaOperationUnrefDart operationUnref;
  late final PaOperationGetStateDart operationGetState;

  LibPulseBindings() {
    _lib = _openLibPulse();

    mainloopNew = _lib
        .lookupFunction<PaMainloopNewC, PaMainloopNewDart>('pa_mainloop_new');
    mainloopFree = _lib
        .lookupFunction<PaMainloopFreeC, PaMainloopFreeDart>('pa_mainloop_free');
    mainloopGetApi =
        _lib.lookupFunction<PaMainloopGetApiC, PaMainloopGetApiDart>(
            'pa_mainloop_get_api');
    mainloopIterate =
        _lib.lookupFunction<PaMainloopIterateC, PaMainloopIterateDart>(
            'pa_mainloop_iterate');

    contextNew =
        _lib.lookupFunction<PaContextNewC, PaContextNewDart>('pa_context_new');
    contextUnref = _lib
        .lookupFunction<PaContextUnrefC, PaContextUnrefDart>('pa_context_unref');
    contextConnect =
        _lib.lookupFunction<PaContextConnectC, PaContextConnectDart>(
            'pa_context_connect');
    contextDisconnect =
        _lib.lookupFunction<PaContextDisconnectC, PaContextDisconnectDart>(
            'pa_context_disconnect');
    contextGetState =
        _lib.lookupFunction<PaContextGetStateC, PaContextGetStateDart>(
            'pa_context_get_state');
    contextSetStateCallback = _lib.lookupFunction<PaContextSetStateCallbackC,
        PaContextSetStateCallbackDart>('pa_context_set_state_callback');
    contextGetSourceInfoList = _lib.lookupFunction<PaContextGetSourceInfoListC,
        PaContextGetSourceInfoListDart>('pa_context_get_source_info_list');

    operationUnref =
        _lib.lookupFunction<PaOperationUnrefC, PaOperationUnrefDart>(
            'pa_operation_unref');
    operationGetState =
        _lib.lookupFunction<PaOperationGetStateC, PaOperationGetStateDart>(
            'pa_operation_get_state');
  }

  static DynamicLibrary _openLibPulse() {
    for (final name in ['libpulse.so.0', 'libpulse.so']) {
      try {
        return DynamicLibrary.open(name);
      } catch (_) {}
    }
    throw Exception('无法加载 libpulse 库');
  }
}

/// PulseAudio 设备信息
class PulseSourceInfo {
  final String name;
  final String description;
  final int index;
  final bool isMonitor;

  PulseSourceInfo({
    required this.name,
    required this.description,
    required this.index,
    required this.isMonitor,
  });

  @override
  String toString() =>
      'PulseSourceInfo(name=$name, desc=$description, monitor=$isMonitor)';
}

/// PulseAudio 设备枚举器
class PulseDeviceEnumerator {
  LibPulseBindings? _bindings;

  /// 枚举所有输入设备（source）
  ///
  /// 返回设备列表，如果失败返回 null
  List<PulseSourceInfo>? enumerate() {
    try {
      _bindings = LibPulseBindings();
    } catch (e) {
      return null; // libpulse 不可用
    }

    final pa = _bindings!;

    // 重置全局状态
    _globalSources = [];
    _globalDone = false;

    // 创建 mainloop
    final mainloop = pa.mainloopNew();
    if (mainloop.address == 0) return null;

    try {
      final api = pa.mainloopGetApi(mainloop);
      if (api.address == 0) return null;

      // 创建 context
      final appName = 'nextalk'.toNativeUtf8();
      final ctx = pa.contextNew(api, appName);
      calloc.free(appName);

      if (ctx.address == 0) return null;

      try {
        // 设置状态回调
        final stateCallbackPtr =
            Pointer.fromFunction<PaContextNotifyCbC>(_stateCallback);
        pa.contextSetStateCallback(ctx, stateCallbackPtr, nullptr);

        // 连接
        final result = pa.contextConnect(ctx, nullptr, 0, nullptr);
        if (result < 0) return null;

        // 运行 mainloop 直到完成
        final retval = calloc<Int32>();
        int iterations = 0;
        const maxIterations = 1000;
        bool requestSent = false;

        while (!_globalDone && iterations < maxIterations) {
          pa.mainloopIterate(mainloop, 1, retval);
          iterations++;

          final state = pa.contextGetState(ctx);
          if (state == paContextReady && !requestSent) {
            requestSent = true;
            final sourceCallbackPtr =
                Pointer.fromFunction<PaSourceInfoCbC>(_sourceInfoCallback);
            final op =
                pa.contextGetSourceInfoList(ctx, sourceCallbackPtr, nullptr);
            if (op.address != 0) {
              pa.operationUnref(op);
            }
          } else if (state == paContextFailed ||
              state == paContextTerminated) {
            break;
          }
        }

        calloc.free(retval);
        pa.contextDisconnect(ctx);
      } finally {
        pa.contextUnref(ctx);
      }
    } finally {
      pa.mainloopFree(mainloop);
    }

    return _globalSources.isEmpty ? null : List.from(_globalSources);
  }
}
