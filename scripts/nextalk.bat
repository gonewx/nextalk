@echo off
REM NexTalk launcher script for Windows

REM Get the directory of this script
set "SCRIPT_DIR=%~dp0"

REM Add parent directory to PYTHONPATH
set "PYTHONPATH=%SCRIPT_DIR%..;%PYTHONPATH%"

REM Run NexTalk
python -m nextalk %*