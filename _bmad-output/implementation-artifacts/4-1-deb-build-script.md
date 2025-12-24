# Story 4.1: 多格式打包脚本 (DEB & RPM)

Status: done

## Story

As a **开发者**,
I want **通过统一脚本构建 DEB 和 RPM 安装包**,
so that **可以方便地分发和部署应用到主流 Linux 发行版，用户能够使用标准包管理器安装 Nextalk**。

## Acceptance Criteria

1. **AC1: 自动化构建流程**
   - Given 项目代码已就绪
   - When 执行 `scripts/build-pkg.sh --deb`
   - Then 自动执行 Flutter release 构建
   - And 自动编译 Fcitx5 插件
   - And 生成符合 Debian 规范的 DEB 包

2. **AC2: DEB 包结构正确**
   - Given DEB 包生成完成
   - When 检查包内容 (`dpkg -c nextalk_*.deb`)
   - Then 主应用安装到 `/opt/nextalk/` (包含 nextalk 可执行文件、lib/、data/ 目录)
   - And Fcitx5 插件安装到 `/usr/lib/${DEB_HOST_MULTIARCH}/fcitx5/nextalk.so` (架构自适应)
   - And 插件配置安装到 `/usr/share/fcitx5/addon/nextalk.conf`
   - And 桌面入口安装到 `/usr/share/applications/nextalk.desktop`
   - And 图标安装到 `/usr/share/icons/hicolor/256x256/apps/nextalk.png`
   - And `/usr/bin/nextalk` 符号链接指向 `/opt/nextalk/nextalk`

3. **AC3: DEB 元数据正确**
   - Given DEB 包生成完成
   - When 查看 control 文件 (`dpkg -I nextalk_*.deb`)
   - Then Package 名为 `nextalk`
   - And Version 与 pubspec.yaml 一致
   - And 声明依赖：`fcitx5 (>= 5.0)`, `libgtk-3-0 (>= 3.24)`, `libc6 (>= 2.31)`
   - And 声明推荐：`pulseaudio | pipewire-pulse`
   - And Description 包含英文应用描述

4. **AC4: 脚本健壮性**
   - Given 脚本执行
   - When 缺少依赖（如 flutter、cmake）
   - Then 显示清晰的错误信息和安装建议
   - And 脚本以非零状态退出

5. **AC5: RPM 包构建** (扩展)
   - Given 项目代码已就绪
   - When 执行 `scripts/build-pkg.sh --rpm`
   - Then 生成符合 RPM 规范的安装包
   - And 包含与 DEB 包相同的文件结构
   - And 版本号格式符合 RPM 规范 (Version-Release)

6. **AC6: 统一构建脚本** (扩展)
   - Given 构建脚本就绪
   - When 执行 `scripts/build-pkg.sh --all`
   - Then 同时生成 DEB 和 RPM 两种格式
   - And 输出目录为 `dist/`

7. **AC7: 多语言支持** (扩展)
   - Given 安装包执行安装/卸载
   - When 系统语言为中文 (`LANG=zh_*`)
   - Then postinst/prerm 脚本显示中文提示
   - When 系统语言为其他语言
   - Then 显示英文提示

8. **AC8: Fcitx5 自动重启** (扩展)
   - Given 安装或卸载完成
   - When Fcitx5 正在运行
   - Then 自动重启 Fcitx5 以加载/卸载插件

## Tasks / Subtasks

### 原始任务 (DEB 打包)

- [x] Task 1: 创建打包目录结构 (AC: 2)
  - [x] 1.1 创建 `packaging/deb/` 目录
  - [x] 1.2 准备 DEBIAN 控制文件模板 (构建时动态生成到 DEBIAN/ 目录)

- [x] Task 2: 创建 DEBIAN/control 模板 (AC: 3)
  - [x] 2.1 编写 `packaging/deb/control.template` 带版本占位符
  - [x] 2.2 添加正确的依赖声明
  - [x] 2.3 添加英文描述 (国际惯例)

- [x] Task 3: 创建 postinst 脚本 (AC: 2, 7, 8)
  - [x] 3.1 创建 `/usr/bin/nextalk` 符号链接
  - [x] 3.2 自动重启 Fcitx5 (检测运行中的用户进程)
  - [x] 3.3 中英文双语提示 (根据 $LANG 检测)

