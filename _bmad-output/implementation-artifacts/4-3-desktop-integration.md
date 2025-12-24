# Story 4.3: 桌面集成 (Desktop Integration)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **用户**,
I want **应用出现在系统应用菜单中**,
so that **可以像其他应用一样启动，获得标准的 Linux 桌面体验**。

## Acceptance Criteria

1. **AC1: 应用菜单显示**
   - Given DEB/RPM 包已安装
   - When 打开系统应用菜单（如 GNOME Activities、KDE 启动器）
   - Then 显示 "Nextalk" 应用入口
   - And 显示正确的应用图标（麦克风图标）
   - And 分类为 "Utility" 或 "Accessibility"

2. **AC2: Desktop Entry 规范合规**
   - Given `nextalk.desktop` 文件
   - When 使用 `desktop-file-validate` 检查
   - Then 验证通过，无错误
   - And 包含必需字段：Type, Name, Exec, Icon
   - And Categories 符合 freedesktop.org 规范

3. **AC3: 图标规范合规**
   - Given 应用图标安装完成
   - When 检查 `/usr/share/icons/hicolor/256x256/apps/nextalk.png`
   - Then 图标存在且格式为 PNG
   - And 尺寸为 256x256 像素
   - And 图标清晰可辨识

4. **AC4: 应用可从菜单启动**
   - Given 用户点击菜单中的 Nextalk 入口
   - When 系统启动应用
   - Then 应用正常启动（显示系统托盘图标）
   - And 无启动错误或警告

5. **AC5: 中文本地化**
   - Given 系统语言设置为中文 (`LANG=zh_CN.*`)
   - When 查看应用菜单
   - Then 显示中文名称 "Nextalk 语音输入"
   - And 显示中文描述

## Tasks / Subtasks

- [x] Task 1: 验证现有 Desktop Entry 合规性 (AC: 2)
  - [x] 1.1 使用 `desktop-file-validate` 验证 `nextalk.desktop`
  - [x] 1.2 修复任何验证错误或警告
  - [x] 1.3 确保 StartupWMClass 正确设置

- [x] Task 2: 优化图标资源 (AC: 3)
  - [x] 2.1 验证源图标尺寸和质量
  - [x] 2.2 确认图标构建流程（256x256 缩放）
  - [x] 2.3 添加多尺寸图标支持（可选：48x48, 128x128）

- [x] Task 3: 创建验证脚本 (AC: 1, 2, 3, 4)
  - [x] 3.1 创建 `scripts/verify-desktop-integration.sh` 验证脚本
  - [x] 3.2 检查 desktop 文件安装位置和内容
  - [x] 3.3 检查图标安装位置和规格
  - [x] 3.4 检查图标缓存刷新

- [x] Task 4: 端到端测试 (AC: 4, 5)
  - [x] 4.1 在 Ubuntu/GNOME 环境测试菜单显示
  - [x] 4.2 验证应用从菜单启动成功
  - [x] 4.3 验证中文本地化显示

## Dev Notes

### 现有实现状态

Story 4-1 已完成以下工作：
- `packaging/deb/nextalk.desktop` 文件已创建，包含完整的中英文本地化
- `scripts/build-pkg.sh` 已处理图标缩放（使用 ImageMagick convert 命令）
- 安装路径配置正确

### Desktop Entry 当前内容

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Nextalk
Name[zh_CN]=Nextalk 语音输入
GenericName=Voice Input
GenericName[zh_CN]=语音输入
Comment=Offline voice-to-text input for Linux
Comment[zh_CN]=Linux 离线语音输入应用
Exec=/opt/nextalk/nextalk
Icon=nextalk
Terminal=false
Categories=Utility;Accessibility;
Keywords=voice;speech;input;dictation;
Keywords[zh_CN]=语音;输入;听写;识别;
StartupNotify=true
StartupWMClass=nextalk
```

### 图标资源信息

- **源文件**: `voice_capsule/assets/icons/icon.png`
- **源尺寸**: 1560x1561 像素 (RGBA PNG, 3.69MB)
- **目标尺寸**: 256x256 像素
- **安装路径**: `/usr/share/icons/hicolor/256x256/apps/nextalk.png`

### freedesktop.org 规范参考

1. **Desktop Entry Specification**:
   - [Source: https://specifications.freedesktop.org/desktop-entry-spec/]
   - 必需字段: Type, Name
   - 推荐字段: Comment, Exec, Icon, Categories

2. **Icon Theme Specification**:
   - [Source: https://specifications.freedesktop.org/icon-theme-spec/]
   - hicolor 主题作为默认回退主题
   - 推荐尺寸: 48x48, 256x256 (或 scalable SVG)

3. **Categories 规范**:
   - `Utility` - 工具类应用
   - `Accessibility` - 辅助功能类
   - 可同时使用多个分类

### 验证命令参考

```bash
# 验证 desktop 文件
desktop-file-validate /usr/share/applications/nextalk.desktop

