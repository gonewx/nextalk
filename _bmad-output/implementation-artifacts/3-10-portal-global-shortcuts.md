# Story 3.10: Portal 全局快捷键（零配置注册）

Status: ready-for-dev

> Ultimate context engine analysis completed - comprehensive developer guide created（代码脉络审计 + Portal 生态 Web 核实双源合成，2026-07-09）

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

**As a** Nextalk 用户,
**I want** 安装后无需进入系统设置手动配置快捷键，应用首次启动时自动弹出系统授权对话框完成全局快捷键注册,
**so that** 获得"开箱即用"的语音输入体验，同时在不支持的桌面环境下仍能回退到现有的系统快捷键方案。

## Background（为什么有这个 Story）

快捷键方案演进史（**开发前必读，防止重蹈覆辙**）：

| 代际 | 方案 | 结局 | 教训 |
|------|------|------|------|
| 第一代 | Flutter `hotkey_manager` 插件（XGrabKey） | 废弃 | Wayland 架构禁止客户端全局抓键，仅 X11 可用 |
| 第二代 | Fcitx5 插件侧快捷键监听 + 命令 Socket + 焦点锁定 | SCP-002 废弃 | 复杂度失控（3 个 socket、焦点锁定 hack），且依赖 Fcitx5 常驻 |
| 第三代（现状） | 系统原生快捷键 + `nextalk --toggle` / `nextalk-toggle` 轻量触发器 | 保留为回退 | 可靠但需用户手动去系统设置配置，"开箱即用"打折 |
| **第四代（本 Story）** | XDG Desktop Portal `org.freedesktop.portal.GlobalShortcuts` | — | 应用内注册 + 系统授权对话框，Wayland 官方正道 |

关键约束：**第四代不能取代第三代，只能叠加**——Portal GlobalShortcuts 依赖桌面环境的 portal backend 支持（GNOME/KDE 较新版本），Ubuntu 22.04 (GNOME 42) 等旧环境不支持，必须保留系统快捷键 + `nextalk-toggle` 回退路径（Story 相关改动见 2026-07-09 延迟优化：`scripts/nextalk-toggle.sh` 已随包安装为 `/usr/bin/nextalk-toggle`）。

## Acceptance Criteria

1. **AC1 [注册]** Given 桌面环境的 portal backend 支持 GlobalShortcuts（接口可发现且版本满足要求），When 应用首次启动，Then 应用通过 Portal 注册 "toggle-voice-input" 全局快捷键（建议默认 Alt+Space），系统弹出一次授权/配置对话框；用户确认后快捷键立即生效。
2. **AC2 [触发]** Given Portal 快捷键已绑定，When 用户按下快捷键，Then 应用收到 `Activated` 信号并执行与 `nextalk --toggle` 完全相同的动作（`HotkeyController.instance.toggle()`），端到端行为与现有状态机一致（idle→recording→submitting）。
3. **AC3 [重启重绑]** Given 用户已授权过快捷键，When 应用重启，Then 应用以稳定的 shortcut id + app_id 重新 CreateSession + BindShortcuts，由 portal backend 匹配用户已保存的绑定（**规范无 restore token 机制**，持久化是 backend 按 app_id 的责任）；KDE 上不应重复弹对话框，GNOME 上允许 backend 决定是否再次确认，应用侧不得在一次运行中反复重绑（避免弹窗骚扰）。
4. **AC4 [回退检测]** Given portal backend 不支持 GlobalShortcuts（接口不存在、版本不足、CreateSession/BindShortcuts 失败或超时），When 应用启动，Then 静默降级到现状方案（不弹错误、不阻塞启动），并在诊断日志记录降级原因；托盘/设置界面显示当前快捷键模式（Portal / 系统快捷键）。
5. **AC5 [引导更新]** Given 应用处于回退模式，When 用户查看快捷键设置引导（init wizard / 托盘设置 / 安装完成提示），Then 引导文案指向 `nextalk-toggle` 命令（而非旧的 `nextalk --toggle`），与 deb/rpm postinst 提示一致。
6. **AC6 [冲突共存]** Given 用户同时配置了系统快捷键和 Portal 快捷键，When 两者都触发 toggle，Then 现有的 `_debounceMs`/`_isProcessing` 防抖与竞态防护保证不会产生双重触发的状态错乱（复用 `HotkeyController` 既有防护，需补测试）。
7. **AC7 [退出清理]** When 应用正常退出，Then Portal session 正确关闭（`Closed`），无泄漏的 D-Bus 连接；异常退出后重启不受残留 session 影响。
8. **AC8 [平台矩阵]** 在支持矩阵内实测通过：KDE Plasma（5.27+/6.x）与 GNOME 48+ 注册成功；**Ubuntu 22.04 (GNOME 42) 与 Ubuntu 24.04 (GNOME 46) 的默认 GNOME 会话均不支持该 portal**，必须验证两者正确静默降级到系统快捷键方案。

