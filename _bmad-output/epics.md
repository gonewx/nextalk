---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments:
  - docs/prd.md
  - docs/architecture.md
  - docs/front-end-spec.md
lastUpdated: 2025-12-28
scp002Applied: true
---

# Nextalk - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Nextalk, decomposing the requirements from the PRD, UX Design, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1 [UI/交互]: 悬浮胶囊窗口
- 应用启动后默认隐藏，托盘显示图标
- 激活时显示无边框、真透明胶囊窗口
- 实时反馈：用户说话时，文字逐字显示在预览区

FR2 [核心]: 实时语音识别 (ASR)
- 模型：sherpa-onnx-streaming-zipformer-bilingual-zh-en (流式双语)
- 采集：通过 Dart FFI + PortAudio 采集 16k 单声道音频

FR3 [核心]: 智能端点检测 (VAD)
- 使用 Sherpa 内置 VAD (默认停顿 ~1.5s 触发)
- 检测到静音后，自动提交预览区文本

FR4 [集成]: 文本上屏
- 客户端通过 Unix Domain Socket 连接 $XDG_RUNTIME_DIR/nextalk-fcitx5.sock
- 协议：[4字节长度 (LE)] + [UTF-8 文本]

FR5 [系统]: 托盘管理
- 支持显示/隐藏/退出

FR6 [系统]: 全局快捷键
- 默认键位：Right Alt
- 逻辑：按下唤醒/开始录音；再次按下停止/上屏/隐藏
- 支持配置文件自定义

### NonFunctional Requirements

NFR1: 端到端延迟 < 20ms
NFR2: 纯离线推理，无网络请求（运行时）
NFR3: 兼容 Ubuntu 22.04+ (X11/Wayland 原生支持，快捷键和文本提交均支持 Wayland)
NFR4: 窗口启动无黑框闪烁 (基于 C++ Runner 改造)

### Additional Requirements

**架构需求:**
- [结构] Monorepo 结构：/addons (C++ 插件) + /voice_capsule (Flutter 客户端)
- [模型] 首次运行下载策略 (Download-on-Demand)，存储在 ~/.local/share/nextalk/models
- [模型] 下载后必须校验 SHA256，防止文件损坏
- [性能] 零拷贝 FFI 音频流水线设计
- [安全] Socket 文件权限必须设为 0600
- [构建] RPATH 配置确保运行时库查找 ($ORIGIN/lib)
- [构建] libportaudio.so 系统动态链接，libsherpa-onnx-c-api.so 打包

**UX 需求:**
- [视觉] Dark Mode Only 策略
- [尺寸] 胶囊尺寸：400x120 逻辑像素，高度 60px，圆角 40px
- [动画] 波纹 1500ms EaseOutQuad，光标 800ms，红点呼吸 sin(t)
- [状态] 三种状态指示：聆听中(红)、处理中(脉冲)、错误(黄/灰)
- [托盘] 菜单项：显示/隐藏、设置(Post MVP)、退出
- [交互] 瞬间出现/消失，无渐变动画
- [交互] 支持拖拽移动并记忆位置
- [错误] 异常处理 UX：音频设备异常、模型损坏、Socket 断开均有视觉反馈

### FR Coverage Map

| FR | 史诗 | 描述 |
|----|------|------|
| FR1 | Epic 3 | 悬浮胶囊窗口 - UI/交互 |
| FR2 | Epic 2 | 实时语音识别 (ASR) |
| FR3 | Epic 2 | 智能端点检测 (VAD) |
| FR4 | Epic 1 | 文本上屏 - IPC 集成 |
| FR5 | Epic 3 | 托盘管理 |
| FR6 | Epic 3 | 全局快捷键 |

## Epic List

### Epic 1: IPC 桥梁 (The Bridge)

**用户成果**：建立核心通信通道，使文本能够被注入到任何应用程序中。

**FRs 覆盖**：FR4

**范围说明**：
- 集成现有的 C++ Fcitx5 插件到项目结构
- 实现 Dart 端 Socket Client
- 验证端到端文本注入能力
- 编写插件安装脚本

**完成标志**：可以通过代码发送文本到任何输入框

---

### Epic 2: 语音识别引擎 (The Brain)

