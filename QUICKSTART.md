# NexTalk 快速启动指南

本指南帮助您在 5 分钟内启动并运行 NexTalk。

## 📋 前置要求

- Python 3.8 或更高版本
- 麦克风设备
- FunASR 语音识别服务（可选）

## 🚀 快速安装

### 选项 1：使用预构建版本（最简单）

1. 从 [Releases](https://github.com/nextalk/nextalk/releases) 下载您系统对应的版本
2. 解压文件
3. 运行可执行文件

### 选项 2：从源码运行

```bash
# 1. 克隆项目
git clone https://github.com/nextalk/nextalk.git
cd nextalk

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. 安装依赖
# 基础依赖（必需）
pip install -r requirements.txt

# 如果需要 GUI 支持
# pip install -r requirements-gui.txt

# 如果要运行 FunASR 服务器
# pip install -r requirements-server.txt

# 开发依赖（可选）
# pip install -r requirements-dev.txt

# 5. 验证安装
python scripts/verify_installation.py

# 6. 启动 NexTalk
python -m nextalk
```

## 🎯 基本使用

### 方法一：一键启动（推荐）

使用提供的启动脚本同时启动服务器和客户端：

```bash
# Linux/macOS
./start_all.sh

# Windows
start_all.bat

# 或使用 Python
python start_all.py
```

### 方法二：分别启动

#### 1. 启动 FunASR 服务器（必需）

FunASR 服务器提供语音识别功能，必须先启动：

```bash
# 首次运行会自动下载模型（约 2-3GB）
python funasr_wss_server.py
# python funasr_wss_server.py --certfile "" --keyfile "" --ngpu 0 --device cpu

# 等待看到以下输出表示服务器就绪：
# model loaded! only support one client at the same time now!!!!
```

**重要**：保持服务器运行，不要关闭终端窗口。

详细配置请参考 [服务器设置指南](docs/SERVER_SETUP.md)。

#### 2. 启动 NexTalk（新终端窗口）

```bash
# 方式 1：直接运行
nextalk

# 方式 2：Python 模块方式
python -m nextalk -c configs/nextalk.yaml

# 方式 3：使用启动脚本
python scripts/start.py
```

### 3. 使用快捷键

- **开始/停止语音识别**：`Ctrl+Alt+Space`
- **清除识别结果**：`Ctrl+Alt+C`
- **退出程序**：`Ctrl+Alt+Q`

## ⚙️ 基本配置

编辑配置文件 `config/nextalk.yaml`：

```yaml
# 服务器设置
server:
  host: "127.0.0.1"  # FunASR 服务器地址
  port: 10095         # 服务器端口

# 音频设置
audio:
  device: "default"   # 使用默认麦克风

# 快捷键设置
hotkeys:
  start_stop: "ctrl+alt+space"  # 自定义快捷键
```

## 🔧 故障排除

### 问题：无法连接到语音识别服务器

**解决方案**：
1. 确保 FunASR 服务器正在运行
2. 检查防火墙设置
3. 验证配置文件中的服务器地址

### 问题：快捷键不工作

**解决方案**：
1. **macOS**：在系统偏好设置中授予辅助功能权限
2. **Linux**：确保在 X11 环境下运行
3. **Windows**：以管理员权限运行

### 问题：没有声音输入

**解决方案**：
1. 运行 `python scripts/verify_installation.py` 检查音频设备
2. 在配置文件中指定正确的音频设备
3. 检查系统音频权限

## 📊 性能测试

运行性能基准测试：

```bash
python scripts/benchmark.py
```

## 🐛 调试模式

启用详细日志：

```bash
# 调试模式
nextalk --debug

# 或修改配置文件
# advanced:
#   log_level: "DEBUG"
```

## 📦 构建和打包

### 构建可执行文件

```bash
# 使用 Makefile
make build

# 或直接运行脚本
python scripts/build.py --mode onefile --gui
```

### 创建安装包

```bash
# 创建所有格式的包
make package

# 或指定格式
python scripts/package.py --format zip
```

## 🆘 获取帮助

- 查看完整文档：[README.md](README.md)
- 报告问题：[GitHub Issues](https://github.com/nextalk/nextalk/issues)
- 加入讨论：[Discussions](https://github.com/nextalk/nextalk/discussions)

## ✅ 检查清单

完成以下步骤确保 NexTalk 正常工作：

- [ ] Python 3.8+ 已安装
- [ ] 所有依赖已安装（`pip install -r requirements.txt`）
- [ ] FunASR 服务器运行中（如果需要）
- [ ] 麦克风权限已授予
- [ ] 系统托盘图标可见
- [ ] 快捷键响应正常
- [ ] 语音识别功能正常

---

🎉 **恭喜！** 您已成功设置 NexTalk。开始享受语音输入的便利吧！