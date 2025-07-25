@echo off
REM Set temporary PATH to include user Scripts folder
set PATH=%APPDATA%\Python\Python313\Scripts;%PATH%

REM Confirm PyInstaller is available
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] PyInstaller not found. Make sure it's installed correctly.
    pause
    exit /b
)

echo [✓] Building NAND Patcher EXE...

REM Run PyInstaller with your spec file
pyinstaller nand_patcher.spec

echo.
echo [✓] Done! Your EXE is in: dist\NANDPatcher\
pause
