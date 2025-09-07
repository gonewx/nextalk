@echo off
REM NexTalk 一键启动脚本 (Windows)
REM 自动启动 FunASR 服务器和 NexTalk 客户端

echo ============================================================
echo  NexTalk 语音识别系统 - 一键启动
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 使用 Python 脚本
python start_all.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 启动失败，请检查错误信息
    pause
)

exit /b %errorlevel%