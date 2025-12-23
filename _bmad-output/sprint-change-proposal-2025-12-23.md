# Sprint 变更提案: 异常处理系统完善

| 字段 | 值 |
|------|-----|
| **日期** | 2025-12-23 |
| **提案人** | Scrum Master (Bob) |
| **触发原因** | 当前应用缺乏完善的异常处理机制 |
| **变更范围** | Moderate (中等) |

---

## 1. 问题摘要

### 触发因素

用户反馈当前应用在出现各种异常情况时，没有合理的处理逻辑：

1. **初次运行时** - 缺少完整的系统初始化与模型下载引导流程
2. **模型加载失败时** - 未根据不同失败原因给出合理提示
3. **音频检查失败时** - 缺少相应的引导或处理逻辑
4. **其他异常情况** - 需要系统性考虑和方案设计

### 发现时机

实现 Epic 3 (完整产品体验) 后，进行端到端测试时发现异常路径处理不完善。

### 当前状态诊断

| 场景 | 当前处理 | 问题 |
|------|----------|------|
| 初次运行/模型下载 | `print()` 日志，无 UI | 用户无感知 |
| 模型加载失败 | 统一显示 "模型损坏，请重启" | 信息不具体 |
| 音频设备异常 | 显示 3 秒后自动隐藏 | 无恢复指引 |
| Socket 断开 | 显示 "Fcitx5 未连接" | 文本丢失，无重连 |
| 运行时设备断开 | 静默停止 | 用户无感知 |

---

## 2. 影响分析

### Epic 影响

| Epic | 影响程度 | 说明 |
|------|----------|------|
| Epic 1: IPC 桥梁 | 🟡 中 | 需增强 Socket 错误处理 |
| Epic 2: 语音识别引擎 | 🟡 中 | 需增强模型和音频错误处理 |
| Epic 3: 完整产品体验 | 🔴 高 | 需新增初始化向导、错误 UI 组件 |

### Story 影响

| Story | 变更类型 | 说明 |
|-------|----------|------|
| Story 2.4 模型管理器 | 修改 | 新增手动安装支持 |
| Story 3.2 胶囊 UI 组件 | 修改 | 支持错误状态和操作按钮 |
| Story 3.3 状态机与动画 | 修改 | 扩展状态枚举 |
| Story 3.6 完整业务流 | 修改 | 增强异常处理流程 |
| **新增** Story 3.7 | 新增 | 初始化向导与错误处理系统 |

### 技术影响

- **状态管理**: 需扩展 `CapsuleState` 和 `CapsuleErrorType` 枚举
- **UI 组件**: 需新增初始化向导和错误操作组件
- **服务层**: 需增强错误传递和恢复机制

---

## 3. 推荐方案

### 方案选择: 直接调整 (Direct Adjustment)

在现有架构基础上增量添加异常处理功能，无需回滚或重大重构。

### 理由

1. 现有代码已有良好的错误类型定义基础
2. 变更主要是 UI 层和状态管理的增强
3. 不影响核心业务逻辑

---

## 4. 详细变更提案

### 变更 #1: 初次运行与模型下载引导流程

**问题**: `main.dart` 只打印日志，UX 规范 3.2 定义的首次运行页面未实现

**变更内容**:

1. 新增应用启动状态机
2. 实现初始化向导 UI (支持自动下载和手动安装两种模式)
3. 支持下载进度显示、错误重试、切换安装方式

**新增文件**:
- `lib/state/init_state.dart` - 初始化流程状态管理
- `lib/ui/init_wizard/init_mode_selector.dart` - 安装方式选择
- `lib/ui/init_wizard/download_progress.dart` - 下载进度显示
- `lib/ui/init_wizard/manual_install_guide.dart` - 手动安装引导

**修改文件**:
- `lib/main.dart` - 启动时进入初始化流程
- `lib/app/nextalk_app.dart` - 根据状态显示初始化向导或主界面
- `lib/services/model_manager.dart` - 新增 `getDownloadUrl()`, `openModelDirectory()`

**用户流程**:
```
启动 → 检测模型 → 未就绪 → 选择安装方式
                              ├─ 自动下载 → 显示进度 → 完成/失败
                              └─ 手动安装 → 显示链接和路径 → 检测文件
```

---

### 变更 #2: 模型加载失败的细化处理

**问题**: 所有模型错误统一显示 "模型损坏，请重启"

**变更内容**:

1. 细化 `CapsuleErrorType` 枚举
2. 针对不同错误提供具体消息和操作建议

**错误类型细化**:

| 原类型 | 新类型 | 消息 | 操作 |
|--------|--------|------|------|
| `modelError` | `modelNotFound` | "未找到语音模型" | [下载模型] [手动安装] |
| `modelError` | `modelIncomplete` | "模型文件不完整" | [重新下载] [手动安装] |
| `modelError` | `modelCorrupted` | "模型文件损坏" | [删除并重新下载] |
| `modelError` | `modelLoadFailed` | "模型加载失败" | [重试] [查看帮助] |

**修改文件**:
- `lib/state/capsule_state.dart` - 细化枚举和消息映射
- `lib/services/hotkey_controller.dart` - 细化错误映射
- `lib/ui/error_action_widget.dart` - 带操作按钮的错误 UI

---

### 变更 #3: 音频设备异常的引导处理

**问题**: 所有音频错误统一显示 "音频设备异常"

**变更内容**:

1. 细化音频错误类型
2. 针对不同场景提供恢复指引
3. 新增主动设备检测

