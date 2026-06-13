@echo off
setlocal
cd /d "%~dp0"
set PYTHON_EXE=python
where py >nul 2>nul
if %errorlevel%==0 set PYTHON_EXE=py -3

%PYTHON_EXE% -m pip install -r requirements.txt
%PYTHON_EXE% -m PyInstaller --noconfirm --clean --windowed --name DDR5OCCalculator --add-data "data;data" main.py
if not exist release mkdir release
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'release\DDR5OCCalculator-windows-x64.zip') { Remove-Item 'release\DDR5OCCalculator-windows-x64.zip' -Force }; Compress-Archive -Path 'dist\DDR5OCCalculator\*' -DestinationPath 'release\DDR5OCCalculator-windows-x64.zip'"
echo Build finished. EXE path: dist\DDR5OCCalculator\DDR5OCCalculator.exe
echo Release package: release\DDR5OCCalculator-windows-x64.zip
pause
