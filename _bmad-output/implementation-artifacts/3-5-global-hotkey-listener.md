# Story 3.5: 全局快捷键监听 (Global Hotkey Listener)

> **⚠️ SUPERSEDED by SCP-002 (2025-12-28)**
>
> 本文档描述的实现方案已被废弃。快捷键监听已从 Fcitx5 插件移除，改为使用系统原生快捷键方案：
> - **新方案**: 系统原生快捷键 (GNOME Settings → Keyboard → Custom Shortcuts) + `nextalk --toggle` 命令行参数
> - **移除内容**: Fcitx5 插件侧快捷键监听、焦点锁定机制、命令 Socket (`nextalk-cmd.sock`)、配置 Socket (`nextalk-fcitx5-cfg.sock`)
> - **详情**: 参见 `_bmad-output/sprint-change-proposals/scp-002-simplified-architecture.md`
>
> 以下内容仅作为历史记录保留。

Status: ~~done~~ **superseded**

## Prerequisites

> **前置条件**: Story 3-1, 3-2, 3-3, 3-4 必须完成
> - ✅ 透明胶囊窗口基础已实现 (Story 3-1)
> - ✅ 胶囊 UI 组件已实现 (Story 3-2)
> - ✅ 状态机与动画系统已实现 (Story 3-3)
> - ✅ 系统托盘集成已实现 (Story 3-4)
> - ✅ WindowService 已实现 show()/hide() 功能
> - ✅ AudioInferencePipeline 已实现 start()/stop() 功能 (Epic 2)
> - ⚠️ 本 Story 将实现全局快捷键监听，连接窗口显隐和录音控制

## Story

As a **用户**,
I want **通过快捷键快速唤醒语音输入**,
So that **无需鼠标操作，实现高效输入**。

## Acceptance Criteria

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC1 | 按下 Right Alt 键时主窗口瞬间出现 | 按键后窗口立即可见 |
| AC2 | 按下 Right Alt 键时自动开始录音 | 状态切换为"聆听中"，Pipeline 启动 |
| AC3 | 正在录音时再次按下 Right Alt 立即停止录音 | Pipeline 停止，获取最终文本 |
| AC4 | 停止录音后提交文本到活动窗口 | 通过 FcitxClient 发送文本 |
| AC5 | 提交后主窗口瞬间隐藏 | 窗口消失，无渐变动画 |
| AC6 | 支持配置文件自定义快捷键 | 读取配置文件，使用用户指定键位 |
| AC7 | 快捷键被其他应用占用时输出警告日志 | 注册失败时 log 警告，不崩溃 |
| AC8 | 应用启动时自动注册全局快捷键 | main.dart 初始化时注册 |
| AC9 | 应用退出时正确注销快捷键 | TrayService.exit 时注销 |
| AC10 | 快捷键在后台运行时也能响应 | 窗口隐藏时按键仍能触发 |
| AC11 | **Wayland 环境下焦点锁定正常工作** | 录音时切换窗口，文本仍提交到原窗口 |

## 技术规格

### 全局快捷键方案分析 [Source: 技术调研]

**方案对比:**

| 方案 | 优点 | 缺点 | 最终选择 |
|------|------|------|----------|
| **hotkey_manager (Flutter)** | Flutter 原生，API 简洁 | 仅支持 X11，Wayland 不工作 | ❌ 弃用 |
| **Fcitx5 插件侧监听** | 原生 Wayland 支持，焦点锁定 | 需要 C++ 实现 | ✅ **采用** |

**选型决策: Fcitx5 插件侧监听**
- 原因: 原生 Wayland 支持，可实现焦点锁定，解决录音时切换窗口的问题
- 实现: 通过 Fcitx5 的 `InputContextKeyEvent` 事件监听
- 通信: 插件通过 Unix Socket 向 Flutter 发送 `toggle` 命令