**用户成果**：用户可以说话，系统实时将语音转换为文本。

**FRs 覆盖**：FR2, FR3

**范围说明**：
- 配置 Flutter Linux 构建环境，链接原生库
- 实现 Dart FFI 绑定 (Sherpa + PortAudio)
- 实现音频采集 → AI 推理的数据流水线
- 实现 VAD 端点检测与自动提交
- 模型管理：首次运行下载策略

**完成标志**：可以识别语音并获得文本结果

---

### Epic 3: 完整产品体验 (The Product)

**用户成果**：用户获得无缝、美观的语音输入体验，支持快捷键唤醒、视觉反馈和系统集成。

**FRs 覆盖**：FR1, FR5, FR6

**范围说明**：
- 实现真透明无边框胶囊窗口 UI
- 串联完整业务流：Right Alt → 录音 → 识别 → 上屏
- 实现全局快捷键监听
- 完善托盘与窗口显隐逻辑
- 实现所有 UX 规范中的动画效果

**完成标志**：完整的生产级语音输入工具

---

## Epic 1: IPC 桥梁 (The Bridge)

建立核心通信通道，使文本能够被注入到任何应用程序中。

### Story 1.1: Fcitx5 插件集成

**As a** 开发者,
**I want** 将现有的 Fcitx5 C++ 插件代码正确集成到 Monorepo 结构中,
**So that** 项目有一个统一的代码库结构，便于后续开发和维护。

**Acceptance Criteria:**

**Given** 现有的 Fcitx5 插件源码位于 `/mnt/disk0/project/newx/nextalk/nextalk_fcitx5/addons`
**When** 执行代码迁移
**Then** 插件源码复制/链接到当前项目的 `/addons/fcitx5/` 目录下
**And** CMakeLists.txt 正确配置，可独立编译插件
**And** 移除 ydotool 回退逻辑（如存在）
**And** 插件能成功编译生成 `.so` 文件

---

### Story 1.2: 插件安装脚本

**As a** 开发者/用户,
**I want** 通过一键脚本编译和安装 Fcitx5 插件,
**So that** 可以快速部署插件而无需手动操作。

**Acceptance Criteria:**

**Given** 插件源码已在 `/addons/fcitx5/` 目录
**When** 执行 `scripts/install_addon.sh`
**Then** 脚本自动执行 cmake 配置和编译
**And** 编译产物自动复制到 Fcitx5 插件目录 (`~/.local/lib/fcitx5/` 或系统目录)
**And** 脚本输出清晰的成功/失败信息
**And** 重启 Fcitx5 后插件正确加载

---

### Story 1.3: Dart Socket Client 实现

**As a** Flutter 客户端,
**I want** 能够通过 Unix Domain Socket 与 Fcitx5 插件通信,
**So that** 可以将识别出的文本注入到任何应用程序的输入框中。

**Acceptance Criteria:**

**Given** Fcitx5 插件已安装并运行，Socket 文件存在于 `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock`
**When** Dart 客户端调用 `sendText("Hello World")`
**Then** 客户端按协议格式发送数据：[4字节长度 LE] + [UTF-8 文本]
**And** 文本成功出现在当前活动窗口的输入框中
**And** 连接异常时返回明确的错误信息

**Given** Socket 文件不存在或连接失败
**When** 尝试发送文本
**Then** 返回连接错误，不崩溃
**And** 提供可用于 UI 显示的错误状态

---

### Story 1.4: Flutter 项目初始化

**As a** 开发者,
**I want** 创建 Flutter Linux 项目的基础结构,
**So that** 有一个可扩展的代码基础用于后续功能开发。

**Acceptance Criteria:**

**Given** Monorepo 根目录
**When** 初始化 Flutter 项目
**Then** `/voice_capsule/` 目录包含完整的 Flutter Linux 项目
**And** `pubspec.yaml` 配置正确的项目名称和依赖
**And** `linux/CMakeLists.txt` 预配置 RPATH 设置 (`$ORIGIN/lib`)
**And** 目录结构符合架构文档：`lib/ffi/`, `lib/services/`, `lib/ui/`
**And** 项目可成功执行 `flutter build linux`

---

## Epic 2: 语音识别引擎 (The Brain)

