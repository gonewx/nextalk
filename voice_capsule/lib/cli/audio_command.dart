import 'dart:io';
import '../services/audio_device_service.dart';
import '../services/settings_service.dart';
import '../services/language_service.dart';

// ignore_for_file: avoid_print

/// Story 3-9: CLI audio 子命令处理器 (AC4-13)
///
/// 使用方法:
/// - nextalk audio              交互模式
/// - nextalk audio <序号>       直接设置设备
/// - nextalk audio default      恢复默认设备
/// - nextalk audio list         机器可读格式输出
/// - nextalk audio help         显示帮助
class AudioCommand {
  AudioCommand._();

  /// 执行 audio 命令
  /// 返回退出码: 0=成功, 1=错误
  static Future<int> execute(List<String> args) async {
    // 初始化设置服务
    await SettingsService.instance.initialize();
    await LanguageService.instance.initialize();

    final lang = LanguageService.instance;

    if (args.isEmpty) {
      // 交互模式 (AC4)
      return await _interactiveMode(lang);
    }

    final arg = args[0];

    // help / --help / -h (AC13)
    if (arg == 'help' || arg == '--help' || arg == '-h') {
      _printHelp(lang);
      return 0;
    }

    // list / --list / -l (AC11)
    if (arg == 'list' || arg == '--list' || arg == '-l') {
      return _listDevices();
    }

    // default (AC12)
    if (arg == 'default') {
      return await _setDefaultDevice(lang);
    }

    // 数字索引 (AC9, AC10)
    final index = int.tryParse(arg);
    if (index != null) {
      return await _setDeviceByIndex(index, lang);
    }

    // 无效参数
    _printError(lang.isZh ? '无效参数: $arg' : 'Invalid argument: $arg');
    _printHelp(lang);
    return 1;
  }

  /// 交互模式 (AC4)
  static Future<int> _interactiveMode(LanguageService lang) async {
    // 检查是否支持交互 (stdin.hasTerminal)
    if (!stdin.hasTerminal) {
      _printError(lang.isZh
          ? '当前环境不支持交互模式，请使用 nextalk audio <序号>'
          : 'Interactive mode not supported, use: nextalk audio <number>');
      return 1;
    }

    final devices = AudioDeviceService.instance.listInputDevices();
    var currentDevice = SettingsService.instance.audioInputDevice;

    _printInteractiveHeader(lang);
    _printDeviceList(devices, currentDevice, lang);
    _printCurrentConfig(devices, currentDevice, lang);
    _printInteractiveFooter(lang);

    // 交互循环，直到用户输入 q 退出
    while (true) {
      stdout.write(lang.isZh ? '请选择: ' : 'Choose: ');
      final input = stdin.readLineSync()?.trim();

      if (input == null || input.isEmpty) {
        continue; // 空输入，继续等待
      }

      // q / quit (AC8)
      if (input == 'q' || input == 'quit') {
        return 0;
      }

      // default (AC7)
      if (input == 'default') {
        final result = await _setDefaultDevice(lang);
        if (result == 0) {
          currentDevice = 'default';
        }
        continue;
      }

      // 数字索引 (AC6)
      final index = int.tryParse(input);
      if (index == null) {
        _printError(lang.isZh
            ? '无效输入: $input'
            : 'Invalid input: $input');
        continue;
      }

      final result = await _setDeviceByIndex(index, lang, devices: devices);
      if (result == 0 && index >= 0 && index < devices.length) {
        currentDevice = devices[index].name;
      }
      // 设置成功后继续循环，用户可以按 q 退出
    }
  }

  /// 打印交互模式头部
  static void _printInteractiveHeader(LanguageService lang) {
    print('');
    print(lang.isZh
        ? 'Nextalk 音频设备配置'
        : 'Nextalk Audio Device Configuration');
    print('=' * 40);
    print('');
    print(lang.isZh ? '可用输入设备:' : 'Available input devices:');
  }

  /// 打印设备列表 (AC5)
  static void _printDeviceList(
    List<AudioInputDevice> devices,
    String currentDevice,
    LanguageService lang,
  ) {
    if (devices.isEmpty) {
      print(lang.isZh
          ? '  (未检测到音频输入设备)'
          : '  (No audio input devices detected)');
      return;
    }

    for (int i = 0; i < devices.length; i++) {
      final device = devices[i];
      final statusIcon = device.status == DeviceAvailability.available
          ? '✓'
          : '⚠️';
      final statusText = device.status == DeviceAvailability.available
          ? ''
          : (lang.isZh ? ' 不可用' : ' unavailable');

      // 当前设备标记
      final currentMark = _isCurrentDevice(device.name, currentDevice)
          ? (lang.isZh ? ' (当前)' : ' (current)')
          : '';

      // 使用 description 显示，更友好
      print('  [$i] ${device.description}  $statusIcon$statusText$currentMark');
    }
  }

