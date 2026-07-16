@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE=python"
if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python314\python.exe"

%PYTHON_EXE% -m pip install -r requirements.txt
%PYTHON_EXE% -m PyInstaller --noconfirm --clean --windowed --name DDR5OCCalculator --add-data "data;data" main.py
if not exist release mkdir release
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'release\DDR5OCCalculator-v0.4.0-windows-x64.zip') { Remove-Item 'release\DDR5OCCalculator-v0.4.0-windows-x64.zip' -Force }; Compress-Archive -Path 'dist\DDR5OCCalculator\*' -DestinationPath 'release\DDR5OCCalculator-v0.4.0-windows-x64.zip'"
echo Build finished. EXE path: dist\DDR5OCCalculator\DDR5OCCalculator.exe
echo Release package: release\DDR5OCCalculator-v0.4.0-windows-x64.zip