用户可以说话，系统实时将语音转换为文本。

### Story 2.1: 原生库链接配置

**As a** 开发者,
**I want** 正确配置 Flutter Linux 构建系统以链接 Sherpa 和 PortAudio 原生库,
**So that** Dart 代码可以通过 FFI 调用这些库的功能。

**Acceptance Criteria:**

**Given** Flutter 项目已初始化，原生库文件位于 `/libs/` 目录
**When** 执行 `flutter build linux`
**Then** `libsherpa-onnx-c-api.so` 被复制到构建产物的 `lib/` 目录
**And** `libportaudio.so` 从系统动态链接
**And** RPATH 设置为 `$ORIGIN/lib`，确保运行时能找到私有库
**And** 构建成功无链接错误

---

### Story 2.2: PortAudio FFI 绑定

**As a** Flutter 客户端,
**I want** 通过 Dart FFI 调用 PortAudio 进行音频采集,
**So that** 可以获取麦克风输入用于语音识别。

**Acceptance Criteria:**

**Given** PortAudio 库已正确链接
**When** 调用 `AudioCapture.start()`
**Then** 成功打开默认麦克风设备
**And** 以 16kHz 采样率、单声道、Float32 格式采集音频
**And** 音频数据写入预分配的堆外内存缓冲区 (`Pointer<Float>`)

**Given** 音频采集正在进行
**When** 调用 `AudioCapture.read(buffer, samples)`
**Then** 返回指定数量的音频样本
**And** 延迟 < 50ms

**Given** 麦克风设备不可用或被占用
**When** 尝试初始化音频采集
**Then** 返回明确的错误状态（设备异常）
**And** 不崩溃

---

### Story 2.3: Sherpa-onnx FFI 绑定

**As a** Flutter 客户端,
**I want** 通过 Dart FFI 调用 Sherpa-onnx 进行语音识别,
**So that** 可以将音频数据转换为文本。

**Acceptance Criteria:**

**Given** Sherpa 库已正确链接，模型文件已就绪
**When** 调用 `SherpaService.initialize(modelPath)`
**Then** 成功创建流式识别器实例
**And** 配置为双语模式 (zh-en)

**Given** 识别器已初始化
**When** 调用 `acceptWaveform(sampleRate, buffer, samples)`
**Then** 音频数据被送入识别引擎
**And** 使用与 PortAudio 相同的内存指针（零拷贝）

**Given** 音频数据已送入
**When** 调用 `getResult()`
**Then** 返回当前识别出的文本（部分结果或最终结果）
**And** 处理 100ms 音频块耗时 < 10ms

---

### Story 2.4: 模型管理器

**As a** 用户,
**I want** 应用首次运行时自动下载所需的 AI 模型,
**So that** 无需手动配置即可使用语音识别功能。

**Acceptance Criteria:**

**Given** 应用首次启动，模型目录 `~/.local/share/nextalk/models` 不存在或为空
**When** 应用检测模型状态
**Then** 返回"模型缺失"状态，触发下载流程

**Given** 需要下载模型
**When** 执行下载
**Then** 从配置的 URL (HuggingFace/GitHub) 下载模型压缩包
**And** 提供下载进度回调（百分比）
**And** 下载完成后自动解压到模型目录

**Given** 模型文件已下载
**When** 执行完整性校验
**Then** 计算 SHA256 并与预期值比对
**And** 校验失败时删除损坏文件并提示重新下载

**Given** 模型已存在且校验通过
**When** 应用启动
**Then** 直接初始化识别引擎，跳过下载流程

---

### Story 2.5: 音频-推理流水线

**As a** 用户,
**I want** 说话时实时看到识别出的文字,
**So that** 获得即时的视觉反馈。

**Acceptance Criteria:**

**Given** 音频采集和识别引擎均已初始化
**When** 调用 `Pipeline.start()`
**Then** 启动音频采集循环
**And** 每 100ms 音频块自动送入 Sherpa 引擎
**And** 使用同一内存指针，无数据拷贝

**Given** 流水线正在运行
**When** 用户说话
**Then** 识别结果通过 Stream 实时输出
**And** 端到端延迟 < 20ms (NFR1)

**Given** 流水线正在运行
**When** 调用 `Pipeline.stop()`
**Then** 停止音频采集
**And** 返回最终识别结果
**And** 释放相关资源

