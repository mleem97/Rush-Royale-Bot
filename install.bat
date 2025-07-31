:: Only has to be run once if not run before
:: Using Python 3.13 for better performance and latest features
C:\Python313\python.exe -m venv .venv313
:: if this does not work add the path to where your Python 3.13 installation is located.
call .venv313\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
:: Handle scrcpy-client dependency conflicts by installing separately
pip install --no-deps scrcpy-client
pip install av>=15.0.0
echo.
echo All dependencies installed successfully!
echo This includes: NumPy, Pandas, OpenCV, Matplotlib, scikit-learn, 
echo scrcpy-client, adbutils, pure-python-adb, and more.
echo.
echo Installation complete! Run launch_gui.bat to start the bot.
pause