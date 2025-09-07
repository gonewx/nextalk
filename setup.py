#!/usr/bin/env python
"""
NexTalk 安装脚本
用于标准的 Python 包安装和分发
"""

from setuptools import setup, find_packages
import os
import sys
from pathlib import Path

# 读取项目根目录
ROOT_DIR = Path(__file__).parent.resolve()

# 读取 README 文件
readme_path = ROOT_DIR / "README.md"
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "个人轻量级实时语音识别与输入系统"

# 读取 requirements.txt
requirements_path = ROOT_DIR / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
else:
    # 如果没有 requirements.txt，使用 pyproject.toml 中定义的依赖
    requirements = [
        "websockets>=12.0",
        "PyYAML>=6.0",
        "pynput>=1.7.6",
        "pyautogui>=0.9.54",
        "pyperclip>=1.8.2",
        "sounddevice>=0.4.6",
        "numpy>=1.21.0",
    ]

# GUI 依赖（可选）
gui_requirements = [
    "PyQt6>=6.4.0",
    "pillow>=9.0.0",
]

# 开发依赖
dev_requirements = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=22.0.0",
    "flake8>=5.0.0",
    "mypy>=1.0.0",
    "pre-commit>=2.20.0",
]

setup(
    name="nextalk",
    version="0.1.0",
    author="NexTalk Team",
    author_email="contact@nextalk.dev",
    description="个人轻量级实时语音识别与输入系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nextalk/nextalk",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "gui": gui_requirements,
        "dev": dev_requirements,
        "all": gui_requirements + dev_requirements,
    },
    entry_points={
        "console_scripts": [
            "nextalk=nextalk.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "nextalk": [
            "ui/assets/*.png",
            "ui/assets/*.ico",
        ],
    },
    data_files=[
        ("config", ["config/nextalk.yaml"]),
    ],
    zip_safe=False,
    project_urls={
        "Bug Reports": "https://github.com/nextalk/nextalk/issues",
        "Source": "https://github.com/nextalk/nextalk",
        "Documentation": "https://nextalk.dev/docs",
    },
)

if __name__ == "__main__":
    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print("错误: NexTalk 需要 Python 3.8 或更高版本")
        sys.exit(1)
    
    print("使用 'pip install .' 安装 NexTalk")
    print("使用 'pip install -e .' 进行开发模式安装")
    print("使用 'pip install .[gui]' 安装包括 GUI 依赖")
    print("使用 'pip install .[dev]' 安装开发依赖")