import 'dart:io';
import 'package:flutter/material.dart';
import '../../services/hotkey_controller.dart';
import '../../services/update_service.dart';

class UpdateSection extends StatelessWidget {
  const UpdateSection(
      {super.key,
      required this.isZh,
      required this.onBusyChanged,
      this.service});
  final bool isZh;
  final ValueChanged<bool> onBusyChanged;
  final UpdateService? service;
  String tr(String zh, String en) => isZh ? zh : en;

  Future<void> _install(BuildContext context, UpdateService updater) async {
    final accepted = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
              title: Text(tr('升级到 ${updater.release!.version}',
                  'Update to ${updater.release!.version}')),
              content: Text(tr(
                  '将自动下载并校验安装包，然后请求系统管理员授权。安装期间不能录音，Fcitx5 可能重启。完成后请退出并重新打开 Nextalk。',
                  'The package will be downloaded and verified, then system authorization will be requested. Recording is unavailable during installation and Fcitx5 may restart. Quit and reopen Nextalk when finished.')),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: Text(tr('稍后', 'Later'))),
                FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: Text(tr('立即升级', 'Update now')))
              ],
            ));
    if (accepted != true || !context.mounted) return;
    onBusyChanged(true);
    try {
      await updater.install(
          canInstall: () =>
              HotkeyController.instance.state == HotkeyState.idle &&
              HotkeyController.instance.configurationOpen);
    } finally {
      if (context.mounted) onBusyChanged(false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final updater = service ?? UpdateService.instance;
    return ListenableBuilder(
        listenable: updater,
        builder: (context, _) {
          final release = updater.release;
          final status = switch (updater.phase) {
            UpdatePhase.idle => tr('检查是否有新版本', 'Check for a new version'),
            UpdatePhase.checking => tr('正在检查更新…', 'Checking for updates…'),
            UpdatePhase.available => tr('发现新版本 ${release?.version}',
                'Version ${release?.version} is available'),
            UpdatePhase.current =>
              tr('已是最新正式版本', 'You have the latest stable version'),
            UpdatePhase.downloading => tr('正在下载安装包…', 'Downloading update…'),
            UpdatePhase.verifying => tr('正在校验安装包…', 'Verifying update…'),
            UpdatePhase.installing => tr('等待系统授权或安装完成，请勿退出应用…',
                'Waiting for system authorization or installation. Keep the app open…'),
            UpdatePhase.installed => tr('升级成功，请退出并重新打开 Nextalk。',
                'Update installed. Quit and reopen Nextalk.'),
            UpdatePhase.failed => switch (updater.error) {
                'checksum' => tr('安装包校验失败，已阻止安装，请重试。',
                    'Package verification failed. Installation blocked. Please retry.'),
                'authorization' => tr('系统授权已取消或不可用，可重新尝试。',
                    'System authorization was cancelled or unavailable. Please retry.'),
                'recording' => tr('请结束录音或识别后再升级。',
                    'Finish recording or recognition before updating.'),
                'install' => tr('安装失败，请检查系统包管理器、权限或软件包锁后重试。',
                    'Installation failed. Check the package manager, permissions or package lock and retry.'),
                'download' => tr('下载失败，请检查网络后重试。',
                    'Download failed. Check your connection and retry.'),
                _ => tr('检查更新失败，请检查网络或稍后重试。',
                    'Update check failed. Check your connection or retry later.'),
              },
          };
          return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Divider(),
                ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(tr('版本与更新', 'Version and updates')),
                    subtitle: Text('Nextalk ${updater.currentVersion}')),
                SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title:
                        Text(tr('自动检查更新', 'Automatically check for updates')),
                    subtitle: Text(tr('每天检查正式版本，安装前由你确认',
                        'Check stable releases daily; ask before installing')),
                    value: updater.autoCheck,
                    onChanged:
                        updater.development ? null : updater.setAutoCheck),
                Semantics(
                    liveRegion: true,
                    child: Text(updater.development
                        ? tr('开发构建不支持自动升级，请使用正式安装包。',
                            'Automatic updates are disabled for development builds.')
                        : status)),
                if (updater.installing) ...[
                  const SizedBox(height: 12),
                  LinearProgressIndicator(
                      value: updater.phase == UpdatePhase.downloading
                          ? updater.progress
                          : null),
                ],
                const SizedBox(height: 12),
                Wrap(spacing: 12, runSpacing: 8, children: [
                  OutlinedButton(
                      onPressed: updater.busy ||
                              updater.development ||
                              updater.phase == UpdatePhase.installed
                          ? null
                          : () => updater.check(),
                      child: Text(tr('检查更新', 'Check for updates'))),
                  if (release != null && updater.phase != UpdatePhase.installed)
                    FilledButton(
                        onPressed: updater.busy || !release.canInstall
                            ? null
                            : () => _install(context, updater),
                        child: Text(tr('立即升级', 'Update now'))),
                  if (updater.phase == UpdatePhase.downloading)
                    TextButton(
                        onPressed: updater.cancelDownload,
                        child: Text(tr('取消下载', 'Cancel download'))),
                  TextButton(
                      onPressed: () async {
                        try {
                          await Process.start(
                              'xdg-open',
                              [
                                'https://github.com/gonewx/nextalk/releases/latest'
                              ],
                              mode: ProcessStartMode.detached);
                        } catch (_) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                                content: Text(tr(
                                    '无法打开浏览器，请访问 github.com/gonewx/nextalk/releases',
                                    'Cannot open browser. Visit github.com/gonewx/nextalk/releases'))));
                          }
                        }
                      },
                      child: Text(tr('发布页面', 'Release page'))),
                ]),
                if (release != null && !release.canInstall)
                  Text(tr('当前系统无兼容安装包或发布包缺少校验信息，请从发布页面手动更新。',
                      'No compatible package or checksum is available. Update manually from the release page.')),
                if (release != null && release.notes.isNotEmpty)
                  ExpansionTile(
                      tilePadding: EdgeInsets.zero,
                      title: Text(tr('更新说明', 'Release notes')),
                      children: [SelectableText(release.notes)]),
              ]);
        });
  }
}
