@echo off
setlocal EnableDelayedExpansion
title PathWise Video Processing
mode con: cols=100 lines=30
color 0B

echo.
echo  ##########################################################################
echo  #                                                                        #
echo  #         PATHWISE ROAD ACTOR BEHAVIOR PREDICTION SYSTEM                 #
echo  #                                                                        #
echo  ##########################################################################
echo.

cd /d "%~dp0"

:: Check for virtual environment
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run 'python -m venv venv'
    echo         and 'venv\Scripts\pip install -r requirements.txt' first.
    pause
    exit /b
)

echo [READY] Environment verified.
echo.
echo [HINT] Enter a local road-video path. For the model-free portfolio demo,
echo        run run_demo.bat instead.
echo.
set /p video_path=">>> Enter path to video file (or drag/drop): "

if "%video_path%"=="" exit /b

:: Clean quotes
set video_path=%video_path:"=%

if not exist "%video_path%" (
    echo.
    echo [ERROR] File not found: %video_path%
    pause
    exit /b
)

echo.
echo [SYSTEM] Starting PathWise Pipeline...
echo [SOURCE] %video_path%
echo.

:: Launch main script
venv\Scripts\python.exe main.py --source "%video_path%" --show-bev

echo.
echo [SYSTEM] Pipeline terminated. Press any key to exit.
pause > nul
