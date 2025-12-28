# Sprint Change Proposal: SCP-002

## 标题: 极简架构 - 移除 IBus/GNOME Extension/Fcitx5 快捷键

**日期:** 2025-12-28
**发起人:** correct-course 工作流
**优先级:** 高
**状态:** 已批准

---

## 1. 变更摘要

### 1.1 触发原因

经深入技术研究，发现以下限制使原有方案不可行：

| 方案 | 问题 |
|------|------|
| IBus Panel Extension | IBus daemon 硬编码限制，只认识 Emoji 扩展 |
| GNOME Extension + wtype | GNOME/Mutter 不支持 `zwp_virtual_keyboard_v1` 协议 |
| ydotool | 非 ASCII 字符（中文）支持不完整 |
| xdotool 剪贴板方案 | 无法区分终端和普通应用的粘贴快捷键 |

### 1.2 最终方案

**采用极简架构：**

```
┌─────────────────────────────────────────────────────────────┐
│              Nextalk (GDK_BACKEND=x11)                      │
│              Flutter App via XWayland                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        ┌──────────┐             ┌──────────────┐
        │ Fcitx5   │             │ 非 Fcitx5    │
        │ 环境     │             │ 环境         │
        └────┬─────┘             └──────┬───────┘
             │                          │
             ▼                          ▼
      Socket IPC                  复制到剪贴板
      自动上屏                    + UI 提示粘贴
```

**快捷键方案：**
- 使用系统原生快捷键设置（GNOME Settings → Keyboard → Custom Shortcuts）
- Nextalk 支持 `--toggle` 命令行参数

---

## 2. 受影响的 Story

### 2.1 Story 1.5: IBus Panel Extension

**状态变更:** `ready-for-dev` → `cancelled`

**原因:** IBus daemon 硬编码限制

### 2.2 Story 3.5: 全局快捷键监听

**状态变更:** `done` → `superseded`

**变更内容:**
- 移除 Fcitx5 插件侧快捷键监听
- 移除 `nextalk-cmd.sock` 通信
- 移除 `command_server.dart`
- 新增 `--toggle` 命令行参数支持

### 2.3 Story 3.6: 完整业务流串联

**AC 变更:**

| AC | 原内容 | 新内容 |
|----|--------|--------|
| Socket 断开 | 显示 "Fcitx5 未连接" | 复制到剪贴板 + UI 提示 "已复制，请粘贴" |

### 2.4 Story 3.9: GNOME Wayland 兼容性

**状态变更:** `in-progress` → `cancelled`

**原因:** wtype/ydotool 在 GNOME Wayland 下均不可行

---

## 3. 代码变更清单

### 3.1 需要删除的目录/文件

| 路径 | 说明 |
|------|------|
| `addons/ibus/` | IBus Panel Extension 代码 |
| `gnome-extension/` | GNOME Shell Extension |
| `voice_capsule/lib/services/command_server.dart` | Fcitx5 命令接收服务 |
| `voice_capsule/lib/services/gnome_extension_client.dart` | GNOME Extension D-Bus 客户端 |
| `voice_capsule/lib/services/gnome_extension_backend.dart` | GNOME Extension 后端 |
| `voice_capsule/lib/services/platform_detector.dart` | 平台检测（可简化） |
| `voice_capsule/lib/services/window_backend.dart` | 窗口后端抽象（可简化） |

### 3.2 需要修改的文件

| 文件 | 修改内容 |
|------|----------|
| `addons/fcitx5/src/nextalk.cpp` | 移除快捷键监听、焦点锁定、cmd.sock 相关代码 |
| `addons/fcitx5/src/nextalk.h` | 移除快捷键相关成员变量 |
| `voice_capsule/lib/main.dart` | 移除 CommandServer，添加 `--toggle` 参数处理 |
| `voice_capsule/lib/services/hotkey_service.dart` | 移除向 Fcitx5 发送配置的代码 |
| `voice_capsule/lib/services/hotkey_controller.dart` | 简化，移除 Fcitx5 通信 |
| `voice_capsule/lib/services/window_service.dart` | 简化，移除 Extension 后端支持 |
| `voice_capsule/lib/services/fcitx_client.dart` | 添加剪贴板 fallback 逻辑 |

### 3.3 需要新增的功能

| 功能 | 说明 |
|------|------|
| `--toggle` 参数 | main.dart 解析命令行参数，触发窗口/录音切换 |
| 剪贴板 fallback | 非 Fcitx5 环境复制文本到剪贴板 |
| UI 提示组件 | 胶囊显示 "已复制到剪贴板，请粘贴" |

---

## 4. 文档更新清单

| 文档 | 更新内容 |
|------|----------|
| `_bmad-output/epics.md` | 更新 Story 1.5, 3.5, 3.6, 3.9 描述 |
| `docs/adr-001-ibus-support.md` | 添加 v5 最终方案 |
| `docs/architecture.md` | 移除快捷键架构，移除 cmd.sock 描述 |
| `docs/prd.md` | 更新 FR6 快捷键需求描述 |
| `_bmad-output/implementation-artifacts/3-5-global-hotkey-listener.md` | 标记为 superseded |

---

## 5. 变更范围评估

**范围分类:** Major (重大变更)

**影响分析:**
- 移除约 2000+ 行代码 (IBus, GNOME Extension, Fcitx5 快捷键)
- 简化架构，减少 3 个外部组件依赖
- 用户体验略有降低（非 Fcitx5 环境需手动粘贴）

**收益:**
- 维护成本降低 80%
- 架构复杂度大幅降低
- 零外部依赖（wtype/ydotool/GNOME Extension）

---

## 6. 实施路由

**路由到:** Dev Agent

**交付物:**
1. 删除指定目录和文件
2. 修改 Fcitx5 插件代码
3. 修改 Flutter 代码
4. 实现 `--toggle` 参数
5. 实现剪贴板 fallback + UI 提示

**验收标准:**
- [ ] Fcitx5 环境：文本自动上屏正常
- [ ] 非 Fcitx5 环境：文本复制到剪贴板，UI 显示提示
- [ ] `nextalk --toggle` 命令正常切换窗口/录音状态
- [ ] 无编译错误和警告

---

## 7. 参考文档

- [Wayland 文本注入研究](../../docs/research/wayland_text_injection.md)
- [SCP-001: IBus 架构修订](./scp-001-ibus-architecture-revision.md)
- [ADR-001: 支持 IBus 输入法框架](../../docs/adr-001-ibus-support.md)

---

**审批记录:**
- [x] 用户批准 (2025-12-28)
