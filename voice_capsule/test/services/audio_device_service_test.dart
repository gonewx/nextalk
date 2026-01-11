import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/audio_device_service.dart';
import 'package:voice_capsule/constants/settings_constants.dart';

/// Story 3-9 Task 2.5, 9.1: AudioDeviceService 单元测试
void main() {
  group('AudioDeviceService', () {
    test('instance 是单例', () {
      final instance1 = AudioDeviceService.instance;
      final instance2 = AudioDeviceService.instance;
      expect(identical(instance1, instance2), isTrue);
    });

    test('listInputDevices() 返回 List<AudioInputDevice>', () {
      // 由于测试环境可能没有实际音频设备，只验证返回类型
      final devices = AudioDeviceService.instance.listInputDevices();
      expect(devices, isA<List<AudioInputDevice>>());
    });

    test('listInputDevices() 支持 forceRefresh 参数', () {
      // 验证 forceRefresh 参数存在且可用
      final devices1 = AudioDeviceService.instance.listInputDevices();
      final devices2 = AudioDeviceService.instance.listInputDevices(forceRefresh: true);
      expect(devices1, isA<List<AudioInputDevice>>());
      expect(devices2, isA<List<AudioInputDevice>>());
    });

    test('invalidateCache() 可以被调用', () {
      expect(() => AudioDeviceService.instance.invalidateCache(), returnsNormally);
    });

    test('findDeviceByName() 对不存在的设备返回 -1', () {
      final index = AudioDeviceService.instance
          .findDeviceByName('__不存在的设备名称__');
      expect(index, equals(-1));
    });

    test('findDeviceByName() 支持子串匹配', () {
      // 测试子串匹配逻辑 (如果有设备的话)
      final devices = AudioDeviceService.instance.listInputDevices();
      if (devices.isNotEmpty) {
        // 尝试用设备名的一部分来匹配
        final firstName = devices.first.name;
        if (firstName.length > 3) {
          final partial = firstName.substring(0, 3);
          final index = AudioDeviceService.instance.findDeviceByName(partial);
          // 应该能找到（返回 >= 0）
          expect(index, greaterThanOrEqualTo(0));
        }
      }
    });

    test('getDeviceStatus() 对无效索引返回 DeviceAvailability.busy', () {
      final status = AudioDeviceService.instance.getDeviceStatus(-1);
      expect(status, equals(DeviceAvailability.busy));
    });

    test('getDeviceStatus() 对超出范围的索引返回 DeviceAvailability.busy', () {
      final status = AudioDeviceService.instance.getDeviceStatus(9999);
      expect(status, equals(DeviceAvailability.busy));
    });
  });

  group('AudioInputDevice 数据类', () {
    test('AudioInputDevice 构造函数正确', () {
      final device = AudioInputDevice(
        index: 0,
        name: 'alsa_input.pci-0000_00_1f.3.analog-stereo',
        description: 'Built-in Audio Analog Stereo',
        status: DeviceAvailability.available,
      );
      expect(device.index, equals(0));
      expect(device.name, equals('alsa_input.pci-0000_00_1f.3.analog-stereo'));
      expect(device.description, equals('Built-in Audio Analog Stereo'));
      expect(device.status, equals(DeviceAvailability.available));
    });

    test('DeviceAvailability 枚举包含预期值', () {
      expect(DeviceAvailability.values.length, equals(2));
      expect(DeviceAvailability.values.contains(DeviceAvailability.available), isTrue);
      expect(DeviceAvailability.values.contains(DeviceAvailability.busy), isTrue);
    });

    test('AudioInputDevice toString() 正确', () {
      final device = AudioInputDevice(
        index: 1,
        name: 'alsa_input.usb-device',
        description: 'USB Microphone',
        status: DeviceAvailability.busy,
      );
      expect(device.toString(), contains('index=1'));
      expect(device.toString(), contains('alsa_input.usb-device'));
      expect(device.toString(), contains('USB Microphone'));
      expect(device.toString(), contains('busy'));
    });
  });

  group('SettingsConstants 音频配置', () {
    test('keyAudioInputDevice 键名正确', () {
      expect(
        SettingsConstants.keyAudioInputDevice,
        equals('${SettingsConstants.keyPrefix}audio_input_device'),
      );
    });

    test('defaultAudioInputDevice 为 "default"', () {
      expect(SettingsConstants.defaultAudioInputDevice, equals('default'));
    });

    test('defaultSettingsYaml 包含 audio 配置块', () {
      expect(SettingsConstants.defaultSettingsYaml, contains('audio:'));
    });

    test('defaultSettingsYaml 包含 input_device 配置', () {
      expect(SettingsConstants.defaultSettingsYaml, contains('input_device:'));
    });

    test('defaultSettingsYaml input_device 默认为 default', () {
      expect(
        SettingsConstants.defaultSettingsYaml,
        contains('input_device: default'),
      );
    });
  });
}