### 架构设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Fcitx5 守护进程                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     NextalkAddon (C++)                           │    │
│  │  ┌─────────────────┐       ┌─────────────────────────────────┐  │    │
│  │  │  KeyEvent 监听   │──────▶│   handleKeyEvent()              │  │    │
│  │  │  (PreInputMethod)│       │  - 检测 configuredKey_          │  │    │
│  │  └─────────────────┘       │  - 锁定 InputContext UUID       │  │    │
│  │                             │  - sendCommandToFlutter("toggle")│  │    │
│  │                             └───────────────┬─────────────────┘  │    │
│  └─────────────────────────────────────────────┼────────────────────┘    │
│                                                │                          │
│                        nextalk-cmd.sock        │                          │
└────────────────────────────────────────────────┼──────────────────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Voice Capsule (Flutter)                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     CommandServer (Dart)                         │    │
│  │  ┌─────────────────┐       ┌─────────────────────────────────┐  │    │
│  │  │  Socket 监听     │──────▶│   HotkeyController              │  │    │
│  │  │  (toggle 命令)   │       │  (业务逻辑控制器)                │  │    │
│  │  └─────────────────┘       └───────────┬─────────────────────┘  │    │
│  │                                        │                         │    │
│  │                          ┌─────────────┼─────────────┐           │    │
│  │                          │             │             │           │    │
│  │                          ▼             ▼             ▼           │    │
│  │                ┌─────────────┐ ┌─────────────┐ ┌───────────┐    │    │
│  │                │WindowService│ │  Pipeline   │ │FcitxClient│    │    │
│  │                │(窗口显隐)   │ │(录音控制)   │ │(文本提交) │    │    │
│  │                └─────────────┘ └─────────────┘ └───────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  状态机流转:                                                             │
│  [Idle] ──(toggle)──▶ [Recording] ──(toggle/VAD)──▶ [Submitting]        │
│    ▲                                                      │              │
│    └──────────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Socket 通信协议

**三个 Socket 的职责:**

| Socket | 路径 | 方向 | 用途 |
|--------|------|------|------|
| 文本 Socket | `nextalk-fcitx5.sock` | Flutter → Fcitx5 | 提交识别文本 |
| 配置 Socket | `nextalk-fcitx5-cfg.sock` | Flutter → Fcitx5 | 发送配置命令 |
| 命令 Socket | `nextalk-cmd.sock` | Fcitx5 → Flutter | 发送控制命令 |

**协议格式 (通用):**
```
[4字节长度 LE] + [UTF-8 字符串]
```

**配置命令格式:**
```
config:hotkey:<key_spec>
```
示例: `config:hotkey:Alt_R`, `config:hotkey:Control+Shift+Space`

### 目标文件结构

```text
voice_capsule/
├── lib/
│   ├── main.dart                        # 🔄 修改 (集成 CommandServer)
│   ├── services/
│   │   ├── command_server.dart          # 🆕 新增 (接收 Fcitx5 命令)
│   │   ├── hotkey_service.dart          # 🔄 修改 (发送配置到 Fcitx5)
│   │   ├── hotkey_controller.dart       # ✅ 已有 (业务控制器)
│   │   ├── window_service.dart          # ✅ 已有 (无需修改)
│   │   ├── tray_service.dart            # ✅ 已有 (无需修改)
│   │   └── audio_inference_pipeline.dart # ✅ 已有 (无需修改)
│   └── constants/
│       ├── hotkey_constants.dart        # ✅ 已有 (快捷键常量)
│       └── settings_constants.dart      # 🔄 修改 (Socket 路径常量)
├── pubspec.yaml                         # ✅ 已有 (无需 hotkey_manager)
└── test/
    └── services/
        ├── hotkey_service_test.dart     # ✅ 已有
        └── hotkey_controller_test.dart  # ✅ 已有

addons/fcitx5/
├── src/
│   ├── nextalk.cpp                      # 🔄 修改 (快捷键监听实现)
│   └── nextalk.h                        # 🔄 修改 (新增成员变量)
└── CMakeLists.txt                       # ✅ 已有 (无需修改)
```

## Tasks / Subtasks

> **执行顺序**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6