- [x] Task 4: 创建 prerm 脚本 (AC: 2, 7, 8)
  - [x] 4.1 清理符号链接
  - [x] 4.2 输出用户数据保留提示 (双语)
  - [x] 4.3 自动重启 Fcitx5 以卸载插件

- [x] Task 5: 创建桌面入口文件 (AC: 2)
  - [x] 5.1 创建 `packaging/deb/nextalk.desktop`
  - [x] 5.2 配置正确的 Exec、Icon、Categories
  - [x] 5.3 添加中英文本地化 (Name, Comment, Keywords)

- [x] Task 6: 编写构建脚本 (AC: 1, 4)
  - [x] 6.1 添加依赖检查（flutter, cmake, dpkg-deb, convert/imagemagick）
  - [x] 6.2 从 pubspec.yaml 提取版本号
  - [x] 6.3 执行 Flutter release 构建
  - [x] 6.4 执行 Fcitx5 插件编译
  - [x] 6.5 组装 DEB 包目录结构（含 lib/ 和 data/ 目录）
  - [x] 6.6 处理图标（缩放到 256x256）
  - [x] 6.7 生成 control 文件（替换版本和大小）
  - [x] 6.8 调用 dpkg-deb 打包
  - [x] 6.9 输出构建结果
  - [x] 6.10 支持 --clean 和 --help 选项

### 扩展任务 (RPM 打包 + 统一脚本)

- [x] Task 7: 创建 RPM 打包目录结构 (AC: 5)
  - [x] 7.1 创建 `packaging/rpm/` 目录
  - [x] 7.2 创建 `nextalk.spec.template` RPM spec 模板

- [x] Task 8: 重构为统一构建脚本 (AC: 6)
  - [x] 8.1 将 `build-deb.sh` 重构为 `build-pkg.sh`
  - [x] 8.2 添加 `--deb`, `--rpm`, `--all` 选项
  - [x] 8.3 抽取公共构建逻辑 (Flutter, Fcitx5 插件)
  - [x] 8.4 抽取公共打包结构组装逻辑

- [x] Task 9: 实现 RPM 构建逻辑 (AC: 5)
  - [x] 9.1 检测 rpmbuild 依赖
  - [x] 9.2 正确拆分版本号 (Version + Release)
  - [x] 9.3 生成 spec 文件
  - [x] 9.4 调用 rpmbuild 打包
  - [x] 9.5 复制 RPM 到 dist/ 目录

## Dev Notes

### 架构约束

1. **DEB 包路径规范** [Source: 架构师分析]
   - 主应用: `/opt/nextalk/` (FHS 第三方应用标准位置)
   - Fcitx5 插件: `/usr/lib/${DEB_HOST_MULTIARCH}/fcitx5/` (Debian 多架构路径)
   - 插件配置: `/usr/share/fcitx5/addon/`

2. **RPM 包路径规范**
   - 与 DEB 包保持一致的安装路径
   - 使用 `%{_libdir}`, `%{_datadir}` 宏定义