---

### Story 2.6: VAD 端点检测

**As a** 用户,
**I want** 停止说话后系统自动完成输入,
**So that** 无需手动确认，实现"即说即打"体验。

**Acceptance Criteria:**

**Given** 流水线正在运行，用户正在说话
**When** 检测到持续静音超过阈值（默认 1.5s）
**Then** VAD 触发端点事件
**And** 自动停止录音
**And** 返回最终识别文本

**Given** VAD 配置
**When** 设置自定义静音阈值
**Then** 使用新阈值进行端点检测

**Given** 用户说话中间有短暂停顿（< 1.5s）
**When** VAD 检测
**Then** 不触发端点，继续录音

---

### Story 2.7: 多模型 ASR 支持 (SenseVoice 集成)

**As a** 用户,
**I want** 应用支持多种语音识别模型，可通过配置切换不同引擎,
**So that** 我可以根据场景选择最适合的识别方案 (流式低延迟 vs 离线高精度)。

**Acceptance Criteria:**

**Given** 当前系统仅支持 Zipformer 流式模型
**When** 重构 ASR 架构
**Then** 创建统一的 `ASREngine` 抽象接口
**And** 现有 Zipformer 功能通过 `ZipformerEngine` 实现
**And** 新增 `SenseVoiceEngine` 实现离线识别 (VAD + SenseVoice)
**And** 引擎切换不影响上层调用

**Given** 用户在配置中选择 SenseVoice 引擎
**When** 初始化识别系统
**Then** 使用 Silero VAD 进行语音活动检测
**And** VAD 检测到语音段后送入 SenseVoice 识别
**And** 识别结果按段落输出 (伪流式体验)
**And** 输出包含自动标点符号

**Given** 托盘菜单
**When** 用户切换 ASR 引擎
**Then** 支持运行时热切换 (无需重启)
**And** 默认使用 SenseVoice 引擎

---

## Epic 3: 完整产品体验 (The Product)

用户获得无缝、美观的语音输入体验，支持快捷键唤醒、视觉反馈和系统集成。

### Story 3.1: 透明胶囊窗口基础

**As a** 用户,
**I want** 应用窗口是无边框、真透明的悬浮窗,
**So that** 获得现代化、不干扰桌面的视觉体验。

**Acceptance Criteria:**

**Given** 应用启动
**When** 窗口显示
**Then** 窗口无系统边框和标题栏
**And** 窗口背景完全透明（可看到桌面）
**And** 窗口尺寸为 400x120 逻辑像素
**And** 窗口出现在屏幕中央（或上次记忆位置）

**Given** 应用启动
**When** 窗口首次渲染
**Then** 无黑框闪烁现象 (NFR4)
**And** 窗口瞬间出现，无渐变动画

**Given** Linux 桌面环境 (X11/Wayland via XWayland)
**When** 窗口显示
**Then** 兼容 Ubuntu 22.04+ (NFR3)
**And** 窗口层级正确（始终在最前）

---

### Story 3.2: 胶囊 UI 组件

**As a** 用户,
**I want** 看到美观的胶囊形状界面,
**So that** 获得愉悦的视觉体验。

**Acceptance Criteria:**

**Given** 窗口已显示
**When** 渲染胶囊组件
**Then** 胶囊高度 60px，宽度 280-380px（自适应内容）
**And** 圆角 40px（完全圆角）
**And** 背景色 `rgba(25, 25, 25, 0.95)`（深灰微透）
**And** 内发光描边 `rgba(255, 255, 255, 0.2)`
**And** 外部柔和阴影提供悬浮感

**Given** 胶囊组件
**When** 显示内容
**Then** 左侧为状态指示器区域（30x30）
**And** 中间为文本预览区（白色，18px，单行省略）
**And** 右侧为光标区域
**And** 左右内边距各 25px

---

### Story 3.3: 状态机与动画系统

**As a** 用户,
**I want** 通过视觉反馈了解当前状态,
**So that** 清楚知道系统是"正在听"、"处理中"还是"出错了"。

**Acceptance Criteria:**

