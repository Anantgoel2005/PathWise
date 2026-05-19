@echo off
echo ==========================================
echo   Starting PathWise Web Dashboard...
echo ==========================================
echo.
echo Launching local server on port 5000 (Headless Mode)
echo.

:: Automatically open the default web browser to the dashboard
start http://localhost:5000

:: Activate virtual environment and run the pipeline without OpenCV windows
call venv\Scripts\activate
python main.py --source videoplayback.mp4 --no-display

pause
