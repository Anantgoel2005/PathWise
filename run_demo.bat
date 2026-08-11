@echo off
setlocal
title PathWise Deterministic Demo
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Create it with: python -m venv venv
    echo Then install:   venv\Scripts\pip install -r requirements-test.txt
    pause
    exit /b 1
)

echo Generating the local, model-free hazard demonstration...
venv\Scripts\python.exe demo.py --output output\demo
if errorlevel 1 (
    echo [ERROR] Demo generation failed.
    pause
    exit /b 1
)

echo.
echo Demo complete: output\demo\pathwise-synthetic-demo.mp4
start "" "output\demo\pathwise-synthetic-demo.mp4"
