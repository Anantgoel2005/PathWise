@echo off
setlocal EnableDelayedExpansion
title PathWise Webcam Processing
mode con: cols=100 lines=25
color 0E

echo.
echo  ##########################################################################
echo  #                                                                        #
echo  #         PATHWISE LIVE WEBCAM PIPELINE                                 #
echo  #                                                                        #
echo  ##########################################################################
echo.

cd /d "%~dp0"

:: Check for virtual environment
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please setup 'venv' first.
    pause
    exit /b
)

echo [READY] Environment verified. Live source (0) selected.
echo [NOTE] Ensure your camera is not being used by another app.
echo.

:: Launch main script (defaults to source 0)
venv\Scripts\python.exe main.py --show-bev

echo.
echo [SYSTEM] Live feed closed.
pause > nul