## Tasks / Subtasks

- [ ] Task 1: Portal 能力探测 (AC: 1, 4)
  - [ ] 1.1 【决策已锁定】`xdg_desktop_portal` 0.1.14 **不支持** GlobalShortcuts（源码 22 个 portal 无此实现）——用 `package:dbus` 直接调用；可参考该包 `XdgPortalSession`/`XdgPortalRequest` 的 Request/Response 处理模式
  - [ ] 1.2 实现探测：`org.freedesktop.DBus.Properties.Get("org.freedesktop.portal.GlobalShortcuts", "version")`，接口不存在时返回明确的 D-Bus 错误（不会挂起），仍加 2s 超时兜底
- [ ] Task 2: 实现 `PortalHotkeyService` (AC: 1, 2, 3, 7)
  - [ ] 2.1 CreateSession：注意返回值是 **Request 对象路径**，真正的 session_handle 必须订阅 `org.freedesktop.portal.Request::Response` 信号从 results 中提取（"Invalid session" 是此接口最常见新手坑）
  - [ ] 2.2 BindShortcuts 注册 "toggle-voice-input"（description 用 i18n 文案；preferred_trigger 默认 `"ALT+SPACE"`，**禁用 Meta/Super 键**——规范保留给桌面环境）；每个 session 只能 BindShortcuts 一次
  - [ ] 2.3 监听 `Activated(session_handle, shortcut_id, timestamp, options)` 信号 → 调用 `HotkeyController.instance.toggle()`
  - [ ] 2.4 持久化策略：**规范无 restore token**——每次启动用稳定 shortcut id + app_id 重新 CreateSession+BindShortcuts，backend 负责记忆用户绑定；D-Bus 连接必须全程保活（连接断开 = session 销毁 = 快捷键失效），单次运行内禁止重复重绑（GNOME 会反复弹窗）
  - [ ] 2.5 dispose 链接入 `main.dart` 的 `TrayService.onBeforeExit`（关闭 session 与 DBusClient）
- [ ] Task 3: 集成与降级路由 (AC: 4)
  - [ ] 3.1 `main.dart` 初始化序列中加入 Portal 探测（在 HotkeyController.initialize 之后，不阻塞启动主路径——用后台 Future，探测失败静默）
  - [ ] 3.2 `HotkeyService` 增加 `hotkeyMode` 状态（portal / system），供托盘与 UI 展示
  - [ ] 3.3 降级原因写入 `DiagnosticLogger`
- [ ] Task 4: 引导文案与设置界面更新 (AC: 5)
  - [ ] 4.1 更新 init wizard / manual_install_guide 中的快捷键引导：优先说明 Portal 自动注册；回退模式下指引 `nextalk-toggle`
  - [ ] 4.2 l10n 中英文案（`app_localizations_zh/en.dart` 经 arb 流程）
