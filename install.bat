@echo off
echo ================================
echo Rush Royale Bot - Installation
echo ================================
echo.

:: Check Python Installation
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

:: Show Python Version
for /f "tokens=*" %%i in ('python --version') do echo Found: %%i

:: Check if Python 3.11+ is available
for /f "tokens=2 delims=. " %%i in ('python --version') do set major=%%i
for /f "tokens=3 delims=. " %%i in ('python --version') do set minor=%%i

if %major% LSS 3 (
    echo ERROR: Python version too old! Required: Python 3.11+
    pause
    exit /b 1
)
if %major% EQU 3 if %minor% LSS 11 (
    echo ERROR: Python version too old! Required: Python 3.11+
    pause
    exit /b 1
)

echo Python version is compatible.
echo.

:: Remove old Virtual Environment if exists
if exist ".bot_env" (
    echo Removing old Virtual Environment...
    rmdir /s /q ".bot_env"
)

:: Create new Virtual Environment
echo Creating Virtual Environment...
python -m venv .bot_env
if errorlevel 1 (
    echo ERROR: Virtual Environment could not be created!
    pause
    exit /b 1
)

:: Activate Virtual Environment
echo Activating Virtual Environment...
call .bot_env\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Virtual Environment could not be activated!
    pause
    exit /b 1
)

:: Upgrade pip
echo Updating pip...
python -m pip install --upgrade pip

:: Install Core Dependencies first
echo Installing core dependencies...
pip install wheel setuptools

:: Install specific packages for Python 3.13 compatibility
echo Installing Computer Vision packages...
pip install opencv-python>=4.10.0

echo Installing Machine Learning packages...
pip install scikit-learn>=1.5.0 numpy>=1.24.0 pandas>=2.0.0

echo Installing ADB packages...
pip install pure-python-adb>=0.3.0

echo Installing GUI packages...
pip install Pillow>=10.0.0

echo Installing additional packages...
pip install matplotlib>=3.7.0 jupyter>=1.0.0 configparser>=6.0.0 tqdm>=4.65.0 requests>=2.31.0

:: Check Installation
echo.
echo Checking installation...
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')" 2>nul || echo "OpenCV: Installation error"
python -c "import sklearn; print(f'scikit-learn: {sklearn.__version__}')" 2>nul || echo "scikit-learn: Installation error"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')" 2>nul || echo "NumPy: Installation error"
python -c "import pandas; print(f'Pandas: {pandas.__version__}')" 2>nul || echo "Pandas: Installation error"
python -c "from ppadb.client import Client; print('ADB Client: OK')" 2>nul || echo "ADB Client: Installation error"

echo.
echo ================================
echo Installation successful!
echo ================================
echo.
echo Next steps:
echo 1. Start BlueStacks
echo 2. Enable ADB in BlueStacks settings (Port 5555)
echo 3. Run launch_gui.bat
echo.
pause