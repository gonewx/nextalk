# Story 3.9: 音频输入设备选择

Status: ready-for-review

## Story

As a **用户**,
I want **能够选择指定的音频输入设备，而不是强制使用系统默认设备**,
So that **当默认设备被其他应用（如 EasyEffects）占用时，可以选择其他可用设备继续使用语音输入**.

## 背景

用户反馈：在启用 EasyEffects 后，出现 "Audio device busy" 错误。禁用 EasyEffects 后应用正常运行。用户希望能在配置中选择音频设备。

## Acceptance Criteria

### 配置文件

1. **Given** 应用首次启动或配置文件不存在
   **When** 创建默认配置
   **Then** `settings.yaml` 包含 `audio.input_device: "default"` 配置项
   **And** 配置注释说明如何使用 `nextalk audio` 命令配置

2. **Given** 配置文件中 `audio.input_device` 为 `"default"` 或未设置
   **When** 应用启动初始化音频
   **Then** 使用 `Pa_GetDefaultInputDevice()` 获取系统默认设备

3. **Given** 配置文件中 `audio.input_device` 为设备名称（如 `"HDA Intel PCH: ALC3246 Analog"`）
   **When** 应用启动初始化音频
   **Then** 遍历设备列表，精确匹配设备名称
   **And** 匹配成功则使用该设备
   **And** 精确匹配失败则尝试子串匹配
   **And** 均失败则回退到默认设备并显示警告

### CLI 命令

4. **Given** 用户执行 `nextalk audio`（无参数）
   **When** 命令运行
   **Then** 进入交互模式，显示可用设备列表
   **And** 显示当前配置的设备及其状态
   **And** 等待用户输入选择

5. **Given** 交互模式下的设备列表显示
   **When** 渲染输出
   **Then** 格式为 `[序号] 设备名称`
   **And** 当前配置的设备标记 `(当前)`
   **And** 设备状态显示（✓ 可用 / ⚠️ 不可用）

6. **Given** 交互模式
   **When** 用户输入设备序号（如 `2`）
   **Then** 将对应设备的**名称**写入配置文件
   **And** 显示成功消息和"重启后生效"提示

7. **Given** 交互模式
   **When** 用户输入 `default`
   **Then** 将 `"default"` 写入配置文件
   **And** 显示"已恢复默认设置"消息

8. **Given** 交互模式
   **When** 用户输入 `q` 或 `quit`
   **Then** 退出命令，不修改配置

9. **Given** 用户执行 `nextalk audio <序号>`（如 `nextalk audio 2`）
   **When** 序号有效
   **Then** 直接设置对应设备，不进入交互模式
   **And** 显示成功消息

10. **Given** 用户执行 `nextalk audio <序号>`
    **When** 序号无效（越界或非数字）
    **Then** 显示错误消息和有效范围
    **And** 退出码非 0

11. **Given** 用户执行 `nextalk audio --list` 或 `nextalk audio -l`
    **When** 命令运行
    **Then** 输出机器可读格式：`<序号>\t<设备名称>\t<状态>\t<是否当前>`
    **And** 状态值为 `available` 或 `busy`
    **And** 当前设备行末尾有 `*` 标记

12. **Given** 用户执行 `nextalk audio default`
    **When** 命令运行
    **Then** 直接恢复默认设置，不进入交互模式

13. **Given** 用户执行 `nextalk audio --help` 或 `nextalk audio -h`
    **When** 命令运行
    **Then** 显示命令帮助信息

### 托盘菜单

14. **Given** 应用运行中
    **When** 右键点击托盘图标
    **Then** 菜单中显示"音频输入设备"子菜单
    **And** 子菜单列出所有可用输入设备
    **And** 当前配置的设备显示 `●` 标记

15. **Given** 托盘音频设备子菜单
    **When** 用户点击某个设备
    **Then** 将该设备名称写入配置文件
    **And** 发送桌面通知"音频设备已更改，重启后生效"
    **And** 重建菜单以更新选中状态