- [ ] Task 5: 测试 (AC: 2, 6, 7)
  - [ ] 5.1 `PortalHotkeyService` 单元测试（mock DBusClient：session 创建/信号分发/token 恢复/超时降级）
  - [ ] 5.2 双触发路径防抖回归测试（single_instance 命令 + portal Activated 并发）
  - [ ] 5.3 真机验证矩阵记录到 story 完成笔记（KDE / GNOME 新版 / Ubuntu 22.04 降级）

## Dev Notes

### 必须复用的现有组件（禁止重复造轮子）

| 组件 | 位置 | 用途 |
|------|------|------|
| `HotkeyController.instance.toggle()/show()/hide()` | `voice_capsule/lib/services/hotkey_controller.dart` | **唯一**业务入口，Portal Activated 只是新的触发源；内置 `_isProcessing` 竞态防护与 300ms 防抖 |
| `SingleInstance.onCommand` | `voice_capsule/lib/services/single_instance.dart` | 现有 `--toggle` 路径，保持不动 |
| `HotkeyService` | `voice_capsule/lib/services/hotkey_service.dart` | 现为纯配置读取（SCP-002 后不做监听）；本 story 为其增加 mode 状态，不改回监听器 |
| `SettingsService` | `voice_capsule/lib/services/settings_service.dart` | restore token 持久化 |
| `DiagnosticLogger` | `voice_capsule/lib/utils/diagnostic_logger.dart` | 降级原因记录 |
| `TrayService.onBeforeExit` | `voice_capsule/lib/main.dart` | dispose 挂载点 |

### 架构约束

- **初始化顺序**（`main.dart` 现有序列）：WindowService → SettingsService → LanguageService → TrayService → HotkeyService → ModelManager/引擎 → HotkeyController → SingleInstance.onCommand。Portal 初始化放在 HotkeyController.initialize 之后、runApp 之前发起，但**必须是非阻塞的后台 Future**——portal backend 挂起不能拖慢启动（先前延迟优化刚消灭了启动等待感，不能倒退）。
- **pubspec 依赖**：`xdg_desktop_portal: ^0.1.13` 已存在；若需直接 D-Bus，`package:dbus` 是其传递依赖（Canonical 同源），显式声明版本。
- **禁止**改动 Fcitx5 插件（`addons/fcitx5/`）——快捷键与插件已在 SCP-002 完全解耦。
- **窗口显隐语义**：toggle 的窗口行为已由 `HotkeyController` 状态机管理（含 Wayland 焦点补偿 100ms），Portal 路径不得绕过状态机直接操作 WindowService。

### 现有文件将被修改（开发前必须完整读一遍）

- `voice_capsule/lib/main.dart`（UPDATE）：初始化序列插入 Portal 探测与服务装配；保持 runZonedGuarded 结构与既有资源清理链
- `voice_capsule/lib/services/hotkey_service.dart`（UPDATE）：增加 mode 状态；保留配置文件读取逻辑（Alt+Space 默认值来自 `HotkeyConfig.defaultConfig`）
- `voice_capsule/lib/services/portal_hotkey_service.dart`（NEW）
- `voice_capsule/lib/ui/init_wizard/manual_install_guide.dart`（UPDATE）：快捷键引导文案
- `voice_capsule/test/services/portal_hotkey_service_test.dart`（NEW）

### 平台支持矩阵与技术规范（2026-07-09 Web 核实）

**D-Bus 接口**：`org.freedesktop.portal.GlobalShortcuts`，当前 version 2
（规范：https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html）

- `CreateSession(options a{sv}) → handle o`（options: `handle_token`、`session_handle_token`；返回 Request 路径，session_handle 从 Response 信号 results 取）
- `BindShortcuts(session_handle o, shortcuts a(sa{sv}), parent_window s, options a{sv})`（shortcut vardict: `description s` 必填、`preferred_trigger s` 可选，格式遵循 freedesktop Shortcuts 规范如 `"CTRL+SHIFT+A"`）
- `ListShortcuts(session_handle o, options a{sv})`
- 信号：`Activated` / `Deactivated` / `ShortcutsChanged`；property：`version u`

**桌面环境支持矩阵**：

