import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../constants/settings_constants.dart';
import '../../services/model_manager.dart';
import '../../services/audio_device_service.dart';
import '../../services/settings_service.dart';
import '../../services/language_service.dart';
import '../../services/hotkey_service.dart';
import '../../services/tray_service.dart';
import '../deepseek_settings_view.dart';
import '../init_wizard/init_wizard.dart';
import 'model_selection_view.dart';
import 'recording_blocked_notice.dart';
import 'update_section.dart';

/// 所有模型的配置、下载和选择共用一个普通窗口。
class SettingsWindow extends StatefulWidget {
  const SettingsWindow(
      {super.key,
      required this.modelManager,
      required this.onClose,
      this.initialEngine,
      this.initialGeneral = false,
      this.notice,
      this.recordingRequested = false,
      this.recordingHintRevision = 0,
      this.onDismissRecordingHint,
      required this.onBusyChanged});
  final ModelManager modelManager;
  final VoidCallback onClose;
  final EngineType? initialEngine;
  final bool initialGeneral;
  final String? notice;
  final bool recordingRequested;
  final int recordingHintRevision;
  final VoidCallback? onDismissRecordingHint;
  final ValueChanged<bool> onBusyChanged;
  @override
  State<SettingsWindow> createState() => _SettingsWindowState();
}

class _SettingsWindowState extends State<SettingsWindow> {
  late EngineType? _detail = widget.initialEngine;
  bool _busy = false;
  late bool _general = widget.initialGeneral;
  String? _message;
  EngineType? _loadingEngine;
  bool _messageError = false;
  List<AudioInputDevice>? _devices;
  void _setBusy(bool value) {
    widget.onBusyChanged(value);
    if (mounted) setState(() => _busy = value);
  }

  bool get isZh => LanguageService.instance.isZh;
  String tr(String zh, String en) => isZh ? zh : en;

  Future<void> _select(EngineType type) async {
    if (_busy || !widget.modelManager.isEngineReady(type)) return;
    _setBusy(true);
    setState(() {
      _message = null;
      _messageError = false;
      _loadingEngine = type;
    });
    // 先绘制加载状态，再进入可能阻塞 UI isolate 的本地模型初始化。
    await WidgetsBinding.instance.endOfFrame;
    await Future<void>.delayed(const Duration(milliseconds: 20));
    try {
      final success = await SettingsService.instance.switchEngineType(type);
      await TrayService.instance.rebuildMenu();
      if (!mounted) return;
      _messageError = !success;
      setState(() => _message = success
          ? tr('已切换到 ', 'Switched to ') + modelName(type)
          : tr('切换失败，请检查模型后重试。', 'Switch failed. Check the model and retry.'));
    } catch (_) {
      _messageError = true;
      if (mounted) {
        setState(
            () => _message = tr('切换失败，请重试。', 'Switch failed. Please retry.'));
      }
    } finally {
      if (mounted) {
        _loadingEngine = null;
        _setBusy(false);
      }
    }
  }

