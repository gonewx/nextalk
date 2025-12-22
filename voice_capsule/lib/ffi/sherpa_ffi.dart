/// Sherpa-onnx FFI 绑定入口
/// 基于官方 flutter/sherpa_onnx 包，针对 Nextalk 项目定制
library sherpa_ffi;

import 'dart:ffi';
import 'dart:io';

export 'sherpa_onnx_bindings.dart';

/// Sherpa 库加载异常
class SherpaLibraryException implements Exception {
  final String message;
  SherpaLibraryException(this.message);

  @override
  String toString() => 'SherpaLibraryException: $message';
}

/// 缓存的库实例 (避免重复加载导致的资源泄漏)
DynamicLibrary? _cachedLibrary;

/// 加载 Sherpa 动态库 (Linux 专用)
///
/// 搜索顺序:
/// 1. libsherpa-onnx-c-api.so (RPATH, $ORIGIN/lib)
/// 2. ./lib/libsherpa-onnx-c-api.so (相对路径)
/// 3. /usr/local/lib/libsherpa-onnx-c-api.so (系统路径)
///
/// 注意: 库实例会被缓存，多次调用返回同一实例。
///
/// Throws [SherpaLibraryException] if library cannot be loaded.
DynamicLibrary loadSherpaLibrary() {
  // 返回缓存的实例
  if (_cachedLibrary != null) {
    return _cachedLibrary!;
  }

  if (!Platform.isLinux) {
    throw SherpaLibraryException('仅支持 Linux 平台');
  }

  final searchPaths = [
    'libsherpa-onnx-c-api.so', // RPATH ($ORIGIN/lib)
    './lib/libsherpa-onnx-c-api.so', // 相对路径
    '/usr/local/lib/libsherpa-onnx-c-api.so', // 系统路径
  ];

  for (final path in searchPaths) {
    try {
      _cachedLibrary = DynamicLibrary.open(path);
      return _cachedLibrary!;
    } catch (e) {
      // 继续尝试下一个路径
    }
  }

  throw SherpaLibraryException(
    '无法加载 Sherpa-onnx 库。请确认库文件存在于以下路径之一:\n'
    '${searchPaths.map((p) => "  - $p").join("\n")}',
  );
}

/// 检查 Sherpa 库是否可用
///
/// 注意: 此方法使用缓存机制，不会重复加载库。
bool isSherpaLibraryAvailable() {
  try {
    loadSherpaLibrary();
    return true;
  } catch (_) {
    return false;
  }
}
