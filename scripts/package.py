#!/usr/bin/env python
"""
NexTalk 打包脚本
创建各平台的安装包和分发包
"""

import os
import sys
import shutil
import platform
import subprocess
import zipfile
import tarfile
import json
import argparse
from pathlib import Path
from datetime import datetime

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.resolve()
DIST_DIR = ROOT_DIR / "dist"
RELEASE_DIR = ROOT_DIR / "releases"
TEMP_DIR = ROOT_DIR / "temp_package"

# 平台信息
PLATFORM = platform.system().lower()
ARCH = platform.machine().lower()
VERSION = "0.1.0"

def check_dist_files():
    """检查构建输出文件是否存在"""
    print("检查构建文件...")
    
    if not DIST_DIR.exists():
        print("✗ dist 目录不存在")
        print("  请先运行 python scripts/build.py 构建可执行文件")
        return False
    
    # 检查可执行文件
    exe_files = list(DIST_DIR.glob("nextalk*"))
    if not exe_files:
        print("✗ 未找到可执行文件")
        print("  请先运行 python scripts/build.py 构建可执行文件")
        return False
    
    print(f"✓ 找到构建文件: {len(exe_files)} 个")
    for file in exe_files:
        print(f"  - {file.name}")
    
    return True

def create_package_structure():
    """创建打包目录结构"""
    print("创建打包结构...")
    
    # 清理临时目录
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    
    TEMP_DIR.mkdir(exist_ok=True)
    
    # 创建标准目录结构
    package_name = f"nextalk-{VERSION}-{PLATFORM}-{ARCH}"
    package_dir = TEMP_DIR / package_name
    package_dir.mkdir()
    
    # 复制可执行文件
    if (DIST_DIR / "nextalk").is_dir():
        # onedir 模式
        shutil.copytree(DIST_DIR / "nextalk", package_dir / "bin")
    else:
        # onefile 模式
        bin_dir = package_dir / "bin"
        bin_dir.mkdir()
        
        for exe_file in DIST_DIR.glob("nextalk*"):
            if exe_file.is_file():
                shutil.copy2(exe_file, bin_dir)
    
    # 复制配置文件
    config_dir = package_dir / "config"
    config_dir.mkdir()
    shutil.copy2(ROOT_DIR / "config" / "nextalk.yaml", config_dir)
    
    # 复制文档
    doc_dir = package_dir / "docs"
    doc_dir.mkdir()
    
    # 创建 README
    readme_content = f"""# NexTalk {VERSION}

个人轻量级实时语音识别与输入系统

## 安装说明

### Windows
1. 解压到任意目录
2. 运行 bin/nextalk.exe
3. 系统托盘会出现 NexTalk 图标

### macOS
1. 解压到 Applications 目录
2. 运行 bin/nextalk
3. 首次运行可能需要在系统偏好设置中授予权限

### Linux
1. 解压到 /opt/nextalk 或任意目录
2. 运行 bin/nextalk
3. 可能需要安装额外的系统依赖

## 配置

配置文件位于 config/nextalk.yaml
首次运行会在用户目录创建配置副本：
- Windows: %APPDATA%/nextalk/config.yaml
- macOS: ~/Library/Application Support/nextalk/config.yaml
- Linux: ~/.config/nextalk/config.yaml

## 使用说明

1. 启动程序后，会在系统托盘显示图标
2. 默认快捷键：
   - Ctrl+Alt+Space: 开始/停止语音识别
   - Ctrl+Alt+C: 清除当前识别结果
   - Ctrl+Alt+Q: 退出程序

## 故障排除

如果遇到问题：
1. 检查配置文件是否正确
2. 确保麦克风权限已授予
3. 查看日志文件：~/.nextalk/logs/

## 支持

- 项目主页: https://nextalk.dev
- 问题反馈: https://github.com/nextalk/nextalk/issues
- 文档: https://nextalk.dev/docs

## 版本信息

版本: {VERSION}
构建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
平台: {PLATFORM} ({ARCH})
"""
    
    (doc_dir / "README.md").write_text(readme_content, encoding="utf-8")
    
    # 复制许可证（如果存在）
    license_file = ROOT_DIR / "LICENSE"
    if license_file.exists():
        shutil.copy2(license_file, package_dir)
    else:
        # 创建默认 MIT 许可证
        mit_license = """MIT License

Copyright (c) 2024 NexTalk Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        (package_dir / "LICENSE").write_text(mit_license, encoding="utf-8")
    
    # 创建启动脚本
    if PLATFORM == "windows":
        # Windows 批处理文件
        start_script = """@echo off
