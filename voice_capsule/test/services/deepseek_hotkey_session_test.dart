import 'dart:async';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:voice_capsule/services/window_service.dart';
import 'package:voice_capsule/services/asr/deepseek_asr_engine.dart';
import 'package:voice_capsule/services/audio_capture.dart';
import 'package:voice_capsule/services/audio_inference_pipeline.dart';
import 'package:voice_capsule/services/cancel_key_service.dart';
import 'package:voice_capsule/services/fcitx_client.dart';
import 'package:voice_capsule/services/hotkey_controller.dart';
import 'package:voice_capsule/services/model_manager.dart';
import 'package:voice_capsule/state/capsule_state.dart';

class SessionPipeline extends AudioInferencePipeline {
  SessionPipeline()
      : super(
            audioCapture: AudioCapture(),
            asrEngine: DeepSeekAsrEngine(),
            modelManager: ModelManager());
  int starts = 0;
  Completer<void>? cancelGate;
  @override
  Future<PipelineError> start() async {
    starts++;
    return PipelineError.none;
  }

  @override
  Future<String> stop() async => 'old transcript';
  @override
  Future<void> cancel() async {
    await cancelGate?.future;
  }
}

class DelayedFcitx extends FcitxClient {
  final checking = Completer<void>();
  final available = Completer<bool>();
  final sent = <String>[];
  @override
  Future<bool> isAvailable() {
    if (!checking.isCompleted) checking.complete();
    return available.future;
  }

  @override
  Future<void> sendText(String text) async {
    sent.add(text);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory dir;
  late SessionPipeline pipeline;
  late DelayedFcitx fcitx;
  late StreamController<CapsuleStateData> states;
  final controller = HotkeyController.instance;
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(const MethodChannel('window_manager'),
        (call) async {
      if (call.method == 'getBounds') {
        return {'x': 0.0, 'y': 0.0, 'width': 400.0, 'height': 120.0};
      }
      if (call.method.startsWith('is')) return false;
      return null;
    });
    messenger.setMockMethodCallHandler(
        const MethodChannel('nextalk/window'), (call) async => null);
    final display = {
      'id': 'test',
      'name': 'test',
      'size': {'width': 1024.0, 'height': 768.0},
      'visiblePosition': {'dx': 0.0, 'dy': 0.0},
      'visibleSize': {'width': 1024.0, 'height': 768.0},
      'scaleFactor': 1.0
    };
    messenger.setMockMethodCallHandler(
        const MethodChannel('dev.leanflutter.plugins/screen_retriever'),
        (call) async {
      if (call.method == 'getCursorScreenPoint') return {'dx': 0.0, 'dy': 0.0};
      if (call.method == 'getPrimaryDisplay') return display;
      if (call.method == 'getAllDisplays') {
        return {
          'displays': [display]
        };
      }
      return null;
    });
    await WindowService.instance.initialize();
    dir = await Directory.systemTemp.createTemp('deepseek-session-test');
    CancelKeyService.markerPathOverride = '${dir.path}/recording';
    CancelKeyService.gnomeEnabled = false;
    pipeline = SessionPipeline();
    fcitx = DelayedFcitx();
    states = StreamController.broadcast();
    await controller.initialize(
        pipeline: pipeline, fcitxClient: fcitx, stateController: states);
  });
  tearDown(() async {
    controller.configurationOpen = false;
    controller.onRecordingBlocked = null;
    await controller.dispose();
    await WindowService.instance.dispose();
    await pipeline.dispose();
    await states.close();
    CancelKeyService.markerPathOverride = null;
    CancelKeyService.gnomeEnabled = true;
    await dir.delete(recursive: true);
  });
  test('settings-blocked shortcuts report feedback without starting capture',
      () async {
    var notifications = 0;
    controller.configurationOpen = true;
    controller.onRecordingBlocked = () async {
      notifications++;
    };
    await controller.toggle();
    await controller.show();
    expect(notifications, 2);
    expect(pipeline.starts, 0);
    expect(controller.state, HotkeyState.idle);
    await controller.cancel();
    expect(notifications, 2);
    controller.configurationOpen = false;
    await controller.show();
    expect(pipeline.starts, 1);
    await controller.cancel();
  });
  test('cancelled backend lookup cannot commit into the next session',
      () async {
    await controller.show();
    final submitting = controller.hide();
    await fcitx.checking.future;
    await controller.cancel();
    await controller.show();
    expect(controller.state, HotkeyState.recording);
    fcitx.available.complete(true);
    await submitting;
    expect(fcitx.sent, isEmpty);
    expect(controller.state, HotkeyState.recording);
    await controller.cancel();
  });
  test('restart waits for complete cancellation before starting capture',
      () async {
    await controller.show();
    pipeline.cancelGate = Completer<void>();
    final cancellation = controller.cancel();
    await Future<void>.delayed(Duration.zero);
    final restart = controller.show();
    await Future<void>.delayed(Duration.zero);
    expect(pipeline.starts, 1);
    pipeline.cancelGate!.complete();
    await cancellation;
    await restart;
    expect(pipeline.starts, 2);
    expect(controller.state, HotkeyState.recording);
    pipeline.cancelGate = null;
    await controller.cancel();
  });
}
