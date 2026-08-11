@echo off
echo ==========================================
echo   Starting PathWise Web Dashboard...
echo ==========================================
echo.
echo Launching local server on 127.0.0.1:5000 (Headless Mode)
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Create it and install requirements first.
    pause
    exit /b
)

set /p video_path="Enter a local road-video path (leave blank for webcam 0): "
if "%video_path%"=="" set video_path=0
set video_path=%video_path:"=%

:: Automatically open the default web browser to the dashboard
start http://localhost:5000

:: Run the pipeline without OpenCV windows. The dashboard is opt-in and local-only.
venv\Scripts\python.exe main.py --source "%video_path%" --dashboard --no-display

pause
