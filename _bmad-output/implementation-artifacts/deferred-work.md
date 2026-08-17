# Deferred Work

## Deferred from: code review of 3-10-portal-global-shortcuts (2026-07-09)

- **app_id 持久化未验证（AC3）**：CreateSession 未设 .desktop app_id，非 Flatpak 裸二进制上 KDE 能否按 app_id 跨重启记忆用户绑定未经真机验证。与 AC8 注册成功分支一并待验。
- **D-Bus 连接断开无检测/重连**：连接断开=session 销毁=快捷键静默失效，但 hotkeyMode 仍显示 portal，UI 与实际状态可能永久不一致。属增强，超本 story 范围。
- **register/dispose 并发守卫**：`_registerAttempted` 守卫位于首个 await 前，dispose 与后台 register 理论可并发导致 use-after-dispose 或误返回 failed。当前仅 `_setupPortalHotkey` 单一调用点，无实际并发 reachability。
- **AC6 回归测试保真度**：双触发测试在测试内本地重建 `guardedToggle` 闭包，未驱动真实 `HotkeyController.toggle()`。两路径确收敛同一入口，风险低，但可补真实集成测试。
- **AC8 注册成功分支真机验证**：KDE 5.27+/6.x、GNOME 48+ 的注册成功路径未在真机验证（无支持环境）；仅降级分支在本机 Ubuntu 24.04+GNOME 46 验证通过。

- source_spec: `_bmad-output/implementation-artifacts/spec-fix-hotkey-recognition-latency.md`
  summary: onModelSwitch/onEngineSwitch 回调无串行化，快速连续切换存在 dispose 竞态（既有问题）
  evidence: 回调为 async 且可被托盘连点触发；switchEngine 会 dispose 旧引擎并替换全局 _asrEngine，与进行中的另一次切换/预热可能交错（本次已将 warmup 改为接收局部 engine 参数缓解，但回调级互斥仍缺失）
- source_spec: `_bmad-output/implementation-artifacts/spec-fix-hotkey-recognition-latency.md`
  summary: main.dart 顶层私有函数（_preInitializeEngine 等）不可单测，预初始化三态（null/已初始化/未初始化）与切换后重预热链路缺测试
  evidence: 审查确认风险最高的行为改动无直接测试覆盖；需可测性重构（提取到 service）后补测
- source_spec: `_bmad-output/implementation-artifacts/spec-fix-hotkey-recognition-latency.md`
  summary: 单元测试将 PortalHotkey 日志写入真实 ~/.local/share/nextalk/logs/diagnostic.log（测试未隔离 DiagnosticLogger）
  evidence: 用户诊断日志中出现 2026-07-09 17:23:29 毫秒级密集的 "bind boom"/"unsupported" 等测试桩记录，污染真机排障信号
- source_spec: `_bmad-output/implementation-artifacts/spec-fix-fedora-inject-clipboard-fallback.md`
  summary: GNOME 注入扩展的 D-Bus CommitText 对 session bus 上任意同用户进程开放，无调用方校验，应评估 sender 校验或在安全文档中显式声明风险边界
  evidence: 对抗评审发现（blind-hunter #2）：任何有 session bus 访问权的进程可向焦点窗口注入文本；同用户非沙箱进程本就有等价能力、Flatpak 默认无 org.gnome.Shell talk 权限，故降级为文档/加固课题而非本 spec 阻塞项
- source_spec: `_bmad-output/implementation-artifacts/spec-fix-fedora-inject-clipboard-fallback.md`
  summary: hotkey_controller 提交编排（隐藏窗口/等焦点/中断/失败恢复窗口→剪贴板）缺单测，需为 WindowService/TrayService 单例引入可注入缝隙后补编排级测试
  evidence: 对抗评审发现（blind-hunter #7）：fcitx 与 GNOME 两条编排路径均零覆盖；受限于 WindowService.instance 静态单例（先于本 story 存在的可测性限制），需先做 DI 改造，超出本 spec 范围

## Deferred from: review of spec-gh-4-fix-sensevoice-accumulation (2026-08-13)

- source_spec: `_bmad-output/implementation-artifacts/spec-gh-4-fix-sensevoice-accumulation.md`
  summary: VAD 自动停止模式（autoStopOnEndpoint: true）下端点触发后 stop() 返回值回归为空
  evidence: _handleEndpoint 先调 finalizeUtterance() 清空 _lastResult，stop() 的 _vadTriggeredStop 分支改走 getResult() 返回空；SenseVoice 仅是对齐 Zipformer 自 38e9e9c 起的既有行为，且仅限端点触发后到采集循环清理（~300ms）的竞态窗口；生产 PTT 配置（main.dart）不受影响
- source_spec: `_bmad-output/implementation-artifacts/spec-gh-4-fix-sensevoice-accumulation.md`
  summary: 设备丢失路径二次调用 finalizeUtterance()，违反「一次发话只调用一次」契约，stop() 返回值变空
  evidence: _handleDeviceLost 先收尾取文本，用户随后松键 stop() 再收尾返回空；对 Zipformer 同样存在（38e9e9c 设计），文本已经设备丢失事件提交，不影响用户体验
- source_spec: `_bmad-output/implementation-artifacts/spec-gh-4-fix-sensevoice-accumulation.md`
  summary: stop() 先收尾后停音频，采集循环残余 acceptWaveform 可能在 finalize 后追加进累积缓冲
  evidence: stop() 等 loopCompleter 最多 300ms 后排空+收尾，循环线程 readAsync 阻塞超时场景下残余块晚于 finalize 到达；预先存在（38e9e9c 收尾时序设计），本次改动后残留量从全会话文本缩小为仅竞态残余段
- source_spec: `_bmad-output/implementation-artifacts/spec-gh-4-fix-sensevoice-accumulation.md`
  summary: autoStopOnEndpoint: true 模式下最终文本不进入提交流（387d6ba 移除自动提交的遗留）
  evidence: 采集循环清理清空 _lastEmittedText，_onEndpoint 对非设备丢失事件只打日志，_submitFromVad 已无调用方；VAD 自动停止模式的提交链路整体失效，与本 fix 相邻但非本 story 引入

- source_spec: `_bmad-output/implementation-artifacts/spec-fix-capsule-position-persistence.md`
  summary: 托盘退出路径的 `await` 无测试守卫——去掉 `tray_service.dart` 里 `await WindowService.instance.dispose()` 的 await，769 项测试仍全绿
  evidence: 已实测确认。新增的「退出链落盘 (WindowService 层)」测试自己写了 `await WindowService.instance.dispose()`，验证的是该方法本身能落盘，而非真实退出路径是否等它完成。`_exitApp()` 以 `exit(0)` 结尾，直接测会杀死测试进程，故需要别的守卫手段。已试 `unawaited_futures` lint：能正确报出该处缺失的 await，但全项目启用会新增 23 处既有告警（89→112），淹没信号；需先清理既有告警或只对该文件启用。后果是「拖动后立刻从托盘退出」的落盘保证可被一次清理式改动静默取消。

- source_spec: `_bmad-output/implementation-artifacts/spec-fix-capsule-position-persistence.md`
  summary: CI 不跑 flutter test，也不调用任何 scripts/verify-*.sh，本次新增的全部回归护栏在 CI 中不生效（既有问题）
  evidence: 已实测确认 `.github/workflows/release.yml` 中 `flutter test` 出现 0 次，只有 `flutter pub get` + `flutter build linux --release`；`docker.yml` 只构建镜像。本次三条破坏性判据（空 onWindowMove / 删 addListener / 退出 await）与 verify 脚本都只在有人本地手动运行时才起作用。
