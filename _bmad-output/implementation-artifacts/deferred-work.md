# Deferred Work

## Deferred from: code review of 3-10-portal-global-shortcuts (2026-07-09)

- **app_id 持久化未验证（AC3）**：CreateSession 未设 .desktop app_id，非 Flatpak 裸二进制上 KDE 能否按 app_id 跨重启记忆用户绑定未经真机验证。与 AC8 注册成功分支一并待验。
- **D-Bus 连接断开无检测/重连**：连接断开=session 销毁=快捷键静默失效，但 hotkeyMode 仍显示 portal，UI 与实际状态可能永久不一致。属增强，超本 story 范围。
- **register/dispose 并发守卫**：`_registerAttempted` 守卫位于首个 await 前，dispose 与后台 register 理论可并发导致 use-after-dispose 或误返回 failed。当前仅 `_setupPortalHotkey` 单一调用点，无实际并发 reachability。
- **AC6 回归测试保真度**：双触发测试在测试内本地重建 `guardedToggle` 闭包，未驱动真实 `HotkeyController.toggle()`。两路径确收敛同一入口，风险低，但可补真实集成测试。
- **AC8 注册成功分支真机验证**：KDE 5.27+/6.x、GNOME 48+ 的注册成功路径未在真机验证（无支持环境）；仅降级分支在本机 Ubuntu 24.04+GNOME 46 验证通过。
