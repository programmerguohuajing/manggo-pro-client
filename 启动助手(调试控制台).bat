@echo off
chcp 65001 >nul
title Manggo Pro - 输入框就地转译助手
echo ========================================================
echo   Manggo Pro 全功能桌面客户端 (调试控制台模式)
echo ========================================================
echo.
echo 正在启动客户端...
echo 提示：若需在后台静默运行，可双击运行同目录下的 [后台静默启动.vbs]
echo.
"C:\Users\A\AppData\Local\Python\pythoncore-3.14-64\python.exe" "%~dp0main.py"
pause
