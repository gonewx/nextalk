# Story 4.2: 安装与卸载脚本

Status: done

## Story

As a **用户**,
I want **安装后自动完成必要的配置**,
so that **无需手动操作即可使用 Nextalk**。

## 分析结论

⚠️ **重要发现**: 本 Story 的所有验收标准已在 Story 4-1 (多格式打包脚本) 中完成实现。

Story 4-1 在创建打包脚本时，同时实现了完整的安装/卸载脚本功能：
- `packaging/deb/postinst` - DEB 安装后脚本
- `packaging/deb/prerm` - DEB 卸载前脚本
- `packaging/rpm/nextalk.spec.template` - RPM %post/%preun 脚本

**建议**: 验证现有实现满足所有验收标准后，直接标记为 done。

## Acceptance Criteria

1. **AC1: 安装后符号链接创建**
   - Given 用户执行 `sudo dpkg -i nextalk_*.deb`
   - When 安装完成
   - Then postinst 脚本创建 `/usr/bin/nextalk` 符号链接
   - **状态**: ✅ 已实现 [Source: packaging/deb/postinst#L51]

2. **AC2: 安装后提示重启 Fcitx5**
   - Given 安装完成
   - When postinst 执行
   - Then 输出提示信息
   - **状态**: ✅ 更进一步 - 自动检测并重启 Fcitx5 [Source: packaging/deb/postinst#L13-46]

3. **AC3: 卸载时清理符号链接**
   - Given 用户执行 `sudo apt remove nextalk`
   - When 卸载进行
   - Then prerm 脚本清理符号链接
   - **状态**: ✅ 已实现 [Source: packaging/deb/prerm#L44]

4. **AC4: 保留用户数据**
   - Given 卸载进行
   - When prerm 执行
   - Then 不删除用户数据目录 `~/.local/share/nextalk/`
   - **状态**: ✅ 已实现 - prerm 仅输出提示，不执行删除操作

5. **AC5: 用户数据保留提示**
   - Given 卸载进行
   - When prerm 执行
   - Then 输出提示："用户数据保留在 ~/.local/share/nextalk/"
   - **状态**: ✅ 已实现，支持双语 [Source: packaging/deb/prerm#L52-55]

6. **AC6: 依赖缺失错误处理**
   - Given 安装过程中
   - When 依赖缺失
   - Then 显示清晰的错误信息和解决建议
   - **状态**: ✅ 已实现 - control 文件声明 Depends，dpkg/apt 自动处理
   - 用户运行 `sudo apt install -f` 即可修复依赖

7. **AC7: RPM 包同等功能** (扩展)
   - Given RPM 包安装/卸载
   - Then %post/%preun 脚本实现相同功能
   - **状态**: ✅ 已实现 [Source: packaging/rpm/nextalk.spec.template#L46-146]

## Tasks / Subtasks

由于所有功能已在 Story 4-1 中实现，本 Story 的任务改为验证性质：

- [x] Task 1: 验证 DEB 安装脚本 (AC: 1, 2)
  - [x] 1.1 确认 postinst 包含符号链接创建 (`ln -sf /opt/nextalk/nextalk /usr/bin/nextalk`)
  - [x] 1.2 确认 Fcitx5 自动重启功能 (`restart_fcitx5` 函数)

- [x] Task 2: 验证 DEB 卸载脚本 (AC: 3, 4, 5)
  - [x] 2.1 确认 prerm 包含符号链接清理 (`rm -f /usr/bin/nextalk`)
  - [x] 2.2 确认用户数据目录保留 (仅输出提示，不执行删除)
  - [x] 2.3 确认双语提示正确 (中英文各 1 处)

- [x] Task 3: 验证依赖处理 (AC: 6)
  - [x] 3.1 确认 control.template 声明 Depends
  - [x] 3.2 dpkg/apt 自动处理依赖错误机制

- [x] Task 4: 验证 RPM 脚本 (AC: 7)
  - [x] 4.1 确认 spec.template 包含 %post 脚本
  - [x] 4.2 确认 spec.template 包含 %preun 脚本

- [x] Task 5: 验证包构建产物
  - [x] 5.1 DEB 包存在: `dist/nextalk_0.1.0-1_amd64.deb` (27MB)
  - [x] 5.2 RPM 包存在: `dist/nextalk-0.1.0-1.x86_64.rpm` (25MB)
  - [x] 5.3 DEB 包内含 postinst/prerm 脚本

## Dev Notes

### 代码已存在

本 Story 无需新增代码，仅需验证 Story 4-1 中实现的以下文件：

| 文件 | 功能 |
|------|------|
| `packaging/deb/postinst` | DEB 安装后脚本 (88行) |
| `packaging/deb/prerm` | DEB 卸载前脚本 (89行) |
| `packaging/deb/control.template` | 依赖声明 |
| `packaging/rpm/nextalk.spec.template` | RPM %post/%preun |

### 实现亮点

1. **自动重启 Fcitx5**: 比原需求更进一步，无需用户手动执行
2. **多用户支持**: 脚本遍历所有运行 fcitx5 的用户，正确设置 XDG_RUNTIME_DIR
3. **双语支持**: 根据 $LANG 自动切换中英文提示
4. **DEB/RPM 一致性**: 两种格式使用相同的安装/卸载逻辑

### Fcitx5 自动重启实现原理

```bash
# 遍历所有运行 fcitx5 的用户，以该用户身份重启
for pid in $(pgrep -x fcitx5); do
    user=$(ps -o user= -p "$pid")
    uid=$(id -u "$user")
    sudo -u "$user" XDG_RUNTIME_DIR="/run/user/$uid" fcitx5 -r -d
done
```

### 验证命令

```bash
# 安装 DEB 包
sudo dpkg -i dist/nextalk_0.1.0-1_amd64.deb

# 检查符号链接
ls -la /usr/bin/nextalk

# 检查用户数据目录
ls -la ~/.local/share/nextalk/

# 卸载
sudo apt remove nextalk

# 确认用户数据保留
ls -la ~/.local/share/nextalk/
```

### Project Structure Notes

无新增文件，验证现有结构：

```
packaging/
├── deb/
│   ├── control.template    # 依赖声明
│   ├── postinst           # 安装后脚本 ✅
│   ├── prerm              # 卸载前脚本 ✅
│   └── nextalk.desktop
└── rpm/
    └── nextalk.spec.template  # 包含 %post/%preun ✅
```

### References

- [Source: packaging/deb/postinst] - DEB 安装后脚本
- [Source: packaging/deb/prerm] - DEB 卸载前脚本
- [Source: packaging/rpm/nextalk.spec.template#L46-146] - RPM 脚本
- [Source: packaging/deb/control.template#L7] - 依赖声明
- [Source: _bmad-output/implementation-artifacts/4-1-deb-build-script.md] - Story 4-1 完成记录

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

无调试问题

### Completion Notes List

1. **所有验收标准已在 Story 4-1 中实现** - 本 Story 为验证性质
2. **验证通过项目**:
   - ✅ AC1: postinst 创建 `/usr/bin/nextalk` 符号链接 (第51行)
   - ✅ AC2: Fcitx5 自动重启功能 (第13-46行 `restart_fcitx5` 函数)
   - ✅ AC3: prerm 清理符号链接 (第44行)
   - ✅ AC4: 不删除用户数据 (prerm 仅输出提示)
   - ✅ AC5: 双语提示 (中英文各 1 处)
   - ✅ AC6: 依赖声明 (control.template Depends 行)
   - ✅ AC7: RPM %post/%preun 脚本 (spec.template)
3. **Shell 脚本语法验证通过** (`bash -n` 无错误)
4. **DEB 包内脚本验证**: postinst/prerm 已正确包含在包内

### File List

无新增文件 (所有代码在 Story 4-1 中完成)

验证的现有文件:
- `packaging/deb/postinst` (88行)
- `packaging/deb/prerm` (89行)
- `packaging/deb/control.template` (22行)
- `packaging/rpm/nextalk.spec.template` (161行)
- `dist/nextalk_0.1.0-1_amd64.deb` (27MB)
- `dist/nextalk-0.1.0-1.x86_64.rpm` (25MB)

### Change Log

- 2025-12-24: Story 创建，发现所有功能已在 Story 4-1 中实现
- 2025-12-24: 执行验证任务，所有 AC 验证通过，标记为 done

