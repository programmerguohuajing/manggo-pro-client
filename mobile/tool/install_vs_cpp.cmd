@echo off
setlocal enabledelayedexpansion
chcp 437 >nul

REM ============================================================
REM  Install Visual Studio "Desktop development with C++" workload
REM  Needed only for `flutter build windows` (Flutter Windows desktop).
REM  NOT needed for Android / iOS / HarmonyOS mobile builds.
REM
REM  Usage: right-click this file -> "Run as administrator"
REM ============================================================

set "SETUP=C:\Program Files (x86)\Microsoft Visual Studio\Installer\setup.exe"
set "VSINSTALLER=C:\Program Files (x86)\Microsoft Visual Studio\Installer\vs_installer.exe"
set "VSW=C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSPATH="

echo ------------------------------------------------------------
echo [1/4] Checking administrator privileges ...
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This script must run as Administrator.
    echo         Right-click the file and choose "Run as administrator".
    pause
    exit /b 1
)
echo       OK - running elevated.

echo.
echo [2/4] Locating Visual Studio instance ...
if exist "%VSW%" (
    for /f "usebackq delims=" %%i in (`"%VSW%" -products * -property installationPath`) do set "VSPATH=%%i"
)

if "%VSPATH%"=="" (
    echo [ERROR] No Visual Studio instance found on this machine.
    echo         Install Visual Studio Community first, then re-run this script.
    pause
    exit /b 1
)
echo       Found: %VSPATH%

echo.
echo [3/4] Adding workload Microsoft.VisualStudio.Workload.NativeDesktop ...
echo       This downloads roughly 7-8 GB and may take 10-30 minutes.
echo       A progress window will appear. Do not close it.
echo.

if exist "%SETUP%" (
    "%SETUP%" modify --installPath "%VSPATH%" --add Microsoft.VisualStudio.Workload.NativeDesktop --includeRecommended --norestart
) else (
    "%VSINSTALLER%" modify --installPath "%VSPATH%" --add Microsoft.VisualStudio.Workload.NativeDesktop --includeRecommended --norestart
)
set "RC=%errorlevel%"
echo.
echo       Installer exit code: %RC%
echo       (0 = success, 3010 = success but reboot recommended, 1602 = cancelled)

echo.
echo [4/4] Verifying installed components ...
if exist "%VSW%" (
    echo --- Workload NativeDesktop ---
    "%VSW%" -products * -requires Microsoft.VisualStudio.Workload.NativeDesktop -property installationPath
    echo --- MSVC compiler tools ---
    "%VSW%" -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    echo --- C++ CMake tools ---
    "%VSW%" -products * -requires Microsoft.VisualStudio.Component.VC.CMake.Project -property installationPath
)

echo.
echo Done. Re-open your terminal, then run:  flutter doctor
echo The line "Visual Studio - develop Windows apps" should now be green.
echo.
echo Optional - add the Windows desktop target to this project:
echo     cd /d "%~dp0.."
echo     flutter create --platforms=windows .
echo     flutter run -d windows
echo.
pause
