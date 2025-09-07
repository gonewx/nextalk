# 贡献指南

感谢您对 NexTalk 项目的关注！我们欢迎所有形式的贡献。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [测试要求](#测试要求)
- [文档规范](#文档规范)

## 行为准则

参与本项目即表示您同意遵守我们的行为准则：

1. **尊重**：尊重所有参与者，无论其背景如何
2. **包容**：欢迎不同观点和经验
3. **协作**：接受建设性批评，专注于对社区最有利的事情
4. **专业**：保持专业态度，避免人身攻击

## 如何贡献

### 报告问题

1. 检查问题是否已存在
2. 使用问题模板创建新 issue
3. 提供详细的复现步骤
4. 包含系统信息（OS、Python 版本等）

### 提出新功能

1. 先在 issue 中讨论
2. 说明使用场景和价值
3. 考虑实现复杂度

### 提交代码

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'feat: add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/nextalk/nextalk.git
cd nextalk
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 安装运行时依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-build.txt
pip install -e .[dev]

# 安装 pre-commit hooks
pre-commit install
```

### 4. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_audio.py

# 带覆盖率运行
pytest --cov=nextalk --cov-report=html
```

## 代码规范

### Python 代码风格

我们使用以下工具确保代码质量：

- **Black**：代码格式化（行长度 88）
- **Flake8**：代码检查
- **MyPy**：类型检查
- **isort**：导入排序

运行代码检查：

```bash
# 格式化代码
black nextalk/

# 检查代码
flake8 nextalk/

# 类型检查
mypy nextalk/

# 或使用 make
make lint
make format
```

### 代码组织

```
nextalk/
├── audio/       # 音频处理
├── config/      # 配置管理
├── core/        # 核心逻辑
├── input/       # 输入处理
├── network/     # 网络通信
├── output/      # 输出处理
├── ui/          # 用户界面
└── utils/       # 工具函数
```

### 命名规范

- **模块**：小写下划线 `audio_capture.py`
- **类**：大驼峰 `AudioCaptureManager`
- **函数**：小写下划线 `process_audio_data`
- **常量**：大写下划线 `DEFAULT_SAMPLE_RATE`

### 类型注解

所有公共函数必须包含类型注解：

```python
def process_audio(
    data: np.ndarray,
    sample_rate: int = 16000,
    channels: int = 1
) -> bytes:
    """处理音频数据
    
    Args:
        data: 音频数据数组
        sample_rate: 采样率
        channels: 声道数
    
    Returns:
        处理后的音频字节流
    """
    pass
```

## 提交规范

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型（type）

- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构（既不是新功能也不是修复）
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

### 示例

```bash
feat(audio): add noise reduction feature

- Implement real-time noise reduction
- Add configuration options
- Update documentation

Closes #123
```

## 测试要求

### 测试覆盖率

- 新功能必须包含测试
- 测试覆盖率不低于 80%
- 关键路径覆盖率 100%

### 测试类型

1. **单元测试**：`tests/unit/`
2. **集成测试**：`tests/integration/`
3. **端到端测试**：`tests/e2e/`

### 测试命名

```python
def test_should_process_audio_when_valid_input():
    """测试：当输入有效时应处理音频"""
    pass

def test_should_raise_error_when_invalid_sample_rate():
    """测试：当采样率无效时应抛出错误"""
    pass
```

## 文档规范

### 代码文档

使用 Google 风格的 docstring：

```python
def example_function(param1: str, param2: int) -> bool:
    """函数简短描述
    
    更详细的描述（如需要）。
    可以包含多行。
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述
    
    Returns:
        返回值的描述
    
    Raises:
        ValueError: 何时抛出此异常
    
    Examples:
        >>> example_function("test", 42)
        True
    """
    pass
```

### 用户文档

- 更新 README.md（如有必要）
- 更新 docs/ 目录下的相关文档
- 添加配置示例（如有新配置项）

## Pull Request 流程

1. **更新文档**：确保 README.md 反映了变更
2. **通过测试**：所有测试必须通过
3. **代码审查**：至少需要一名维护者审查
4. **更新 CHANGELOG**：在未发布部分添加变更说明
5. **合并**：由维护者合并到主分支

## 获取帮助

- 查看 [文档](https://nextalk.dev/docs)
- 在 [Discussions](https://github.com/nextalk/nextalk/discussions) 提问
- 加入 [Discord](https://discord.gg/nextalk) 社区

## 致谢

感谢所有贡献者的努力！您的贡献让 NexTalk 变得更好。

## 许可证

通过贡献代码，您同意您的贡献将在 MIT 许可证下发布。