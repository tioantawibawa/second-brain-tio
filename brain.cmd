@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0brain.ps1" %*
if "%~1"=="" pause
