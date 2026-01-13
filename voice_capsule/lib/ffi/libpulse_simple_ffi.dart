// ignore_for_file: constant_identifier_names
import 'dart:ffi';
import 'package:ffi/ffi.dart';

// ===== PulseAudio Simple API 常量 =====

/// 流方向
const int PA_STREAM_RECORD = 2;

/// 采样格式
const int PA_SAMPLE_FLOAT32NE = 5; // Float32 native endian (通常是 LE)

// ===== FFI 结构体 =====

/// pa_sample_spec 结构体
final class PaSampleSpec extends Struct {
  @Int32()
  external int format;

  @Uint32()
  external int rate;

  @Uint8()
  external int channels;
}

/// Opaque 类型
final class PaSimple extends Opaque {}

// ===== C 函数签名 =====

typedef PaSimpleNewC = Pointer<PaSimple> Function(
  Pointer<Utf8> server,      // NULL for default
  Pointer<Utf8> name,        // Application name
  Int32 dir,                 // PA_STREAM_RECORD
  Pointer<Utf8> dev,         // Device name (NULL for default)
  Pointer<Utf8> streamName,  // Stream name
  Pointer<PaSampleSpec> ss,  // Sample spec
  Pointer<Void> map,         // Channel map (NULL for default)
  Pointer<Void> attr,        // Buffer attributes (NULL for default)
  Pointer<Int32> error,      // Error code output
);

typedef PaSimpleReadC = Int32 Function(
  Pointer<PaSimple> s,
  Pointer<Void> data,
  Size length,
  Pointer<Int32> error,
);

typedef PaSimpleFreeC = Void Function(Pointer<PaSimple> s);

typedef PaStrerrorC = Pointer<Utf8> Function(Int32 error);

// ===== Dart 函数签名 =====

typedef PaSimpleNewDart = Pointer<PaSimple> Function(
  Pointer<Utf8> server,
  Pointer<Utf8> name,
  int dir,
  Pointer<Utf8> dev,
  Pointer<Utf8> streamName,
  Pointer<PaSampleSpec> ss,
  Pointer<Void> map,
  Pointer<Void> attr,
  Pointer<Int32> error,
);

typedef PaSimpleReadDart = int Function(
  Pointer<PaSimple> s,
  Pointer<Void> data,
  int length,
  Pointer<Int32> error,
);

typedef PaSimpleFreeDart = void Function(Pointer<PaSimple> s);

typedef PaStrerrorDart = Pointer<Utf8> Function(int error);

// ===== PulseAudio Simple 绑定类 =====

class LibPulseSimpleBindings {
  late final DynamicLibrary _lib;

  late final PaSimpleNewDart simpleNew;
  late final PaSimpleReadDart simpleRead;
  late final PaSimpleFreeDart simpleFree;
  late final PaStrerrorDart strerror;

  LibPulseSimpleBindings() {
    _lib = _openLibPulseSimple();

    simpleNew = _lib.lookupFunction<PaSimpleNewC, PaSimpleNewDart>('pa_simple_new');
    simpleRead = _lib.lookupFunction<PaSimpleReadC, PaSimpleReadDart>('pa_simple_read');
    simpleFree = _lib.lookupFunction<PaSimpleFreeC, PaSimpleFreeDart>('pa_simple_free');
    strerror = _lib.lookupFunction<PaStrerrorC, PaStrerrorDart>('pa_strerror');
  }

  static DynamicLibrary _openLibPulseSimple() {
    for (final name in ['libpulse-simple.so.0', 'libpulse-simple.so']) {
      try {
        return DynamicLibrary.open(name);
      } catch (_) {}
    }
    throw Exception('无法加载 libpulse-simple 库');
  }
}