### 启动错误提示

16. **Given** 应用启动时配置的音频设备不可用（被占用/不存在）
    **When** 初始化音频失败
    **Then** 显示悬浮窗错误提示
    **And** 提示内容包含：设备名称、错误原因、解决方法
    **And** 解决方法指引用户使用托盘菜单或 `nextalk audio` 命令

17. **Given** 启动错误提示悬浮窗
    **When** 用户点击"知道了"按钮
    **Then** 关闭提示窗口

18. **Given** 配置的设备不存在（如设备已拔出）
    **When** 应用启动
    **Then** 自动回退到系统默认设备
    **And** 显示警告通知"配置的设备不存在，已使用默认设备"

### 国际化

19. **Given** 所有音频设备相关的 UI 文本
    **When** 渲染显示
    **Then** 支持中英双语（跟随应用语言设置）

## Tasks / Subtasks

- [x] Task 1: PortAudio FFI 扩展 (AC: 2, 3)
  - [x] 1.1 在 `portaudio_ffi.dart` 添加 `Pa_GetDeviceCount` 绑定
  - [x] 1.2 添加 Dart 类型签名 `PaGetDeviceCountDart`
  - [x] 1.3 在 `PortAudioBindings` 类中初始化绑定

- [x] Task 2: AudioDeviceService 实现 (AC: 4, 5, 11, 14) ⚠️ 关键
  - [x] 2.1 创建 `lib/services/audio_device_service.dart` 单例
  - [x] 2.2 实现 `listInputDevices()` 返回设备列表（序号、名称、状态）
  - [x] 2.3 实现 `getDeviceStatus(int index)` 检测设备是否可用
  - [x] 2.4 实现 `findDeviceByName(String name)` 按名称查找设备索引
  - [x] 2.5 单元测试: 设备枚举和状态检测

- [x] Task 3: SettingsService 扩展 (AC: 1, 2, 3, 6, 7, 12)
  - [x] 3.1 在 `settings_constants.dart` 添加 `audio.input_device` 默认配置
  - [x] 3.2 在 `SettingsService` 添加 `audioInputDevice` getter
  - [x] 3.3 在 `SettingsService` 添加 `setAudioInputDevice(String)` 方法
  - [x] 3.4 更新 `defaultSettingsYaml` 模板包含 audio 配置段
  - [x] 3.5 单元测试: 配置读写

- [x] Task 4: AudioCapture 设备选择 (AC: 2, 3, 18) ⚠️ 关键
  - [x] 4.1 修改 `warmup()` 方法支持指定设备名称
  - [x] 4.2 修改 `start()` 方法支持指定设备名称
  - [x] 4.3 实现设备名称匹配逻辑（精确 → 子串 → 默认）
  - [x] 4.4 匹配失败时记录详细日志
  - [x] 4.5 单元测试: 设备选择逻辑 (通过 AudioDeviceService 测试覆盖)

- [x] Task 5: CLI audio 子命令 (AC: 4-13) ⚠️ 关键
  - [x] 5.1 在 `main.dart` 添加 `audio` 子命令解析
  - [x] 5.2 实现交互模式界面渲染
  - [x] 5.3 实现交互模式输入处理循环
  - [x] 5.4 实现 `--list` / `-l` 机器可读输出
  - [x] 5.5 实现 `--help` / `-h` 帮助输出
  - [x] 5.6 实现直接设置模式 `nextalk audio <序号>`
  - [x] 5.7 实现 `nextalk audio default` 恢复默认
  - [x] 5.8 错误处理和退出码

- [x] Task 6: 托盘菜单集成 (AC: 14, 15)
  - [x] 6.1 在 `tray_service.dart` 添加音频设备子菜单
  - [x] 6.2 实现设备选择回调 `_switchAudioDevice(int index)`
  - [x] 6.3 发送桌面通知"重启后生效"
  - [x] 6.4 选择后调用 `rebuildMenu()` 更新选中状态