**错误类型细化**:

| 原类型 | 新类型 | 消息 | 图标 |
|--------|--------|------|------|
| `audioDeviceError` | `audioNoDevice` | "未检测到麦克风" | 灰色 |
| `audioDeviceError` | `audioDeviceBusy` | "麦克风被其他应用占用" | 黄色 |
| `audioDeviceError` | `audioPermissionDenied` | "麦克风权限未授权" | 黄色 |
| `audioDeviceError` | `audioDeviceLost` | "麦克风已断开" | 黄色 |

**修改文件**:
- `lib/state/capsule_state.dart` - 细化音频错误类型
- `lib/services/audio_capture.dart` - 新增 `checkDeviceStatus()` 静态方法
- `lib/services/audio_inference_pipeline.dart` - 传递细化错误类型
- `lib/services/hotkey_controller.dart` - 细化错误处理

---

### 变更 #4: Socket/Fcitx5 连接问题处理

**问题**: 提交失败时文本丢失，错误消息不具体

**变更内容**:

1. UI 层使用 `FcitxError` 细化消息
2. 提交失败时保护用户文本 (复制到剪贴板)
3. 托盘菜单新增 [重新连接] 选项

**提交失败时的文本保护**:
```
录音完成 → 提交失败 → 显示错误 + 保留文本
                         ├─ [复制文本] - 复制到剪贴板
                         ├─ [重试提交] - 重置降级模式并重试
                         └─ [放弃] - 丢弃文本
```

**新增文件**:
- `lib/utils/clipboard_helper.dart` - 剪贴板工具

**修改文件**:
- `lib/state/capsule_state.dart` - 支持携带 `FcitxError`
- `lib/services/hotkey_controller.dart` - 实现文本保护
- `lib/services/tray_service.dart` - 新增 [重新连接] 菜单项
- `lib/ui/error_action_widget.dart` - 支持多按钮和文本显示

---

### 变更 #5: 运行时异常的优雅处理

**问题**: 运行时异常可能导致静默失败或崩溃

**变更内容**:

1. 全局错误边界 (`runZonedGuarded`)
2. 增强 Pipeline 运行时异常处理
3. 诊断日志系统
4. 托盘状态角标

**错误恢复策略**:

| 异常类型 | 严重性 | 恢复策略 |
|----------|--------|----------|
| 设备临时断开 | 中 | 自动重试 3 次 |
| 推理单次失败 | 低 | 重置流，继续 |
| 推理连续失败 | 中 | 停止录音，提示重试 |
| FFI 崩溃 | 高 | 无法恢复，需重启 |

**新增文件**:
- `lib/utils/diagnostic_logger.dart` - 诊断日志工具
- `lib/ui/fatal_error_dialog.dart` - 致命错误对话框

**修改文件**:
- `lib/main.dart` - 添加全局错误边界
- `lib/services/audio_inference_pipeline.dart` - 增强运行时异常处理
- `lib/services/tray_service.dart` - 支持状态角标

---

## 5. 实现交付

### 变更范围分类

**Moderate (中等)**: 需要 Story 新增和现有 Story 修改，但不涉及架构重构。

### 交付物

1. **新增 Story 3.7**: 初始化向导与错误处理系统
2. **修改 Story 3.2, 3.3, 3.6**: 增强错误 UI 和状态管理
3. **新增文件**: 约 8 个新文件
4. **修改文件**: 约 10 个现有文件

### 文件变更汇总

| 文件路径 | 变更类型 | 涉及变更 |
|----------|----------|----------|
| `lib/state/capsule_state.dart` | 修改 | #1 #2 #3 #4 |
| `lib/state/init_state.dart` | 新增 | #1 |
| `lib/main.dart` | 修改 | #1 #5 |
| `lib/app/nextalk_app.dart` | 修改 | #1 |
| `lib/services/model_manager.dart` | 修改 | #1 |
| `lib/services/audio_capture.dart` | 修改 | #3 |
| `lib/services/audio_inference_pipeline.dart` | 修改 | #3 #5 |
| `lib/services/hotkey_controller.dart` | 修改 | #2 #3 #4 #5 |
| `lib/services/tray_service.dart` | 修改 | #4 #5 |
| `lib/ui/init_wizard/*.dart` | 新增 | #1 |
| `lib/ui/error_action_widget.dart` | 新增 | #2 #3 #4 |
| `lib/ui/fatal_error_dialog.dart` | 新增 | #5 |
| `lib/utils/clipboard_helper.dart` | 新增 | #4 |
| `lib/utils/diagnostic_logger.dart` | 新增 | #5 |

### 成功标准

- [ ] 初次运行时显示完整的初始化向导
- [ ] 支持自动下载和手动安装两种模式
- [ ] 模型错误根据具体原因显示不同消息和操作
- [ ] 音频错误提供具体的恢复指引
- [ ] Socket 提交失败时保护用户已识别的文本
- [ ] 运行时异常不会导致静默失败
- [ ] 所有错误 UI 提供可操作的恢复选项

---

## 6. 后续步骤

1. **PM/SM 审批**: 确认变更范围和优先级
2. **创建 Story 3.7**: 详细拆分初始化向导和错误处理的验收标准
3. **更新 sprint-status.yaml**: 添加新 Story 到当前 Sprint
4. **开发实现**: 按优先级实现各变更
5. **测试验证**: 覆盖所有异常场景

---

*文档生成时间: 2025-12-23*
*Correct Course 工作流执行完成*
