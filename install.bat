@echo off
echo Updating pip...
python -m pip install --upgrade pip
echo Installing required libraries...
pip install PyQt5 requests psutil pywin32
echo Installation complete!
pause