3. **依赖库打包** [Source: docs/architecture.md#4.2, libs/]
   - `libsherpa-onnx-c-api.so` (4.9MB) - 打包到 `/opt/nextalk/lib/`
   - `libonnxruntime.so` (15MB) - 打包到 `/opt/nextalk/lib/`
   - `libflutter_linux_gtk.so` (~42MB) - Flutter 自带
   - RPATH 已配置为 `$ORIGIN/lib`

4. **不打包模型** [Source: docs/architecture.md#4.4]
   - 模型采用"首次运行下载"策略
   - 存储路径: `~/.local/share/nextalk/models`

### 统一构建脚本使用方法

```bash
# 仅构建 DEB 包
./scripts/build-pkg.sh --deb

# 仅构建 RPM 包
./scripts/build-pkg.sh --rpm

# 构建全部格式
./scripts/build-pkg.sh --all

# 强制重新构建
./scripts/build-pkg.sh --all --rebuild

# 清理临时文件
./scripts/build-pkg.sh --clean
```

### 版本号处理

| 源格式 | DEB 格式 | RPM 格式 |
|--------|----------|----------|
| `0.1.0+1` | `0.1.0-1` | Version: `0.1.0`, Release: `1` |

### 文件命名规范

| 格式 | 命名规范 | 示例 |
|------|----------|------|
| DEB | `<name>_<version>_<arch>.deb` | `nextalk_0.1.0-1_amd64.deb` |
| RPM | `<name>-<version>-<release>.<arch>.rpm` | `nextalk-0.1.0-1.x86_64.rpm` |

### 覆盖发行版

| 格式 | 发行版 |
|------|--------|
| DEB | Ubuntu, Debian, Linux Mint, Pop!_OS, elementary OS |
| RPM | Fedora, CentOS, RHEL, Rocky Linux, AlmaLinux, openSUSE |

### Fcitx5 自动重启实现

```bash
# 遍历所有运行 fcitx5 的用户，以该用户身份重启
for pid in $(pgrep -x fcitx5); do
    user=$(ps -o user= -p "$pid")
    uid=$(id -u "$user")
    sudo -u "$user" XDG_RUNTIME_DIR="/run/user/$uid" fcitx5 -r -d
done
```

### Project Structure

```
packaging/
├── deb/
│   ├── DEBIAN/
│   ├── control.template
│   ├── postinst
│   ├── prerm
│   └── nextalk.desktop
└── rpm/
    └── nextalk.spec.template

scripts/
└── build-pkg.sh    # 统一构建脚本 (替代 build-deb.sh)

dist/
├── nextalk_0.1.0-1_amd64.deb
└── nextalk-0.1.0-1.x86_64.rpm
```

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

无调试问题

### Completion Notes List

**原始任务 (DEB 打包)**:
1. **Task 1 完成**: 创建了 `packaging/deb/` 和 `packaging/deb/DEBIAN/` 目录结构
2. **Task 2 完成**: 创建了 `control.template`，包含版本占位符，英文描述
3. **Task 3 完成**: 创建了 `postinst` 脚本，实现符号链接创建、Fcitx5 自动重启、中英双语提示
4. **Task 4 完成**: 创建了 `prerm` 脚本，实现符号链接清理、用户数据保留提示、Fcitx5 自动重启
5. **Task 5 完成**: 创建了 `nextalk.desktop` 桌面入口文件，支持中英文本地化
6. **Task 6 完成**: 创建了完整的构建脚本

**扩展任务 (RPM + 统一脚本)**:
7. **Task 7 完成**: 创建了 `packaging/rpm/` 目录和 `nextalk.spec.template`
8. **Task 8 完成**: 重构 `build-deb.sh` 为 `build-pkg.sh`，支持 `--deb`, `--rpm`, `--all`
9. **Task 9 完成**: 实现了完整的 RPM 构建逻辑，版本号正确拆分

**验证结果**:
- DEB 构建成功: `dist/nextalk_0.1.0-1_amd64.deb` (27MB)
- RPM 构建成功: `dist/nextalk-0.1.0-1.x86_64.rpm` (24MB)
- DEB 包结构符合 AC2 所有要求
- RPM 包结构符合 AC5 要求
- 脚本支持 `--help`, `--version`, `--clean`, `--rebuild`, `--deb`, `--rpm`, `--all` 选项
- 多语言提示根据 `$LANG` 自动切换
- Fcitx5 安装/卸载时自动重启

### File List

新增文件:
- `packaging/deb/control.template`
- `packaging/deb/postinst`
- `packaging/deb/prerm`
- `packaging/deb/nextalk.desktop`
- `packaging/rpm/nextalk.spec.template`
- `scripts/build-pkg.sh`

修改文件:
- `.gitignore` (添加 `dist/` 到忽略列表)

构建产物 (不纳入版本控制):
- `dist/nextalk_0.1.0-1_amd64.deb`
- `dist/nextalk-0.1.0-1.x86_64.rpm`

注意: `packaging/deb/DEBIAN/` 目录在构建时由脚本动态创建，不纳入版本控制。

### Change Log

- 2025-12-24: 完成 Story 4.1 原始任务，实现 DEB 包自动化构建脚本
- 2025-12-24: 添加多语言支持 (postinst/prerm 根据 $LANG 切换中英文)
- 2025-12-24: 添加 Fcitx5 自动重启功能
- 2025-12-24: 扩展支持 RPM 打包，重构为统一构建脚本 `build-pkg.sh`
- 2025-12-24: [Code Review] 修复 RPM spec 多语言支持、源文件权限、更新 File List