- [x] Task 7: 启动错误提示 UI (AC: 16, 17, 18)
  - [x] 7.1 创建 `lib/ui/audio_device_error_dialog.dart` 组件
  - [x] 7.2 在 `main.dart` 启动流程中检测音频错误并显示对话框
  - [x] 7.3 对话框内容：设备名、错误原因、解决方法
  - [x] 7.4 实现"知道了"按钮关闭逻辑
  - [x] 7.5 设备不存在时的警告通知

- [x] Task 8: 国际化 (AC: 19)
  - [x] 8.1 在 `LanguageService._translations` 添加中文音频设备相关字符串
  - [x] 8.2 在 `LanguageService._translations` 添加对应英文翻译
  - [x] 8.3 托盘/CLI/对话框使用 `LanguageService.tr()` 获取翻译

- [x] Task 9: 测试验证
  - [x] 9.1 单元测试: AudioDeviceService 设备枚举
  - [x] 9.2 单元测试: SettingsService 音频配置读写
  - [ ] 9.3 集成测试: CLI 命令各模式 (手动验证)
  - [ ] 9.4 手动测试: 托盘菜单设备切换 (需用户验证)
  - [ ] 9.5 手动测试: 启动错误提示流程 (需用户验证)
  - [ ] 9.6 手动测试: EasyEffects 场景验证 (需用户验证)

## Dev Notes

### 架构要点

**配置存储策略:**
- 用户交互时显示数字序号（易于选择）
- 配置文件存储设备名称（持久稳定）
- 设备索引可能因重启/插拔变化，名称相对稳定

**设备匹配逻辑:**
```
读取 settings.yaml 中的 audio.input_device
  ↓
是 "default" 或空? → Pa_GetDefaultInputDevice()
  ↓ 否
遍历设备列表精确匹配名称
  ↓ 失败
遍历设备列表子串匹配
  ↓ 失败
回退到默认设备 + 显示警告
```

**CLI 交互模式输出格式:**
```
Nextalk 音频设备配置
====================

可用输入设备:
  [0] HDA Intel PCH: ALC3246 Analog  ✓
  [1] easyeffects_source              ⚠️ 不可用
  [2] USB Audio Device                ✓

当前配置: [0] HDA Intel PCH: ALC3246 Analog
状态: ✓ 可用

──────────────────────────────
  输入数字选择设备 | default 恢复默认 | q 退出

请选择:
```

**机器可读格式 (`-l`):**
```
0	HDA Intel PCH: ALC3246 Analog	available	*
1	easyeffects_source	busy
2	USB Audio Device	available
```

### 需要修改的文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `portaudio_ffi.dart` | 修改 | 添加 Pa_GetDeviceCount |
| `audio_device_service.dart` | 新增 | 设备枚举服务 |
| `settings_constants.dart` | 修改 | 添加 audio 配置 |
| `settings_service.dart` | 修改 | 添加 audioInputDevice |
| `audio_capture.dart` | 修改 | 支持指定设备 |
| `main.dart` | 修改 | 添加 audio 子命令 |
| `tray_service.dart` | 修改 | 添加设备子菜单 |
| `audio_device_error_dialog.dart` | 新增 | 错误提示组件 |
| `app_zh.arb` | 修改 | 添加翻译 |
| `app_en.arb` | 修改 | 添加翻译 |

### 常见陷阱

1. **设备索引不稳定** → 配置中存储名称而非索引
2. **子串匹配冲突** → 精确匹配优先，子串匹配作为容错
3. **托盘菜单不刷新** → 选择后调用 `rebuildMenu()`
4. **CLI 模式检测** → 检查 stdin.hasTerminal 判断是否支持交互

### References