  /// 打印当前配置状态
  static void _printCurrentConfig(
    List<AudioInputDevice> devices,
    String currentDevice,
    LanguageService lang,
  ) {
    print('');

    if (currentDevice == 'default') {
      print(lang.isZh
          ? '当前配置: 系统默认设备'
          : 'Current config: System default device');
    } else {
      // 查找当前配置的设备
      final matchedDevice = devices.where(
        (d) => _isCurrentDevice(d.name, currentDevice),
      ).firstOrNull;

      if (matchedDevice != null) {
        final statusText = matchedDevice.status == DeviceAvailability.available
            ? (lang.isZh ? '✓ 可用' : '✓ Available')
            : (lang.isZh ? '⚠️ 不可用' : '⚠️ Unavailable');
        print(lang.isZh
            ? '当前配置: ${matchedDevice.description}'
            : 'Current config: ${matchedDevice.description}');
        print(lang.isZh ? '状态: $statusText' : 'Status: $statusText');
      } else {
        print(lang.isZh
            ? '当前配置: $currentDevice (设备不存在)'
            : 'Current config: $currentDevice (device not found)');
      }
    }
  }

  /// 打印交互模式底部
  static void _printInteractiveFooter(LanguageService lang) {
    print('');
    print('─' * 40);
    print(lang.isZh
        ? '  输入数字选择设备 | default 恢复默认 | q 退出'
        : '  Enter number to select | default to reset | q to quit');
    print('');
  }

  /// 设置默认设备 (AC7, AC12)
  static Future<int> _setDefaultDevice(LanguageService lang) async {
    await SettingsService.instance.setAudioInputDevice('default');
    print(lang.isZh
        ? '✅ 已恢复默认设置，重启应用后生效'
        : '✅ Reset to default, restart app to take effect');
    return 0;
  }

  /// 按索引设置设备 (AC6, AC9, AC10)
  static Future<int> _setDeviceByIndex(
    int index,
    LanguageService lang, {
    List<AudioInputDevice>? devices,
  }) async {
    final deviceList = devices ?? AudioDeviceService.instance.listInputDevices();

    // 检查索引有效性 (AC10)
    if (index < 0 || index >= deviceList.length) {
      _printError(lang.isZh
          ? '无效的设备序号: $index (有效范围: 0-${deviceList.length - 1})'
          : 'Invalid device index: $index (valid range: 0-${deviceList.length - 1})');
      return 1;
    }

    final device = deviceList[index];
    await SettingsService.instance.setAudioInputDevice(device.name);

    print(lang.isZh
        ? '✅ 设备已设置为: ${device.name}，重启应用后生效'
        : '✅ Device set to: ${device.name}, restart app to take effect');
    return 0;
  }

  /// 机器可读格式输出 (AC11)
  static int _listDevices() {
    // 先枚举设备（这会产生 ALSA/JACK 警告到 stderr）
    final devices = AudioDeviceService.instance.listInputDevices();
    final currentDevice = SettingsService.instance.audioInputDevice;

    // 输出标记行，方便脚本解析时跳过警告
    print('# DEVICES');
    for (int i = 0; i < devices.length; i++) {
      final device = devices[i];
      final status = device.status == DeviceAvailability.available
          ? 'available'
          : 'busy';
      final current = _isCurrentDevice(device.name, currentDevice) ? '*' : '';

      // 格式: <序号>\t<设备名称>\t<状态>\t<是否当前>
      print('$i\t${device.name}\t$status\t$current');
    }
    print('# END');

    return 0;
  }

  /// 打印帮助信息 (AC13)
  static void _printHelp(LanguageService lang) {
    if (lang.isZh) {
      print('''
Nextalk 音频设备配置

用法:
  nextalk audio              进入交互模式
  nextalk audio <序号>       设置指定设备
  nextalk audio default      恢复默认设备
  nextalk audio list         机器可读格式输出
  nextalk audio help         显示此帮助

示例:
  nextalk audio              交互选择设备
  nextalk audio 0            设置第一个设备
  nextalk audio default      使用系统默认设备

提示:
  抑制警告信息: nextalk audio list 2>/dev/null
''');
    } else {
      print('''
Nextalk Audio Device Configuration

Usage:
  nextalk audio              Interactive mode
  nextalk audio <number>     Set specified device
  nextalk audio default      Reset to default device
  nextalk audio list         Machine-readable output
  nextalk audio help         Show this help

Examples:
  nextalk audio              Interactive device selection
  nextalk audio 0            Set first device
  nextalk audio default      Use system default device

Tips:
  Suppress warnings: nextalk audio list 2>/dev/null
''');
    }
  }

  /// 判断设备是否为当前配置
  static bool _isCurrentDevice(String deviceName, String currentConfig) {
    if (currentConfig == 'default') return false;
    return deviceName == currentConfig ||
        deviceName.contains(currentConfig) ||
        currentConfig.contains(deviceName);
  }

  /// 打印错误信息
  static void _printError(String message) {
    stderr.writeln('❌ $message');
  }
}