**Given** 状态为"聆听中"
**When** 渲染状态指示器
**Then** 显示红色实心圆点 (`#FF4757`)
**And** 圆点呼吸动画：Scale 1.0 -> 1.1 -> 1.0，公式 `1.0 + 0.1 * sin(t)`
**And** 波纹扩散动画：1500ms，EaseOutQuad，Scale 1.0->3.0，Opacity 0.5->0.0
**And** 光标闪烁：800ms 周期，EaseInOut

**Given** 状态为"处理中"
**When** 渲染状态指示器
**Then** 红点转为快速脉冲或转圈 Loading
**And** 文字颜色变暗（0.8 opacity）

**Given** 状态为"错误"
**When** 渲染状态指示器
**Then** 圆点变为黄色（警告）或灰色（无设备）
**And** 中间显示错误提示文字

---

### Story 3.4: 系统托盘集成

**As a** 用户,
**I want** 应用在系统托盘驻留,
**So that** 不占用任务栏空间，随时可以访问。

**Acceptance Criteria:**

**Given** 应用启动
**When** 初始化完成
**Then** 系统托盘显示 Nextalk 图标（麦克风图标）
**And** 主窗口默认隐藏

**Given** 托盘图标
**When** 右键点击
**Then** 显示菜单：显示/隐藏、退出
**And** 菜单样式符合系统风格

**Given** 托盘菜单
**When** 点击"显示/隐藏"
**Then** 切换主窗口显示状态

**Given** 托盘菜单
**When** 点击"退出"
**Then** 应用完全退出，释放所有资源

---

### Story 3.5: 全局快捷键监听

> **⚠️ SUPERSEDED by SCP-002**: 本 Story 的原实现方案已被废弃。快捷键监听改为使用系统原生快捷键 + `--toggle` 命令行参数方案。详见 `_bmad-output/sprint-change-proposals/scp-002-simplified-architecture.md`

**As a** 用户,
**I want** 通过快捷键快速唤醒语音输入,
**So that** 无需鼠标操作，实现高效输入。

**技术方案**: ~~Fcitx5 插件侧原生快捷键监听~~ → **系统原生快捷键 + `nextalk --toggle`**

**Acceptance Criteria (SCP-002 更新后):**

**Given** 应用在后台运行
**When** 用户通过系统快捷键触发 `nextalk --toggle`
**Then** 主窗口瞬间出现
**And** 自动开始录音
**And** 状态切换为"聆听中"

**Given** 正在录音
**When** 再次触发快捷键
**Then** 立即停止录音
**And** 提交当前识别文本到活动窗口
**And** 主窗口瞬间隐藏

**Given** 应用已启动
**When** 执行 `nextalk --toggle` / `--show` / `--hide`
**Then** 通过单实例 Socket 发送命令到运行中的实例

~~**Given** 配置文件存在~~
~~**When** 设置自定义快捷键~~
~~**Then** 使用新键位替代默认的 Right Alt~~

~~**Given** Wayland 环境下用户录音时切换窗口~~
~~**When** 停止录音并提交文本~~
~~**Then** 文本仍然提交到原来的窗口 (焦点锁定机制)~~

~~**Given** Fcitx5 插件监听快捷键~~
~~**When** 检测到配置的快捷键按下~~
~~**Then** 通过 Unix Socket (`nextalk-cmd.sock`) 向 Flutter 发送 toggle 命令~~

---

### Story 3.6: 完整业务流串联

**As a** 用户,
**I want** 完整的语音输入体验,
**So that** 可以在任何应用中通过语音快速输入文字。

**Acceptance Criteria:**

**Given** 应用已启动，用户在任意输入框中
**When** 按下 Right Alt
**Then** 胶囊窗口出现，开始录音，红灯呼吸，波纹扩散

**Given** 正在录音
**When** 用户说话
**Then** 文字实时逐字显示在预览区
**And** 文字超长时自动省略（Ellipsis）

**Given** 正在录音
**When** VAD 检测到静音超过 1.5s
**Then** 自动停止录音，提交文字，窗口消失
**And** 文字出现在之前的输入框中

**Given** 正在录音
**When** 用户再次按下 Right Alt
**Then** 手动停止录音，提交文字，窗口消失

**Given** 胶囊窗口可见
**When** 用户拖拽窗口
**Then** 窗口跟随鼠标移动
**And** 松开后记录位置，下次出现在此位置