cd /d "%~dp0"
start "" "bin\\nextalk.exe"
"""
        (package_dir / "start.bat").write_text(start_script)
    else:
        # Unix shell 脚本
        start_script = """#!/bin/bash
cd "$(dirname "$0")"
./bin/nextalk &
"""
        start_file = package_dir / "start.sh"
        start_file.write_text(start_script)
        start_file.chmod(0o755)
    
    print(f"  已创建: {package_dir}")
    return package_dir

def create_zip_package(package_dir):
    """创建 ZIP 压缩包"""
    print("创建 ZIP 包...")
    
    RELEASE_DIR.mkdir(exist_ok=True)
    
    package_name = package_dir.name
    zip_file = RELEASE_DIR / f"{package_name}.zip"
    
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arc_name = file_path.relative_to(package_dir.parent)
                zf.write(file_path, arc_name)
    
    print(f"  已创建: {zip_file}")
    print(f"  大小: {zip_file.stat().st_size / 1024 / 1024:.2f} MB")
    return zip_file

def create_tar_package(package_dir):
    """创建 tar.gz 压缩包"""
    print("创建 tar.gz 包...")
    
    RELEASE_DIR.mkdir(exist_ok=True)
    
    package_name = package_dir.name
    tar_file = RELEASE_DIR / f"{package_name}.tar.gz"
    
    with tarfile.open(tar_file, 'w:gz') as tf:
        tf.add(package_dir, arcname=package_name)
    
    print(f"  已创建: {tar_file}")
    print(f"  大小: {tar_file.stat().st_size / 1024 / 1024:.2f} MB")
    return tar_file

def create_windows_installer():
    """创建 Windows 安装器（使用 NSIS 或 Inno Setup）"""
    print("创建 Windows 安装器...")
    
    # 创建 Inno Setup 脚本
    iss_content = f"""
[Setup]
AppName=NexTalk
AppVersion={VERSION}
DefaultDirName={{pf}}\\NexTalk
DefaultGroupName=NexTalk
UninstallDisplayIcon={{app}}\\bin\\nextalk.exe
Compression=lzma2
SolidCompression=yes
OutputDir={RELEASE_DIR}
OutputBaseFilename=nextalk-{VERSION}-setup

[Files]
Source: "{TEMP_DIR}\\*"; DestDir: "{{app}}"; Flags: recursesubdirs

[Icons]
Name: "{{group}}\\NexTalk"; Filename: "{{app}}\\bin\\nextalk.exe"
Name: "{{group}}\\Uninstall NexTalk"; Filename: "{{uninstallexe}}"
Name: "{{commondesktop}}\\NexTalk"; Filename: "{{app}}\\bin\\nextalk.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Start automatically with Windows"; GroupDescription: "Startup:"