- [x] **Task 1: Fcitx5 插件侧快捷键监听** (AC: #1, #7, #8, #10)
  - [x] 1.1 在 `nextalk.h` 中添加快捷键相关成员变量:
    - `keyNameMap_`: 按键名称到 KeySym 的映射
    - `configuredKey_`: 当前配置的主键 (默认 Alt_R)
    - `configuredModifiers_`: 配置的修饰键集合
    - `hotkeyPressed_`: 快捷键状态跟踪
  - [x] 1.2 在 `nextalk.cpp` 中实现:
    - `initKeyMap()`: 初始化按键映射表
    - `setupKeyEventHandler()`: 注册 KeyEvent 监听器
    - `handleKeyEvent()`: 处理按键事件
    - `isConfiguredHotkey()`: 检查是否匹配配置的快捷键

- [x] **Task 2: 焦点锁定机制** (AC: #4, #11)
  - [x] 2.1 在 `nextalk.h` 中添加:
    - `lockedInputContextUUID_`: 锁定的 InputContext UUID
    - `hasLockedContext_`: 是否有锁定的上下文
  - [x] 2.2 在 `handleKeyEvent()` 中锁定当前 InputContext
  - [x] 2.3 在 `commitText()` 中优先使用锁定的 InputContext
  - [x] 2.4 提交后清除锁定状态

- [x] **Task 3: 命令 Socket (Fcitx5 → Flutter)** (AC: #1, #2, #3)
  - [x] 3.1 在 `nextalk.cpp` 中实现 `sendCommandToFlutter()`:
    - 连接到 `nextalk-cmd.sock`
    - 发送 `toggle` 命令
  - [x] 3.2 在 `handleKeyEvent()` 中调用发送命令

- [x] **Task 4: 配置 Socket (Flutter → Fcitx5)** (AC: #6)
  - [x] 4.1 在 `nextalk.cpp` 中实现配置监听:
    - `startConfigListener()`: 启动配置 Socket 服务器
    - `configListenerLoop()`: 监听循环
    - `handleConfigClient()`: 处理配置命令
    - `processCommand()`: 解析并应用配置
  - [x] 4.2 实现 `parseHotkeyConfig()` 解析快捷键配置

- [x] **Task 5: Flutter CommandServer 实现** (AC: #1, #2, #3, #5)
  - [x] 5.1 创建 `lib/services/command_server.dart`:
    - 监听 `nextalk-cmd.sock`
    - 接收 `toggle` 命令
    - 调用 HotkeyController
  - [x] 5.2 在 `main.dart` 中集成 CommandServer

- [x] **Task 6: 文本提交 IME 周期模拟** (AC: #4)
  - [x] 6.1 在 `commitText()` 中实现完整 IME 周期:
    - 设置 preedit
    - 提交文本
    - 清空 preedit
  - [x] 6.2 添加调试日志

## Dev Notes

### 架构约束与禁止事项

| 类别 | 约束 | 原因 |
|------|------|------|
| **平台支持** | 同时支持 X11 和 Wayland | Fcitx5 原生支持两者 |
| **初始化顺序** | WindowService → TrayService → CommandServer | 确保窗口就绪后再监听命令 |
| **焦点锁定** | 必须在快捷键按下时锁定 | 解决 Wayland 焦点切换问题 |
| **IME 周期** | 必须模拟完整 preedit 周期 | 确保终端等应用正确处理 |

### 与 hotkey_manager 方案的对比

| 特性 | hotkey_manager (旧方案) | Fcitx5 插件 (新方案) |
|------|-------------------------|---------------------|
| Wayland 支持 | ❌ 仅 X11 | ✅ 原生支持 |
| 焦点锁定 | ❌ 不支持 | ✅ 支持 |
| 系统依赖 | libkeybinder-3.0-dev | 无额外依赖 |
| 实现位置 | Flutter 侧 | Fcitx5 插件侧 |
| 配置热更新 | 需重启应用 | ✅ 运行时更新 |

### 配置文件示例

**创建配置目录和文件:**
```bash
mkdir -p ~/.config/nextalk
cat > ~/.config/nextalk/config.yaml << 'EOF'
# Nextalk 配置文件
# 快捷键配置 (支持运行时更新)
hotkey:
  # 主键 (可选值: Alt_R, Alt_L, Control_L, Control_R, F1-F12, Space 等)
  key: Alt_R
  # 修饰键 (可选，多个用列表形式)
  # 示例: [Control, Shift]
  modifiers: []

# 备选配置示例 (Ctrl+Shift+Space):
# hotkey:
#   key: Space
#   modifiers: [Control, Shift]
EOF
```

### 快速验证命令

```bash
cd /mnt/disk0/project/newx/nextalk/nextalk_fcitx5_v2/voice_capsule

# 1. 构建 Flutter 应用
flutter build linux --release

# 2. 编译 Fcitx5 插件
cd ../addons/fcitx5 && mkdir -p build && cd build && cmake .. && make

# 3. 安装插件
../../../scripts/install_addon.sh

# 4. 重启 Fcitx5
fcitx5 -r

# 5. 运行应用
cd ../../../voice_capsule && flutter run -d linux
```

**手动验证清单 (全部通过 = AC 通过):**
| # | 检查项 | 对应 AC |
|---|--------|---------|
| [x] | 按 Right Alt 窗口瞬间出现 | AC1 |
| [x] | 窗口出现时红灯呼吸动画 | AC2 |
| [x] | 录音中再次按 Right Alt 窗口隐藏 | AC3, AC5 |
| [x] | 说话后文字实时显示 | AC2 |
| [x] | 静音后自动提交并隐藏 | AC4 (VAD) |
| [x] | 配置文件自定义快捷键生效 | AC6 |
| [x] | 应用启动时快捷键自动响应 | AC8 |
| [x] | 窗口隐藏时按快捷键仍能响应 | AC10 |
| [x] | Wayland 下切换窗口后文本仍提交到原窗口 | AC11 |

### 潜在问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| Fcitx5 未运行 | Flutter 应用检测 Socket 不存在时提示用户 |
| 快捷键与系统冲突 | 用户可通过配置文件自定义其他键位 |
| 焦点锁定的 InputContext 已销毁 | 回退到 mostRecentInputContext |
| 终端不响应 commitString | 使用完整 IME 周期 (preedit) |

### 外部资源

- [Fcitx5 开发文档](https://fcitx-im.org/wiki/Develop)
- [docs/architecture.md#4.1](docs/architecture.md) - Socket 架构设计
- [docs/prd.md#FR6](docs/prd.md) - 全局快捷键功能需求

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (via Claude Code)

### Debug Log References

- 测试运行: 通过
- 静态分析: 无新增 warning

### Completion Notes List

- Task 1-6 全部完成
- AC1-AC11 已验证通过
- 方案从 hotkey_manager 切换为 Fcitx5 插件侧监听
- 新增焦点锁定机制解决 Wayland 焦点切换问题
- 新增 IME 周期模拟解决终端输入问题

### File List

| 文件 | 操作 | 说明 |
|------|------|------|
| `addons/fcitx5/src/nextalk.cpp` | 🔄 修改 | 快捷键监听、焦点锁定、命令 Socket、配置 Socket |
| `addons/fcitx5/src/nextalk.h` | 🔄 修改 | 新增快捷键、焦点锁定相关成员变量 |
| `voice_capsule/lib/services/command_server.dart` | 🆕 新增 | 接收 Fcitx5 命令的服务 |
| `voice_capsule/lib/services/hotkey_controller.dart` | 🔄 修改 | 业务逻辑控制器 |
| `voice_capsule/lib/main.dart` | 🔄 修改 | 集成 CommandServer |
| `voice_capsule/lib/constants/hotkey_constants.dart` | ✅ 保留 | 快捷键常量定义 |

---

### SM Validation Record

| Date | Validator | Result | Notes |
|------|-----------|--------|-------|
| 2025-12-22 | SM Agent (Bob) | ✅ PASS | 基于 hotkey_manager 方案 |
| 2025-12-25 | SM Agent (Bob) | ✅ PASS | 更新为 Fcitx5 插件侧监听方案 |

**架构变更说明:**

原方案使用 Flutter 侧的 `hotkey_manager` 库监听全局快捷键，仅支持 X11。
新方案改为 Fcitx5 插件侧监听，具有以下优势:
1. 原生 Wayland 支持
2. 焦点锁定机制
3. 无额外系统依赖
4. 运行时配置更新

---
*References: docs/architecture.md#4.1, docs/prd.md#FR6, _bmad-output/epics.md#Story-3.5*
