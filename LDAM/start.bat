@echo off
echo ========================================
echo Livestock Health Monitor Pro
echo ========================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo.

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo Starting Flask application...
echo.
echo Web interface will be available at:
echo   http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py
pause