[Registry]
Root: HKCU; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Run"; ValueType: string; ValueName: "NexTalk"; ValueData: "{{app}}\\bin\\nextalk.exe"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{{app}}\\bin\\nextalk.exe"; Description: "Launch NexTalk"; Flags: nowait postinstall skipifsilent
"""
    
    iss_file = TEMP_DIR / "nextalk.iss"
    iss_file.write_text(iss_content.strip())
    
    print(f"  已创建 Inno Setup 脚本: {iss_file}")
    
    # 检查是否安装了 Inno Setup
    try:
        result = subprocess.run(
            ["iscc", "/Q", str(iss_file)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("  ✓ Windows 安装器创建成功")
        else:
            print("  ✗ Inno Setup 编译失败")
            print("  请安装 Inno Setup: https://jrsoftware.org/isdl.php")
    except FileNotFoundError:
        print("  ⚠ Inno Setup 未安装")
        print("  请安装后运行: iscc", str(iss_file))

def create_macos_dmg():
    """创建 macOS DMG 镜像"""
    print("创建 macOS DMG...")
    
    if PLATFORM != "darwin":
        print("  ⚠ DMG 只能在 macOS 上创建")
        return
    
    dmg_name = f"nextalk-{VERSION}.dmg"
    dmg_file = RELEASE_DIR / dmg_name
    
    # 创建 DMG 的脚本会比较复杂，这里提供基本框架
    print(f"  请使用 create-dmg 工具创建 DMG")
    print(f"  brew install create-dmg")
    print(f"  create-dmg --volname 'NexTalk {VERSION}' {dmg_file} {TEMP_DIR}")

def create_linux_packages():
    """创建 Linux 包（DEB/RPM）"""
    print("创建 Linux 包...")
    
    # 创建 .desktop 文件
    desktop_content = f"""[Desktop Entry]
Version={VERSION}
Type=Application
Name=NexTalk
Comment=个人轻量级实时语音识别与输入系统
Exec=/opt/nextalk/bin/nextalk
Icon=/opt/nextalk/icons/nextalk.png
Categories=Utility;Audio;
StartupNotify=false
Terminal=false
"""
    
    desktop_file = TEMP_DIR / "nextalk.desktop"
    desktop_file.write_text(desktop_content.strip())
    
    print(f"  已创建 .desktop 文件: {desktop_file}")
    
    # 创建 systemd 服务文件
    service_content = """[Unit]
Description=NexTalk Voice Recognition Service
After=network.target

[Service]
Type=simple
ExecStart=/opt/nextalk/bin/nextalk
Restart=on-failure
User=%i

[Install]
WantedBy=multi-user.target
"""
    
    service_file = TEMP_DIR / "nextalk.service"
    service_file.write_text(service_content.strip())
    
    print(f"  已创建 systemd 服务文件: {service_file}")
    print("  使用 fpm 或 dpkg/rpmbuild 创建包")

def create_portable_package(package_dir):
    """创建便携版（免安装版）"""
    print("创建便携版...")
    
    portable_name = f"nextalk-{VERSION}-portable-{PLATFORM}-{ARCH}"
    portable_dir = RELEASE_DIR / portable_name
    
    # 复制到便携版目录
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    shutil.copytree(package_dir, portable_dir)
    
    # 添加便携版配置
    portable_config = {
        "portable": True,
        "data_dir": "./data",
        "config_dir": "./config",
        "log_dir": "./logs"
    }
    
    (portable_dir / "portable.json").write_text(
        json.dumps(portable_config, indent=2)
    )
    
    # 创建数据目录
    (portable_dir / "data").mkdir(exist_ok=True)
    (portable_dir / "logs").mkdir(exist_ok=True)
    
    # 创建便携版压缩包
    if PLATFORM == "windows":
        zip_file = create_zip_package(portable_dir)
    else:
        tar_file = create_tar_package(portable_dir)
    
    # 清理临时便携版目录
    shutil.rmtree(portable_dir)
    
    print("  ✓ 便携版创建完成")

def generate_checksums():
    """生成校验和文件"""
    print("生成校验和...")
    
    import hashlib
    
    checksums = []
    
    for file in RELEASE_DIR.glob("*"):
        if file.is_file() and not file.name.endswith(".sha256"):
            sha256 = hashlib.sha256()
            with open(file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            
            checksum = sha256.hexdigest()
            checksums.append(f"{checksum}  {file.name}")
            print(f"  {file.name}: {checksum[:16]}...")
    
    # 写入校验和文件
    checksum_file = RELEASE_DIR / "checksums.sha256"
    checksum_file.write_text("\n".join(checksums))
    print(f"  已创建: {checksum_file}")

def create_release_notes():
    """创建发布说明"""
    print("创建发布说明...")
    
    release_notes = f"""# NexTalk {VERSION} Release Notes

