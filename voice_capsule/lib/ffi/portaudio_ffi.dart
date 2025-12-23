import 'dart:ffi';
import 'package:ffi/ffi.dart';

// ===== PortAudio 常量 =====
const int paFloat32 = 0x00000001;
const int paNoError = 0;
const int paNoDevice = -1;
const int paFramesPerBufferUnspecified = 0;
const int paClipOff = 0x00000001;

// 错误码 (用于 read() 处理)
const int paInputOverflowed = -9981;
const int paDeviceUnavailable = -9985;
const int paInternalError = -9986;
const int paInvalidChannelCount = -9998;

// ===== FFI 结构体 =====
final class PaStreamParameters extends Struct {
  @Int32()
  external int device;
  @Int32()
  external int channelCount;
  @Uint32()
  external int sampleFormat;
  @Double()
  external double suggestedLatency;
  external Pointer<Void> hostApiSpecificStreamInfo;
}

final class PaDeviceInfo extends Struct {
  @Int32()
  external int structVersion;
  external Pointer<Utf8> name;
  @Int32()
  external int hostApi;
  @Int32()
  external int maxInputChannels;
  @Int32()
  external int maxOutputChannels;
  @Double()
  external double defaultLowInputLatency;
  @Double()
  external double defaultLowOutputLatency;
  @Double()
  external double defaultHighInputLatency;
  @Double()
  external double defaultHighOutputLatency;
  @Double()
  external double defaultSampleRate;
}

// ===== FFI 类型签名 (C 类型) =====
typedef PaInitializeC = Int32 Function();
typedef PaTerminateC = Int32 Function();
typedef PaGetDefaultInputDeviceC = Int32 Function();
typedef PaGetDeviceInfoC = Pointer<PaDeviceInfo> Function(Int32 device);
typedef PaCloseStreamC = Int32 Function(Pointer<Void> stream);
typedef PaStartStreamC = Int32 Function(Pointer<Void> stream);
typedef PaStopStreamC = Int32 Function(Pointer<Void> stream);
typedef PaReadStreamC = Int32 Function(
  Pointer<Void> stream,
  Pointer<Float> buffer,
  Uint32 frames,
);
typedef PaGetErrorTextC = Pointer<Utf8> Function(Int32 errorCode);

// Pa_OpenStream 完整签名
typedef PaOpenStreamC = Int32 Function(
  Pointer<Pointer<Void>> stream,
  Pointer<PaStreamParameters> inputParams,
  Pointer<PaStreamParameters> outputParams,
  Double sampleRate,
  Uint32 framesPerBuffer,
  Uint32 streamFlags,
  Pointer<Void> callback,
  Pointer<Void> userData,
);

// ===== FFI 类型签名 (Dart 类型) =====
typedef PaInitializeDart = int Function();
typedef PaTerminateDart = int Function();
typedef PaGetDefaultInputDeviceDart = int Function();
typedef PaGetDeviceInfoDart = Pointer<PaDeviceInfo> Function(int device);
typedef PaCloseStreamDart = int Function(Pointer<Void> stream);
typedef PaStartStreamDart = int Function(Pointer<Void> stream);
typedef PaStopStreamDart = int Function(Pointer<Void> stream);
typedef PaReadStreamDart = int Function(
  Pointer<Void> stream,
  Pointer<Float> buffer,
  int frames,
);
typedef PaGetErrorTextDart = Pointer<Utf8> Function(int errorCode);

typedef PaOpenStreamDart = int Function(
  Pointer<Pointer<Void>> stream,
  Pointer<PaStreamParameters> inputParams,
  Pointer<PaStreamParameters> outputParams,
  double sampleRate,
  int framesPerBuffer,
  int streamFlags,
  Pointer<Void> callback,
  Pointer<Void> userData,
);

// ===== PortAudio 绑定类 =====
class PortAudioBindings {
  late final DynamicLibrary _lib;
  late final PaInitializeDart initialize;
  late final PaTerminateDart terminate;
  late final PaGetDefaultInputDeviceDart getDefaultInputDevice;
  late final PaGetDeviceInfoDart getDeviceInfo;
  late final PaOpenStreamDart openStream;
  late final PaCloseStreamDart closeStream;
  late final PaStartStreamDart startStream;
  late final PaStopStreamDart stopStream;
  late final PaReadStreamDart readStream;
  late final PaGetErrorTextDart getErrorText;

  PortAudioBindings() {
    _lib = _openPortAudio();
    initialize = _lib.lookupFunction<PaInitializeC, PaInitializeDart>(
      'Pa_Initialize',
    );
    terminate = _lib.lookupFunction<PaTerminateC, PaTerminateDart>(
      'Pa_Terminate',
    );
    getDefaultInputDevice = _lib.lookupFunction<PaGetDefaultInputDeviceC,
        PaGetDefaultInputDeviceDart>('Pa_GetDefaultInputDevice');
    getDeviceInfo = _lib.lookupFunction<PaGetDeviceInfoC, PaGetDeviceInfoDart>(
      'Pa_GetDeviceInfo',
    );
    openStream = _lib.lookupFunction<PaOpenStreamC, PaOpenStreamDart>(
      'Pa_OpenStream',
    );
    closeStream = _lib.lookupFunction<PaCloseStreamC, PaCloseStreamDart>(
      'Pa_CloseStream',
    );
    startStream = _lib.lookupFunction<PaStartStreamC, PaStartStreamDart>(
      'Pa_StartStream',
    );
    stopStream = _lib.lookupFunction<PaStopStreamC, PaStopStreamDart>(
      'Pa_StopStream',
    );
    readStream = _lib.lookupFunction<PaReadStreamC, PaReadStreamDart>(
      'Pa_ReadStream',
    );
    getErrorText = _lib.lookupFunction<PaGetErrorTextC, PaGetErrorTextDart>(
      'Pa_GetErrorText',
    );
  }

  /// 回退逻辑: 兼容不同发行版
  static DynamicLibrary _openPortAudio() {
    for (final name in [
      'libportaudio.so.2',
      'libportaudio.so',
      'libportaudio.so.0'
    ]) {
      try {
        return DynamicLibrary.open(name);
      } catch (_) {}
    }
    throw Exception('无法加载 PortAudio 库，请确认已安装 libportaudio2');
  }

  String errorText(int code) => getErrorText(code).toDartString();
}