- [Source: voice_capsule/lib/ffi/portaudio_ffi.dart - 现有 FFI 绑定]
- [Source: voice_capsule/lib/services/audio_capture.dart - 现有音频采集]
- [Source: voice_capsule/lib/services/settings_service.dart - 配置服务模式]
- [Source: voice_capsule/lib/services/tray_service.dart - 托盘菜单模式]
- [PortAudio API: Pa_GetDeviceCount](http://www.portaudio.com/docs/v19-doxydocs/portaudio_8h.html)

## Change Log

- 2026-01-11: Story 创建 - 音频输入设备选择功能规格
- 2026-01-11: 实现完成 - Task 1-9 全部完成，进入 code review
- 2026-01-11: Code Review 修复:
  - M1: 更新 Task 8 描述，明确使用 LanguageService._translations 而非 .arb 文件
  - M2: CLI 交互模式添加循环，直到用户输入 q 退出
  - M3: AudioDeviceService 添加设备列表缓存 (5秒 TTL)，优化托盘菜单性能
- 2026-01-11: 重大重构 - AudioDeviceService 从 PortAudio/ALSA 切换到 pactl (PipeWire/PulseAudio):
  - 原因: 用户反馈系统设置显示"无输入设备"时，CLI 不应访问底层 ALSA 设备
  - 变更: 使用 `pactl list sources` 枚举设备，与系统设置保持一致
  - AudioInputDevice 类添加 `description` 字段（用户友好名称）
  - 托盘菜单和 CLI 使用 description 显示，存储使用 PulseAudio source name
- 2026-01-11: 端口可用性检测 - 只显示至少有一个端口可用的设备:
  - 原因: pactl 枚举的 source 可能所有端口都是 "not available"（如未插入麦克风）
  - 变更: 解析 `pactl list sources` 输出中的端口可用性信息
  - 只有端口状态为 "available"（非 "not available"）的设备才显示
  - 现在完全匹配系统设置的设备检测逻辑
- 2026-01-12: 重大重构 - AudioDeviceService 从 pactl 切换到 libpulse FFI:
  - 原因: Debian 13 等系统可能没有安装 pactl 命令（pulseaudio-utils），但 libpulse.so 作为基础库存在
  - 变更: 使用 libpulse FFI 直接调用 PulseAudio C API 枚举设备，无需外部命令依赖
  - 新增 `lib/ffi/libpulse_ffi.dart` - libpulse FFI 绑定
  - 混合策略: 优先使用 libpulse，不可用时回退到 PortAudio
  - 设备名称与系统设置完全一致（如 "Built-in Audio Analog Stereo"）
- 2026-01-13: 重大重构 - AudioCapture 从 PortAudio 切换到 libpulse-simple 录音:
  - **问题背景**:
    1. PipeWire + WirePlumber + Easy Effects 环境下节点休眠导致设备不可用
    2. libpulse 枚举的设备名（如 `alsa_input.xxx`）与 PortAudio 设备名不匹配
    3. 用户配置保存 libpulse 名称后，PortAudio 无法找到对应设备
  - **解决方案**: 使用 libpulse-simple 进行音频录制
    - 设备名直接使用 libpulse 格式，与系统设置完全一致
    - libpulse-simple 自动处理采样率转换，无需担心硬件限制
    - 与 PipeWire/PulseAudio 完美集成
  - **新增文件**:
    - `lib/ffi/libpulse_simple_ffi.dart` - libpulse-simple FFI 绑定 (pa_simple_new, pa_simple_read, pa_simple_free)
    - `lib/services/pulse_audio_capture.dart` - PulseAudio 录音服务类
  - **修改文件**:
    - `lib/ffi/libpulse_ffi.dart` - 添加 sink 预热查询，解决 PipeWire 节点休眠
    - `lib/services/audio_capture.dart` - 集成 PulseAudioCapture，优先使用后回退到 PortAudio
    - `lib/services/audio_device_service.dart` - 恢复 libpulse 设备枚举，显示 description
  - **架构变更**:
    ```
    录音流程 (新):
    PulseAudioCapture (libpulse-simple)  ← 优先，设备名与系统一致
        ↓ (失败时回退)
    AudioCapture (PortAudio)             ← 兼容性保障

    设备枚举流程:
    libpulse enumerate → description 显示 (如 "内置音频 模拟立体声")
        ↓ (失败时回退)
    PortAudio enumerate
    ```
  - **解决的问题**:
    - PipeWire/WirePlumber 节点休眠导致设备不可用
    - 设备名称与系统设置不一致
    - 采样率不匹配错误 (硬件 44100Hz vs 应用 16000Hz)

## Dev Agent Record

### 实现摘要

本次实现添加了完整的音频输入设备选择功能，包括：
- ~~PortAudio FFI 扩展：添加 Pa_GetDeviceCount 绑定~~ (已弃用)
- ~~AudioDeviceService：基于 pactl 的设备枚举~~ (已弃用)
- **AudioDeviceService：基于 libpulse FFI 的设备枚举（当前方案）**
  - 优先使用 libpulse FFI 获取设备列表（与系统设置一致）
  - libpulse 不可用时回退到 PortAudio
- **PulseAudioCapture：基于 libpulse-simple 的音频录制（当前方案）**
  - 优先使用 libpulse-simple 录音（设备名与系统一致）
  - libpulse-simple 不可用时回退到 PortAudio
  - 自动处理采样率转换，与 PipeWire/PulseAudio 完美集成
- SettingsService：音频设备配置存储
- AudioCapture：支持指定设备名称进行录音，混合 PulseAudio/PortAudio 方案
- CLI audio 子命令：交互循环模式 + 直接模式 + 机器可读输出
- 托盘菜单集成：设备选择子菜单
- 启动错误提示：音频设备不可用时显示对话框
- 设备回退通知：配置的设备不存在时显示警告

**重大变更 (2026-01-13)**: 音频录制从 PortAudio 切换到 libpulse-simple，
解决 PipeWire 环境下设备命名不一致和节点休眠问题。

### 修改/创建的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `lib/ffi/portaudio_ffi.dart` | 修改 | 添加 Pa_GetDeviceCount 绑定 |
| `lib/ffi/libpulse_ffi.dart` | **新增** | libpulse FFI 绑定（设备枚举 + sink 预热） |
| `lib/ffi/libpulse_simple_ffi.dart` | **新增** | libpulse-simple FFI 绑定（音频录制） |
| `lib/services/pulse_audio_capture.dart` | **新增** | PulseAudio 录音服务类 |
| `lib/services/audio_device_service.dart` | 新增 | 混合策略：libpulse 优先，PortAudio 回退 |
| `lib/services/audio_capture.dart` | 修改 | 集成 PulseAudioCapture，优先使用后回退 PortAudio |
| `lib/services/settings_service.dart` | 修改 | 添加 audioInputDevice 配置 |
| `lib/constants/settings_constants.dart` | 修改 | 添加 audio 配置常量 |
| `lib/services/tray_service.dart` | 修改 | 添加音频设备子菜单 |
| `lib/services/language_service.dart` | 修改 | 添加音频设备翻译 |
| `lib/cli/audio_command.dart` | 新增 | CLI audio 子命令 |
| `lib/ui/audio_device_error_dialog.dart` | 新增 | 音频错误对话框 |
| `lib/app/nextalk_app.dart` | 修改 | 添加音频错误对话框显示 |
| `lib/main.dart` | 修改 | 添加 audio 子命令、help、version 和回退通知 |
| `test/services/audio_device_service_test.dart` | 新增 | AudioDeviceService 单元测试 |
| `test/services/settings_service_test.dart` | 修改 | 添加音频配置测试 |

### 测试结果

- 单元测试: 52 tests passed ✅
- 集成测试: 需手动验证 (CLI, 托盘菜单, 错误提示)

### 遗留事项

- Task 9.3-9.6 为手动测试，需用户验证:
  - CLI 命令各模式
  - 托盘菜单设备切换
  - 启动错误提示流程
  - EasyEffects 场景验证