# 刷新图标缓存
sudo gtk-update-icon-cache /usr/share/icons/hicolor

# 更新桌面数据库
sudo update-desktop-database /usr/share/applications

# 检查图标尺寸
identify /usr/share/icons/hicolor/256x256/apps/nextalk.png
```

### Project Structure Notes

现有文件:
- `packaging/deb/nextalk.desktop` - 桌面入口定义
- `voice_capsule/assets/icons/icon.png` - 源图标
- `scripts/build-pkg.sh` - 构建脚本（包含图标处理）

新增文件:
- `scripts/verify-desktop-integration.sh` - 验证脚本（待创建）

### 依赖注意事项

验证工具需要安装：
```bash
# Ubuntu/Debian
sudo apt install desktop-file-utils imagemagick

# Fedora/RHEL
sudo dnf install desktop-file-utils ImageMagick
```

### References

- [Source: docs/architecture.md#5.3] - 发布包布局
- [Source: _bmad-output/implementation-artifacts/4-1-deb-build-script.md] - DEB 构建实现
- [Source: _bmad-output/epics.md#Story-4.3] - 验收标准定义
- [Source: packaging/deb/nextalk.desktop] - 现有 desktop 文件

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Debug Log References

- desktop-file-validate 验证通过
- 验证脚本输出: 22/22 项通过

### Completion Notes List

1. **Task 1**: Desktop Entry 验证
   - `desktop-file-validate` 验证通过，无错误
   - 修复 APPLICATION_ID 从 "com.nextalk.voice_capsule" 改为 "nextalk" 以匹配 StartupWMClass
   - 所有必需字段 (Type, Name, Exec, Icon) 存在且正确

2. **Task 2**: 图标优化
   - 源图标验证: 1560x1561 PNG RGBA 8-bit, 高质量
   - 添加多尺寸图标支持: 48x48, 128x128, 256x256
   - 更新 build-pkg.sh 和 RPM spec 模板

3. **Task 3**: 验证脚本
   - 创建 `scripts/verify-desktop-integration.sh`
   - 支持 --source, --installed, --all 模式
   - 验证 desktop 文件、图标、二进制、符号链接、图标缓存
   - 修复 desktop 文件权限问题 (644)

4. **Task 4**: 端到端测试
   - 构建 DEB 包并安装成功
   - 验证脚本 22/22 项全部通过
   - 中文本地化正确: Name[zh_CN], Comment[zh_CN], Keywords[zh_CN]
   - 应用二进制有效，依赖正确链接
   - 测试环境: Ubuntu 24.04 LTS, GNOME 46, Fcitx5 5.1.x

### File List

**新增文件:**
- `scripts/verify-desktop-integration.sh` - 桌面集成验证脚本

**修改文件:**
- `voice_capsule/linux/CMakeLists.txt` - APPLICATION_ID 改为 "nextalk"
- `scripts/build-pkg.sh` - 添加多尺寸图标生成，修复 desktop 文件权限
- `packaging/rpm/nextalk.spec.template` - 添加多尺寸图标文件列表
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - 更新 story 状态为 review

### Code Review Fixes

1. **验证脚本退出码修复** - `show_summary` 返回值现在正确传递给 `exit`
2. **移除未使用变量** - 删除 `validate_installed_icons()` 中未使用的 `icon_found` 变量

## Change Log

- 2025-12-24: Code Review 修复 - 验证脚本退出码逻辑、移除未使用变量
- 2025-12-24: Story 4-3 实现完成，所有 AC 验证通过