**Given** Socket 连接断开 / Fcitx5 不可用
**When** 尝试提交文字
**Then** 自动复制文本到系统剪贴板 (SCP-002 剪贴板 fallback)
**And** 状态指示器变为绿色勾选
**And** 显示 "已复制到剪贴板，请粘贴"
**And** 2秒后自动隐藏窗口

~~**Given** Wayland 环境下用户在应用 A 触发录音后切换到应用 B~~
~~**When** 停止录音并提交文字~~
~~**Then** 文字提交到应用 A (焦点锁定机制)~~
~~**And** 不会误提交到应用 B~~

> **SCP-002 变更**: 焦点锁定机制已移除，Wayland 环境下如切换窗口可能导致文本提交到当前焦点窗口。

**Given** 终端应用 (如 gnome-terminal)
**When** 提交文字
**Then** 使用完整 IME 周期 (preedit → commit → clear preedit)
**And** 终端正确显示输入的文字

---

### Story 3.8: 中英双语国际化与托盘语言切换

**As a** 用户,
**I want** 应用支持中英双语界面，并可在系统托盘菜单中切换语言,
**So that** 我可以根据个人习惯选择使用中文或英文界面。

**Acceptance Criteria:**

**Given** 应用首次启动
**When** 检测系统语言设置
**Then** 自动选择匹配的语言 (zh_CN → 中文, en_* → 英文)
**And** 默认回退到中文

**Given** 应用运行中
**When** 右键点击托盘图标
**Then** 菜单中显示"语言 / Language"子菜单
**And** 子菜单包含"简体中文"和"English"两个选项
**And** 当前语言显示勾选标记

**Given** 托盘语言菜单
**When** 用户选择不同语言
**Then** 立即更新所有 UI 文本 (热切换，无需重启)
**And** 语言偏好持久化到配置文件

**Given** 语言设置已保存
**When** 应用重启
**Then** 使用上次选择的语言

---

### Story 3.9: 音频输入设备选择

**As a** 用户,
**I want** 能够选择指定的音频输入设备，而不是强制使用系统默认设备,
**So that** 当默认设备被其他应用（如 EasyEffects）占用时，可以选择其他可用设备继续使用语音输入。

> **实现说明**: 设备枚举使用 `pactl` (PipeWire/PulseAudio) 而非直接访问 ALSA，
> 确保显示的设备与系统设置一致。

**Acceptance Criteria:**

**Given** 用户执行 `nextalk audio`
**When** 命令运行
**Then** 进入交互模式，显示可用设备列表
**And** 显示当前配置的设备及其状态
**And** 等待用户输入选择

**Given** 应用运行中
**When** 右键点击托盘图标
**Then** 菜单中显示"音频输入设备"子菜单
**And** 子菜单列出所有可用输入设备
**And** 当前配置的设备显示勾选标记

**Given** 用户通过 CLI 或托盘菜单选择设备
**When** 选择完成
**Then** 设备名称写入配置文件
**And** 显示"重启后生效"提示

**Given** 配置文件中指定了设备名称
**When** 应用启动
**Then** 按名称匹配设备（精确 → 子串 → 回退默认）

**Given** 配置的设备不可用
**When** 应用启动
**Then** 显示错误提示悬浮窗
**And** 指引用户使用托盘菜单或 CLI 命令选择其他设备

---

## Epic 4: 打包发布 (Distribution)

用户可以通过标准的 DEB 或 RPM 包安装 Nextalk，覆盖主流 Linux 发行版，实现一键部署。

### Story 4.1: 多格式打包脚本 (DEB & RPM)

**As a** 开发者,
**I want** 通过统一脚本构建 DEB 和 RPM 安装包,
**So that** 可以方便地分发和部署应用到主流 Linux 发行版。

**Acceptance Criteria:**

**Given** 项目代码已就绪
**When** 执行 `scripts/build-pkg.sh --deb`
**Then** 自动执行 Flutter release 构建
**And** 自动编译 Fcitx5 插件
**And** 生成符合 Debian 规范的 DEB 包

**Given** 项目代码已就绪
**When** 执行 `scripts/build-pkg.sh --rpm`
**Then** 生成符合 RPM 规范的安装包
**And** 包含与 DEB 包相同的文件结构