发布日期: {datetime.now().strftime('%Y-%m-%d')}

## 新特性

- 实时语音识别与转写
- 全局快捷键支持
- 系统托盘集成
- 多应用兼容性
- 自动文本注入

## 改进

- 优化音频采集性能
- 改进网络连接稳定性
- 增强错误处理机制

## 修复

- 修复特殊字符输入问题
- 修复内存泄漏问题
- 修复快捷键冲突检测

## 系统要求

- Windows 10/11 (64-bit)
- macOS 10.15+
- Linux (Ubuntu 20.04+, Fedora 34+)
- Python 3.8+（源码安装）

## 安装说明

### Windows
下载 nextalk-{VERSION}-setup.exe 并运行安装程序

### macOS
下载 nextalk-{VERSION}.dmg 并拖动到 Applications

### Linux
下载对应的 .tar.gz 包并解压到 /opt/nextalk

### 便携版
下载 portable 版本，无需安装即可使用

## 已知问题

- 某些输入法可能影响文本注入
- macOS 需要授予辅助功能权限
- Linux 需要 X11 或 Wayland 支持

## 下一版本计划

- 添加更多语言支持
- 改进 UI 界面
- 支持自定义语音模型
- 添加云同步功能
"""
    
    notes_file = RELEASE_DIR / f"RELEASE_NOTES_{VERSION}.md"
    notes_file.write_text(release_notes, encoding="utf-8")
    print(f"  已创建: {notes_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="NexTalk 打包脚本")
    parser.add_argument(
        "--format",
        choices=["zip", "tar", "all"],
        default="all",
        help="打包格式"
    )
    parser.add_argument(
        "--installer",
        action="store_true",
        help="创建平台特定的安装器"
    )
    parser.add_argument(
        "--portable",
        action="store_true",
        help="创建便携版"
    )
    parser.add_argument(
        "--checksums",
        action="store_true",
        help="生成校验和"
    )
    parser.add_argument(
        "--notes",
        action="store_true",
        help="创建发布说明"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="执行所有打包任务"
    )
    
    args = parser.parse_args()
    
    print(f"NexTalk 打包脚本")
    print(f"版本: {VERSION}")
    print(f"平台: {PLATFORM} ({ARCH})")
    print("-" * 50)
    
    # 检查构建文件
    if not check_dist_files():
        return 1
    
    # 创建打包结构
    package_dir = create_package_structure()
    
    # 创建发布目录
    RELEASE_DIR.mkdir(exist_ok=True)
    
    # 创建压缩包
    if args.format in ["zip", "all"] or args.all:
        create_zip_package(package_dir)
    
    if args.format in ["tar", "all"] or args.all:
        create_tar_package(package_dir)
    
    # 创建便携版
    if args.portable or args.all:
        create_portable_package(package_dir)
    
    # 创建平台特定安装器
    if args.installer or args.all:
        if PLATFORM == "windows":
            create_windows_installer()
        elif PLATFORM == "darwin":
            create_macos_dmg()
        else:
            create_linux_packages()
    
    # 生成校验和
    if args.checksums or args.all:
        generate_checksums()
    
    # 创建发布说明
    if args.notes or args.all:
        create_release_notes()
    
    # 清理临时目录
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    
    print("\n打包完成！")
    print(f"发布目录: {RELEASE_DIR}")
    
    # 显示生成的文件
    print("\n生成的文件:")
    for file in sorted(RELEASE_DIR.glob("*")):
        if file.is_file():
            size = file.stat().st_size / 1024 / 1024
            print(f"  - {file.name} ({size:.2f} MB)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())