| 后端 | 支持 | 说明 |
|------|------|------|
| KDE Plasma (xdg-desktop-portal-kde) | ✅ | Plasma 5.27 起，参考实现基准，系统快捷键设置中可见并记忆 |
| GNOME (xdg-desktop-portal-gnome) | ✅ GNOME 48 起 | 首次绑定弹系统确认对话框（MR gnome/xdg-desktop-portal-gnome!208） |
| Hyprland | ✅ | 已实现 |
| wlroots/Sway (xdg-desktop-portal-wlr) | ❌ | 长期未实现（issue #240） |
| **Ubuntu 22.04 (GNOME 42) / 24.04 (GNOME 46)** | ❌ | **两个 LTS 默认会话均不支持**——本项目 NFR3 基线是 Ubuntu 22.04+，故 Portal 只能作为渐进增强，回退路径是硬需求 |

**已知坑（实现时逐条对照）**：
1. "Invalid session"：CreateSession 返回 Request handle ≠ session_handle（KDE Discuss #12370）
2. 探测用 version property，接口缺失返回明确 D-Bus 错误，不挂起
3. session 生命周期 = D-Bus 连接生命周期，连接必须保活
4. 每 session 仅一次 BindShortcuts；改绑定需重开 session（本应用固定 1 个快捷键，无影响）
5. 无 restore token；KDE 按 app_id 记忆（KDE 6.0.3 曾有跨会话不持久 bug #484682）；GNOME 可能每次启动再确认——不算缺陷，属 backend 行为
6. 避免频繁重绑（Chrome 134 接入初期因弹窗骚扰被投诉，chromium #404298968）

**参考实现**：KDE `xdg-portal-test-kde`（最权威用法参考）、Chromium 134+ 的 portal 集成、obs-wayland-hotkeys 插件源码、规范原始 PR flatpak/xdg-desktop-portal#711。

**Dart 生态结论**：`xdg_desktop_portal` 0.1.14（canonical）未实现 GlobalShortcuts（已核对源码 portal 清单），用其底层依赖 `package:dbus` 直接调用；该包的 Session/Request 封装模式可作代码参考。

### 测试标准

- 单测框架：`flutter_test`，现有 40+ 测试文件分层（unit/integration/e2e），Portal 服务测试放 `test/services/`
- Mock 模式参考：`test/` 下现有 service 测试用构造注入 + fake 依赖（如 `audio_inference_pipeline_test.dart` 的 FakeASREngine 模式）
- D-Bus 层 mock：注入 `DBusClient` 接口，不依赖真实 session bus

### Project Structure Notes

- 新服务遵循 `lib/services/` 平铺结构与 `xxx_service.dart` 命名惯例
- 常量放 `lib/constants/hotkey_constants.dart`（已存在，含 keyToFcitx5 映射表——注意该表是 SCP-002 遗留，本 story 需要的是 Portal trigger 格式映射，新增不覆盖）
- i18n 走 `lib/l10n/` 现有 arb 生成流程（Story 3-8 建立）

### References

- [Source: docs/prd_zh.md#FR6] 全局快捷键需求（SCP-002 版）
- [Source: _bmad-output/epics.md#Story-3.5] 第二代方案及其废弃记录
- [Source: _bmad-output/sprint-change-proposals/scp-002-simplified-architecture.md] SCP-002 决策全文
- [Source: _bmad-output/implementation-artifacts/3-5-global-hotkey-listener.md] 前身 story（superseded，含 Wayland 教训）
- [Source: _bmad-output/planning-artifacts/research/technical-nextalk-advanced-features-implementation-audit-research-2026-07-09.md] 2026-07-09 特性审计：系统快捷键方案被外部验证为"Wayland 唯一可行"，Portal 是其官方演进方向
- [Source: voice_capsule/lib/services/hotkey_controller.dart] 触发入口与状态机
- 2026-07-09 延迟优化：`nextalk-toggle` 轻量触发器已随包安装（`packaging/deb/postinst` 等），回退路径引导文案以此为准

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
