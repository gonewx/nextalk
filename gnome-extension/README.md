# Nextalk GNOME Shell Extension POC

验证 GNOME Shell Extension 方案能否解决 Wayland 下的焦点问题。

## 核心验证目标

1. **置顶显示** - 使用 `addTopChrome()` 添加到顶层
2. **不抢焦点** - 设置 `affectsInputRegion: false`
3. **D-Bus 控制** - Flutter 可通过 D-Bus 控制 UI

## 快速开始

### 1. 安装扩展

```bash
cd gnome-extension
./install.sh
```

### 2. 重启 GNOME Shell

- **Wayland**: 注销并重新登录
- **X11**: 按 `Alt+F2`, 输入 `r`, 按 Enter

### 3. 检查扩展状态

```bash
./test.sh check
```

### 4. 运行演示

```bash
./test.sh demo
```

### 5. 焦点测试 (关键验证)

```bash
./focus_test.sh
```

**测试原理：**
1. 脚本启动后给你 5 秒倒计时
2. 在倒计时内切换到文本编辑器（如 gedit）并开始连续打字
3. 脚本在后台通过 D-Bus 触发 overlay 显示
4. **关键观察**：overlay 显示的瞬间，打字是否中断？

**验证标准：**
| 现象 | 结论 |
|------|------|
| 打字没中断，一直流畅 | ✅ 方案可行 |
| overlay 显示瞬间打字中断 | ❌ 方案有问题 |

## D-Bus 接口

| 方法 | 参数 | 说明 |
|------|------|------|
| `Show` | `boolean` | 显示/隐藏胶囊 |
| `SetText` | `string` | 设置显示文本 |
| `SetState` | `string` | 设置状态 (idle/listening/processing/success) |
| `SetPosition` | `int x, int y` | 设置位置 |
| `GetInfo` | - | 获取当前状态信息 |

### 使用 gdbus 测试

```bash
# 显示胶囊
gdbus call --session \
  --dest com.gonewx.nextalk.Panel \
  --object-path /com/gonewx/nextalk/Panel \
  --method com.gonewx.nextalk.Panel.Show true

# 设置文本
gdbus call --session \
  --dest com.gonewx.nextalk.Panel \
  --object-path /com/gonewx/nextalk/Panel \
  --method com.gonewx.nextalk.Panel.SetText "🎤 正在聆听..."

# 设置状态
gdbus call --session \
  --dest com.gonewx.nextalk.Panel \
  --object-path /com/gonewx/nextalk/Panel \
  --method com.gonewx.nextalk.Panel.SetState "listening"
```

## 查看日志

```bash
journalctl -f -o cat /usr/bin/gnome-shell | grep -i nextalk
```

## 文件结构

```
gnome-extension/
├── nextalk@gonewx.com/
│   ├── metadata.json      # 扩展元数据
│   └── extension.js       # 扩展核心代码
├── install.sh             # 安装脚本
├── uninstall.sh           # 卸载脚本
├── test.sh                # 快速测试脚本 (使用 gdbus)
├── focus_test.sh          # 焦点测试脚本 (关键验证)
└── README.md              # 本文件
```

## 验证成功标准

1. 运行 `./test.sh demo` 能看到胶囊 UI 动画
2. 运行 `./focus_test.sh`，overlay 显示时打字不中断
3. 焦点始终保持在目标应用

如果以上都通过，则证明方案可行！
