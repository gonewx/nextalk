import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import '../services/asr/deepseek_asr_client.dart';

/// 草稿与生效配置分离；测试仅使用当前输入快照。
class DeepSeekSettingsView extends StatefulWidget {
  const DeepSeekSettingsView(
      {super.key,
      required this.initialKey,
      required this.fromEnvironment,
      required this.isZh,
      required this.onSave,
      required this.onCancel,
      this.client});
  final String initialKey;
  final bool fromEnvironment;
  final bool isZh;
  final Future<void> Function(String) onSave;
  final VoidCallback onCancel;
  final DeepSeekAsrClient? client;
  @override
  State<DeepSeekSettingsView> createState() => _DeepSeekSettingsViewState();
}

class _DeepSeekSettingsViewState extends State<DeepSeekSettingsView> {
  late final TextEditingController _key =
      TextEditingController(text: widget.initialKey);
  late final DeepSeekAsrClient _client = widget.client ?? DeepSeekAsrClient();
  CancelToken? _test;
  bool _obscure = true;
  bool _saving = false;
  bool _success = false;
  String? _message;
  int _revision = 0;
  String tr(String zh, String en) => widget.isZh ? zh : en;
  bool get _valid =>
      _key.text.trim().isNotEmpty &&
      !_key.text.contains('\n') &&
      !_key.text.contains('\r');

  void _edited(String _) {
    _revision++;
    _test?.cancel();
    setState(() {
      _test = null;
      _message = null;
      _success = false;
    });
  }

  Future<void> _testConnection() async {
    final revision = ++_revision;
    final token = CancelToken();
    setState(() {
      _test = token;
      _message = null;
      _success = false;
    });
    try {
      await _client.testConnection(_key.text.trim(), cancelToken: token);
      if (!mounted || revision != _revision) return;
      setState(() {
        _success = true;
        _message = tr('连接成功，API Key 可用', 'Connected. API key is valid.');
      });
    } on DeepSeekException catch (e) {
      if (!mounted || revision != _revision) return;
      setState(() => _message = e.message(widget.isZh));
    } catch (_) {
      if (!mounted || revision != _revision) return;
      setState(() => _message =
          tr('测试失败，请检查网络后重试', 'Test failed. Check your network and retry.'));
    } finally {
      if (mounted && revision == _revision) setState(() => _test = null);
    }
  }

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _message = null;
      _success = false;
    });
    try {
      await widget.onSave(_key.text.trim());
    } catch (_) {
      if (mounted) {
        setState(() => _message = tr('保存失败，请重试', 'Save failed. Please retry.'));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    _revision++;
    _test?.cancel();
    _key.dispose();
    if (widget.client == null) _client.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF1A1A1A),
      padding: const EdgeInsets.all(24),
      child: SingleChildScrollView(
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(tr('DeepSeek 云端识别', 'DeepSeek Cloud Recognition'),
            style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        Text(tr('停止录音后上传至 DeepSeek，最长 120 秒，无实时文字预览。',
            'Audio is uploaded to DeepSeek after recording. Maximum 120 seconds; no live transcript.')),
        const SizedBox(height: 20),
        TextField(
            controller: _key,
            obscureText: _obscure,
            enabled: !_saving,
            autocorrect: false,
            enableSuggestions: false,
            onChanged: _edited,
            decoration: InputDecoration(
                labelText: 'API Key',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                    tooltip: tr('显示／隐藏密钥', 'Show / hide key'),
                    onPressed: () => setState(() => _obscure = !_obscure),
                    icon: Icon(
                        _obscure ? Icons.visibility : Icons.visibility_off)))),
        const SizedBox(height: 8),
        Text(widget.fromEnvironment
            ? tr('当前来源：环境变量。保存后将使用此处配置。',
                'Source: environment. Saving overrides it with this configuration.')
            : tr('密钥保存在当前用户的 Nextalk 配置中。',
                'The key is saved in your Nextalk user configuration.')),
        const SizedBox(height: 16),
        Text(tr('测试会上传 1 秒静音，产生少量 API 用量，不使用麦克风。',
            'Testing uploads 1 second of silence and incurs a small API usage charge. No microphone is used.')),
        const SizedBox(height: 12),
        OutlinedButton(
            onPressed:
                _valid && !_saving && _test == null ? _testConnection : null,
            child: Text(_test != null
                ? tr('正在测试…', 'Testing…')
                : tr('测试连接', 'Test connection'))),
        if (_test != null) const LinearProgressIndicator(),
        if (_message != null)
          Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Text(_message!,
                  key: const ValueKey('deepseek-status'),
                  style: TextStyle(
                      color: _success
                          ? Colors.greenAccent
                          : Colors.orangeAccent))),
        const SizedBox(height: 16),
        Wrap(alignment: WrapAlignment.end, spacing: 12, children: [
          TextButton(
              onPressed: _saving ? null : widget.onCancel,
              child: Text(tr('取消', 'Cancel'))),
          FilledButton(
              onPressed: _valid && !_saving && _test == null ? _save : null,
              child: Text(_saving
                  ? tr('正在保存…', 'Saving…')
                  : tr('保存配置', 'Save configuration'))),
        ]),
      ])),
    );
  }
}