  // 为鼠标与键盘操作提供同样清晰的反馈，禁用控件不响应悬浮。
  static final _interactionStyle = ButtonStyle(
    animationDuration: const Duration(milliseconds: 120),
    overlayColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.disabled)) return Colors.transparent;
      if (states.contains(WidgetState.pressed)) return const Color(0x40EF5350);
      if (states.contains(WidgetState.hovered) ||
          states.contains(WidgetState.focused)) {
        return const Color(0x28FFFFFF);
      }
      return Colors.transparent;
    }),
    mouseCursor: WidgetStateProperty.resolveWith((states) =>
        states.contains(WidgetState.disabled)
            ? SystemMouseCursors.basic
            : SystemMouseCursors.click),
  );

  @override
  Widget build(BuildContext context) => Theme(
      data: Theme.of(context).copyWith(
        textButtonTheme: TextButtonThemeData(style: _interactionStyle),
        outlinedButtonTheme: OutlinedButtonThemeData(
            style: _interactionStyle.copyWith(
          side: WidgetStateProperty.resolveWith((states) => BorderSide(
              color: states.contains(WidgetState.disabled)
                  ? Colors.white12
                  : states.contains(WidgetState.hovered) ||
                          states.contains(WidgetState.focused)
                      ? const Color(0xFFEF9A9A)
                      : Colors.white38)),
        )),
        filledButtonTheme: FilledButtonThemeData(style: _interactionStyle),
        elevatedButtonTheme: ElevatedButtonThemeData(style: _interactionStyle),
        iconButtonTheme: IconButtonThemeData(style: _interactionStyle),
        hoverColor: const Color(0x24FFFFFF),
      ),
      child: Material(
          color: const Color(0xFF1A1A1A),
          child: LayoutBuilder(builder: (context, constraints) {
            final scale = MediaQuery.textScalerOf(context).scale(14) / 14;
            // 短窗口/大字体下让整个外壳滚动，正文仍保有独立的有限高度。
            final minimumHeight = (widget.recordingRequested ? 640.0 : 380.0) *
                math.max(1.0, scale);
            return SingleChildScrollView(
                child: SizedBox(
                    height: math.max(constraints.maxHeight, minimumHeight),
                    child: Align(
                        alignment: Alignment.topCenter,
                        child: ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 1040),
                            child: _buildFrame(context)))));
          })));

  Widget _buildFrame(BuildContext context) => Column(children: [
        Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            child: Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 24,
                runSpacing: 8,
                children: [
                  Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.graphic_eq, color: Color(0xFFEF5350)),
                    const SizedBox(width: 10),
                    const Text('Nextalk',
                        style: TextStyle(
                            fontSize: 18, fontWeight: FontWeight.bold)),
                  ]),
                  Wrap(spacing: 8, children: [
                    TextButton(
                        onPressed: _busy
                            ? null
                            : () => setState(() {
                                  _detail = null;
                                  _general = false;
                                  _message = null;
                                }),
                        child: Text(tr('模型选择', 'Models'))),
                    TextButton(
                        onPressed: _busy
                            ? null
                            : () => setState(() {
                                  _detail = null;
                                  _general = true;
                                }),
                        child: Text(tr('设置', 'Settings'))),
                  ]),
                ])),
        const Divider(height: 1),
        if (widget.recordingRequested)
          RecordingBlockedNotice(
              key: ValueKey(widget.recordingHintRevision),
              isZh: isZh,
              busy: _busy,
              editing: _detail != null,
              modelReady: widget.modelManager
                  .isEngineReady(SettingsService.instance.actualEngineType),
              onCloseSettings: widget.onClose,
              onDismiss: widget.onDismissRecordingHint),
        if (_busy) const LinearProgressIndicator(),
        if (_loadingEngine != null)
          Padding(
              padding: const EdgeInsets.all(16),
              child: Row(children: [
                const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2)),
                const SizedBox(width: 12),
                Expanded(
                    child: Text(
                        tr('正在加载 ${modelName(_loadingEngine!)}，请稍候…',
                            'Loading ${modelName(_loadingEngine!)}. Please wait…'),
                        key: const ValueKey('model-loading-status'))),
              ])),
        if (_detail != null)
          Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(children: [
                TextButton.icon(
                    onPressed:
                        _busy ? null : () => setState(() => _detail = null),
                    icon: const Icon(Icons.arrow_back, size: 18),
                    label: Text(tr('模型选择', 'Models'))),
                const SizedBox(width: 12),
                Expanded(child: Text(modelName(_detail!))),
              ])),
        if (widget.notice != null)
          Padding(
              padding: const EdgeInsets.all(12),
              child: Text(widget.notice!,
                  style: const TextStyle(color: Colors.orangeAccent))),
        if (_message != null)
          Padding(
              padding: const EdgeInsets.all(12),
              child: Semantics(
                  liveRegion: true,
                  child: Row(children: [
                    Icon(
                        _messageError
                            ? Icons.error_outline
                            : Icons.check_circle_outline,
                        color: _messageError
                            ? Colors.orangeAccent
                            : Colors.greenAccent,
                        size: 20),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_message!)),
                  ]))),
        Expanded(
            child: _detail == EngineType.deepseek
                ? DeepSeekSettingsView(
                    initialKey: SettingsService.instance.deepseekApiKey,
                    fromEnvironment:
                        SettingsService.instance.deepseekKeyFromEnvironment,
                    isZh: isZh,
                    onSave: (key) async {
                      _setBusy(true);
                      try {
                        await SettingsService.instance.saveDeepSeekApiKey(key);
                        if (mounted) {
                          setState(() {
                            _detail = null;
                            _message = tr('配置已保存，可在列表中选择 DeepSeek。',
                                'Configuration saved. Select DeepSeek from the list.');
                          });
                        }
                      } finally {
                        if (mounted) _setBusy(false);
                      }
                    },
                    onCancel: () => setState(() => _detail = null),
                  )
                : _detail != null
                    ? InitWizard(
                        key: ValueKey(_detail),
                        modelManager: widget.modelManager,
                        targetEngineType: _detail,
                        embedded: true,
                        onBusyChanged: _setBusy,
                        onCompleted: () => setState(() {
                          _detail = null;
                          _message = tr('下载完成，请选择要使用的模型。',
                              'Download complete. Select a model to use.');
                        }),
                      )
                    : _general
                        ? _settings()
                        : ModelSelectionView(
                            isZh: isZh,
                            selected: SettingsService.instance.actualEngineType,
                            readiness: {
                              for (final type in EngineType.values)
                                type: widget.modelManager.isEngineReady(type)
                            },
                            busy: _busy,
                            loading: _loadingEngine,
                            onSelect: _select,
                            onManage: (type) => setState(() {
                                  _detail = type;
                                  _message = null;
                                }))),
        const Divider(height: 1),
        Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
            child: Row(children: [
              Expanded(
                  child: Text(
                      tr('配置或下载不会自动切换模型',
                          'Configuring or downloading does not switch models'),
                      style: const TextStyle(
                          color: Colors.white54, fontSize: 12))),
              TextButton(
                  onPressed: _busy ? null : widget.onClose,
                  child: Text(tr('完成', 'Done'))),
            ])),
      ]);

  Widget _audioSettings() {
    _devices ??= AudioDeviceService.instance.listInputDevices();
    final current = SettingsService.instance.audioInputDevice;
    final names = <String, String>{
      'default': tr('系统默认', 'System default'),
      for (final d in _devices!) d.description: d.description
    };
    names.putIfAbsent(current, () => '$current (${tr('不可用', 'unavailable')})');
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      ListTile(
          title: Text(tr('录音设备', 'Audio input')),
          subtitle: Text(tr('下次录音生效', 'Applies to the next recording')),
          trailing: IconButton(
              tooltip: tr('刷新设备', 'Refresh devices'),
              icon: const Icon(Icons.refresh),
              onPressed: () => setState(() {
                    _devices = AudioDeviceService.instance
                        .listInputDevices(forceRefresh: true);
                  }))),
      DropdownButtonFormField<String>(
          // 发布镜像使用 Flutter 3.32，尚不支持 initialValue。
          // ignore: deprecated_member_use
          value: current,
          isExpanded: true,
          items: [
            for (final e in names.entries)
              DropdownMenuItem(
                  value: e.key,
                  child: Text(e.value, overflow: TextOverflow.ellipsis))
          ],
          onChanged: (value) async {
            if (value == null) return;
            await SettingsService.instance.setAudioInputDevice(value);
            await TrayService.instance.rebuildMenu();
            if (mounted) setState(() {});
          }),
    ]);
  }

  Widget _settingControl(
          {required Widget title, Widget? subtitle, required Widget control}) =>
      LayoutBuilder(builder: (context, constraints) {
        final scale = MediaQuery.textScalerOf(context).scale(14) / 14;
        if (constraints.maxWidth < 560 * scale) {
          return Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    title,
                    if (subtitle != null) subtitle,
                    const SizedBox(height: 8),
                    control,
                  ]));
        }
        return ListTile(
            title: title,
            subtitle: subtitle,
            trailing: SizedBox(width: 180, child: control));
      });

  Widget _settings() => ListView(padding: const EdgeInsets.all(24), children: [
        Text(tr('设置', 'Settings'),
            style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 24),
        _settingControl(
            title: Text(tr('界面语言', 'Language')),
            control: DropdownButton<String>(
                isExpanded: true,
                value: isZh ? 'zh' : 'en',
                items: const [
                  DropdownMenuItem(value: 'zh', child: Text('简体中文')),
                  DropdownMenuItem(value: 'en', child: Text('English'))
                ],
                onChanged: (value) async {
                  if (value == null) return;
                  await LanguageService.instance.switchLanguage(value);
                  await TrayService.instance.rebuildMenu();
                  if (mounted) setState(() {});
                })),
        _settingControl(
            title: Text(tr('Zipformer 模型版本', 'Zipformer variant')),
            subtitle: Text(tr('更改后重启应用生效', 'Restart the app to apply')),
            control: DropdownButton<ModelType>(
                isExpanded: true,
                value: SettingsService.instance.modelType,
                items: const [
                  DropdownMenuItem(value: ModelType.int8, child: Text('INT8')),
                  DropdownMenuItem(
                      value: ModelType.standard, child: Text('Standard'))
                ],
                onChanged: (value) async {
                  if (value == null) return;
                  await SettingsService.instance.switchModelType(value);
                  if (mounted) setState(() {});
                })),
        ListTile(
            title: Text(tr('快捷键', 'Shortcut')),
            subtitle: Text(LanguageService.instance.tr(
                HotkeyService.instance.hotkeyMode == HotkeyMode.portal
                    ? 'tray_hotkey_mode_portal'
                    : 'tray_hotkey_mode_system'))),
        _audioSettings(),
        UpdateSection(isZh: isZh, onBusyChanged: _setBusy),
        const SizedBox(height: 16),
        const Divider(),
        ListTile(
            title: Text(tr('高级配置', 'Advanced configuration')),
            subtitle: Text(tr('音频、快捷键与识别参数等完整配置',
                'Full audio, shortcut and recognition settings')),
            trailing: const Icon(Icons.open_in_new),
            onTap: () async {
              await Directory(SettingsConstants.configDir)
                  .create(recursive: true);
              await Process.run('xdg-open', [SettingsConstants.configDir]);
            }),
      ]);
}
