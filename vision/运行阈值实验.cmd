@echo off
chcp 936 >nul
cd /d "%~dp0"
"%LOCALAPPDATA%\Programs\Python\Python314\python.exe" "ãÐÖµÊµÑé.py" %*
echo.
pause >nul
