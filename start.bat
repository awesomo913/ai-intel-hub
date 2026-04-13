@echo off
title AI Intel Hub
cd /d "%~dp0"
python run.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Failed to start AI Intel Hub.
    echo Make sure Python 3.10+ is installed and dependencies are set up.
    echo Run: pip install -r requirements.txt
    pause
)