**Given** 项目代码已就绪
**When** 执行 `scripts/build-pkg.sh --all`
**Then** 同时生成 DEB 和 RPM 两种格式
**And** 输出目录为 `dist/`

**Given** DEB/RPM 包结构
**When** 检查包内容
**Then** 主应用安装到 `/opt/nextalk/`
**And** Fcitx5 插件安装到 `/usr/lib/<arch>/fcitx5/`
**And** 插件配置安装到 `/usr/share/fcitx5/addon/`
**And** 桌面入口安装到 `/usr/share/applications/`
**And** 图标安装到 `/usr/share/icons/hicolor/`

**Given** 安装包执行安装/卸载
**When** 系统语言为中文 (`LANG=zh_*`)
**Then** postinst/prerm 脚本显示中文提示
**When** 系统语言为其他语言
**Then** 显示英文提示

**Given** 安装或卸载完成
**When** Fcitx5 正在运行
**Then** 自动重启 Fcitx5 以加载/卸载插件

---

### Story 4.2: 安装与卸载脚本

**As a** 用户,
**I want** 安装后自动完成必要的配置,
**So that** 无需手动操作即可使用。

**Acceptance Criteria:**

**Given** 用户执行 `sudo dpkg -i nextalk_*.deb`
**When** 安装完成
**Then** postinst 脚本创建 `/usr/bin/nextalk` 符号链接
**And** 输出提示："请执行 fcitx5 -r 重启输入法以加载插件"

**Given** 用户执行 `sudo apt remove nextalk`
**When** 卸载进行
**Then** prerm 脚本清理符号链接
**And** 不删除用户数据目录 `~/.local/share/nextalk/`
**And** 输出提示："用户数据保留在 ~/.local/share/nextalk/"

**Given** 安装过程中出错
**When** 依赖缺失
**Then** 显示清晰的错误信息和解决建议

---

### Story 4.3: 桌面集成

**As a** 用户,
**I want** 应用出现在系统应用菜单中,
**So that** 可以像其他应用一样启动。

**Acceptance Criteria:**

**Given** DEB 包已安装
**When** 打开系统应用菜单
**Then** 显示 "Nextalk" 应用入口
**And** 显示正确的应用图标
**And** 分类为 "工具" 或 "输入法"

**Given** nextalk.desktop 文件
**When** 检查内容
**Then** Name=Nextalk
**And** Comment=高性能离线语音输入
**And** Exec=/opt/nextalk/nextalk
**And** Icon=nextalk
**And** Categories=Utility;

**Given** 应用图标
**When** 检查安装
**Then** 图标安装到 `/usr/share/icons/hicolor/256x256/apps/nextalk.png`
**And** 图标清晰，符合 freedesktop 规范

---

### Story 4.4: Docker 跨发行版兼容编译环境

**As a** 开发者,
**I want** 使用 Docker 容器化编译环境在 Ubuntu 22.04 中构建 Flutter 应用和 Fcitx5 插件,
**So that** 编译产物可以在多个 Linux 发行版（Ubuntu 24.04、Fedora 40/41、Debian 12）上正常运行，无需担心 GLib 符号兼容性问题。

**Acceptance Criteria:**

**Given** 项目根目录
**When** 存在 `docker/Dockerfile.build` 文件
**Then** Dockerfile 基于 `ubuntu:22.04` 镜像
**And** 安装 Flutter 3.32.5 和所有 Linux 桌面开发依赖
**And** 安装 Fcitx5 开发库 (5.0.14 版本)

**Given** Docker 镜像已构建
**When** 执行 `scripts/docker-build.sh`
**Then** 在容器内编译 Flutter 应用和 Fcitx5 插件
**And** 编译产物输出到宿主机

**Given** 使用 Docker 容器编译的产物
**When** 检查 `.so` 文件的符号依赖
**Then** 不包含 `g_once_init_enter_pointer` 符号 (GLib 2.80+ 专有)

**Given** 容器编译的 Flutter 应用和 Fcitx5 插件
**When** 在 Ubuntu 24.04、Fedora 40/41、Debian 12 上运行
**Then** 应用正常启动并工作

