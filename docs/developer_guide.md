# NexTalk 开发者指南

## 目录

- [项目架构概述](#项目架构概述)
- [开发环境设置](#开发环境设置)
- [代码组织结构](#代码组织结构)
- [测试指南](#测试指南)
- [代码风格指南](#代码风格指南)
- [贡献流程](#贡献流程)
- [常见问题解决](#常见问题解决)

## 项目架构概述

NexTalk 是一个轻量级实时本地语音识别和输入系统，由客户端和服务器两部分组成。详细的架构信息请参阅 [架构文档](architecture.md)。

系统主要组件包括：
- **服务器端**：负责语音识别和处理
- **客户端**：负责音频捕获和文本注入
- **WebSocket通信**：连接客户端和服务器
- **VAD（语音活动检测）**：过滤非语音音频
- **语音识别引擎**：包括Whisper和FunASR模型，执行语音转文本
- **文本注入器**：将识别文本输入到活动窗口

## 开发环境设置

### 系统要求

- Python 3.10.4 或更高版本
- Linux 系统（主要开发和测试平台）
- Git

### 开发依赖

除了基本的运行时依赖外，开发时还需要以下工具和库：

- `pytest` 和 `pytest-asyncio`：用于测试
- `pytest-cov`：用于测试覆盖率报告
- `ruff`：代码格式和静态分析
- `uvicorn[standard]`：用于开发服务器
- `funasr`：用于FunASR模型支持（可选）

### 设置开发环境

1. 克隆仓库：
   ```bash
   git clone https://github.com/your-org/nextalk.git
   cd nextalk
   ```

2. 使用 uv 创建虚拟环境并安装依赖：
   ```bash
   uv venv .venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"  # 安装带开发依赖的项目
   ```

3. 安装系统依赖（Linux）：
   ```bash
   sudo apt-get install xdotool libnotify-bin portaudio19-dev
   ```

4. （可选）安装FunASR支持：
   ```bash
   pip install funasr
   ```

## 代码组织结构

项目代码组织为三个主要包：

```
src/
├── nextalk_shared/  # 共享模块
│   ├── constants.py  # 共享常量
│   └── data_models.py  # 共享数据模型
│
├── nextalk_server/  # 服务器端
│   ├── api/  # API端点
│   ├── asr/  # 语音识别
│   ├── audio/  # 音频处理
│   ├── config/  # 服务器配置
│   └── models/  # 模型管理
│
└── nextalk_client/  # 客户端
    ├── audio/  # 音频捕获
    ├── config/  # 客户端配置
    ├── network/  # 网络通信
    ├── hotkey/  # 热键监听
    ├── injection/  # 文本注入
    └── ui/  # 用户界面
```

## 测试指南

### 测试结构

测试代码组织如下：

```
tests/
├── client/  # 客户端测试
│   ├── unit/  # 单元测试
│   └── integration/  # 集成测试
├── server/  # 服务器测试
│   ├── unit/  # 单元测试
│   └── integration/  # 集成测试
├── shared/  # 共享模块测试
├── fixtures/  # 测试数据
├── conftest.py  # 全局测试夹具
└── pytest.ini  # 测试配置
```

### 运行测试

运行所有测试：
```bash
cd nextalk
python -m pytest
```

运行特定测试组：
```bash
python -m pytest tests/client  # 运行所有客户端测试
python -m pytest tests/server/unit  # 仅运行服务器单元测试
```

生成覆盖率报告：
```bash
python -m pytest --cov=src --cov-report=term-missing
```

### 编写测试

- 使用 `pytest` 框架
- 对于异步代码，使用 `pytest-asyncio`
- 测试文件命名为 `test_*.py`
- 测试函数命名为 `test_*`
- 利用 `conftest.py` 中的夹具

示例：
```python
def test_vad_filter_silence(silence_frame):
    """测试VAD对静音帧的处理"""
    from nextalk_server.audio.vad import VADFilter
    
    vad = VADFilter(sensitivity=2)
    assert vad.is_speech(silence_frame) is False
```

## 代码风格指南

本项目使用 `ruff` 进行代码格式化和静态分析。

### 代码风格规则

- 行长度限制为 100 字符
- 使用 4 空格缩进
- 遵循 PEP 8 命名规范
- 导入顺序：标准库、第三方库、本地模块

### 运行代码检查

```bash
cd nextalk
ruff check .  # 检查代码
ruff format .  # 格式化代码
```

## 贡献流程

### 贡献步骤

1. Fork 仓库并克隆到本地
2. 创建新的特性分支 (`git checkout -b feature/my-feature`)
3. 编写代码和测试
4. 确保所有测试通过 (`pytest`)
5. 确保代码符合风格要求 (`ruff check .`)
6. 提交更改 (`git commit -am '添加新特性'`)
7. 推送到分支 (`git push origin feature/my-feature`)
8. 创建 Pull Request

### 提交规范

提交消息应当包含清晰的描述，建议使用以下前缀：

- `feat:`：新功能
- `fix:`：bug修复
- `docs:`：文档修改
- `style:`：代码格式修改
- `refactor:`：代码重构
- `test:`：添加测试
- `chore:`：更新构建任务、包管理器配置等

示例：`feat: 添加模型切换功能`

## 常见问题解决

### 开发中的常见问题

1. **测试超时问题**
   - 对于WebSocket测试，可能需要增加超时时间
   - 使用 `@pytest.mark.asyncio(timeout=10)` 设置更长的超时

2. **GPU内存问题**
   - 开发时如遇GPU内存不足，可在配置中设置 `device=cpu`
   - 或使用较小的模型（如 `tiny.en` 或 `SenseVoiceSmall`）进行开发

3. **音频设备权限问题**
   - 确保用户在 `audio` 组中
   - 使用 `aplay -l` 和 `arecord -l` 验证设备访问权限

4. **FunASR相关问题**
   - 如果遇到ImportError，确保已安装funasr库：`pip install funasr`
   - 如果遇到模型下载问题，可以手动下载模型到`~/.cache/NexTalk/funasr_models`目录
   - FunASR模型可能会在第一次使用时自动下载，需要确保网络连接良好
   - 使用`ASRRecognizer`类时注意导入检查，避免强制依赖FunASR库

### 调试技巧

- 使用标准库的 `logging` 模块记录详细信息
- 服务器端设置环境变量 `LOG_LEVEL=DEBUG`
- 客户端使用 `--debug` 参数启动，输出更多日志信息
- WebSocket通信问题可使用浏览器开发工具的网络面板检查