@echo off
chcp 65001 >nul
title Manggo Pro - 重启服务
echo ========================================================
echo   Manggo Pro - 一键重启托盘客户端 (管理员权限模式)
echo ========================================================
echo.

:: 检查并自动提升管理员权限 (确保能跨权限操作 Claude 等以管理员权限运行的软件)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在以管理员权限提权启动...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

echo 正在清理旧实例并启动全新后台服务...
wscript.exe "%~dp0后台静默启动.vbs"
echo.
echo 启动指令已发出！
echo 提示：服务已在系统托盘运行，若未在右下角直接看到，请点击任务栏右下角的“^”折叠箭头。
timeout /t 3 >nul
