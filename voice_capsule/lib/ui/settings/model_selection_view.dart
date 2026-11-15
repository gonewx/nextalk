import 'package:flutter/material.dart';
import '../../constants/settings_constants.dart';

String modelName(EngineType type) => switch (type) {
      EngineType.deepseek => 'DeepSeek',
      EngineType.qwen3Asr => 'Qwen3-ASR',
      EngineType.zipformer => 'Zipformer',
      EngineType.sensevoice => 'SenseVoice',
    };

/// 选择与管理分开：未就绪的条目仍可配置，但不能选中。
class ModelSelectionView extends StatelessWidget {
  const ModelSelectionView(
      {super.key,
      required this.isZh,
      required this.selected,
      required this.readiness,
      required this.onSelect,
      required this.onManage,
      this.busy = false,
      this.loading});
  final bool isZh;
  final EngineType selected;
  final Map<EngineType, bool> readiness;
  final ValueChanged<EngineType> onSelect;
  final ValueChanged<EngineType> onManage;
  final bool busy;
  final EngineType? loading;
  String tr(String zh, String en) => isZh ? zh : en;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(tr('模型选择', 'Model selection'),
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
              tr('选择已就绪的模型。首次使用请先配置云端服务或下载本地模型。',
                  'Select a ready model. Configure cloud access or download a local model first.'),
              style: const TextStyle(color: Colors.white60)),
          const SizedBox(height: 24),
          for (final type in [
            EngineType.qwen3Asr,
            EngineType.deepseek,
            EngineType.zipformer,
            EngineType.sensevoice
          ])
            _row(context, type),
        ],
      );

  Widget _row(BuildContext context, EngineType type) {
    final isLoading = loading == type;
    final ready = readiness[type] ?? false;
    final active = selected == type && ready;
    final cloud = type == EngineType.deepseek;
    final description = switch (type) {
      EngineType.deepseek =>
        tr('云端 · 录音结束后识别', 'Cloud · Transcribe after recording'),
      EngineType.qwen3Asr => tr('本地 · 高精度识别', 'Local · High accuracy'),
      EngineType.zipformer =>
        tr('本地 · 实时流式识别', 'Local · Streaming recognition'),
      EngineType.sensevoice =>
        tr('本地 · 多语言识别', 'Local · Multilingual recognition'),
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      // InkWell 必须绘制在卡片自身的 Material 上，否则反馈会被不透明背景遮挡。
      child: Material(
        color: active ? const Color(0xFF352326) : const Color(0xFF242424),
        clipBehavior: Clip.antiAlias,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
                color: active ? const Color(0xFFEF5350) : Colors.white12)),
        child: LayoutBuilder(builder: (context, constraints) {
          final scale = MediaQuery.textScalerOf(context).scale(14) / 14;
          final compact = constraints.maxWidth < 520 * scale;
          final selection = Semantics(
              selected: active,
              enabled: ready && !busy,
              button: true,
              child: InkWell(
                key: ValueKey('select-${type.name}'),
                mouseCursor: ready && !busy
                    ? SystemMouseCursors.click
                    : SystemMouseCursors.forbidden,
                hoverColor: const Color(0x24FFFFFF),
                focusColor: const Color(0x30EF5350),
                splashColor: const Color(0x40EF5350),
                borderRadius: BorderRadius.circular(12),
                onTap: ready && !busy ? () => onSelect(type) : null,
                child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(children: [
                      if (isLoading)
                        const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(strokeWidth: 2))
                      else
                        Icon(
                            active
                                ? Icons.radio_button_checked
                                : Icons.radio_button_off,
                            color: active
                                ? const Color(0xFFEF5350)
                                : ready
                                    ? Colors.white60
                                    : Colors.white24),
                      const SizedBox(width: 14),
                      Expanded(
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                            Text(modelName(type),
                                style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w600,
                                    color:
                                        ready ? Colors.white : Colors.white38)),
                            const SizedBox(height: 5),
                            Text(description,
                                style: TextStyle(
                                    fontSize: 12,
                                    color: ready
                                        ? Colors.white60
                                        : Colors.white38)),
                            const SizedBox(height: 5),
                            Text(
                                isLoading
                                    ? tr('正在加载…', 'Loading…')
                                    : active
                                        ? tr('当前使用', 'In use')
                                        : ready
                                            ? tr('已就绪', 'Ready')
                                            : cloud
                                                ? tr('未配置', 'Not configured')
                                                : tr('未下载完整',
                                                    'Download required'),
                                style: TextStyle(
                                    fontSize: 12,
                                    color: active
                                        ? const Color(0xFFEF9A9A)
                                        : Colors.white54)),
                          ])),
                    ])),
              ));
          final manage = Padding(
              padding: const EdgeInsets.only(right: 16),
              child: OutlinedButton(
                  key: ValueKey('manage-${type.name}'),
                  onPressed: busy ? null : () => onManage(type),
                  child: Text(cloud
                      ? tr('配置', 'Configure')
                      : ready
                          ? tr('管理', 'Manage')
                          : tr('下载', 'Download'))));
          return compact
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                      selection,
                      Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Align(
                              alignment: Alignment.centerRight, child: manage)),
                    ])
              : Row(children: [Expanded(child: selection), manage]);
        }),
      ),
    );
  }
}
