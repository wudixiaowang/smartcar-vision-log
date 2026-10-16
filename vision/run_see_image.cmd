@echo off
title fospeed vision - see an image as numbers
set PY=python
echo ============================================
echo   fospeed vision : du yi zhang tu cheng yi pai pai shu zi
echo --------------------------------------------
echo   1) img.shape  (480, 640, 3) = gao / kuan / tong dao
echo   2) img[0,0]  yi ge xiang su li zhuang 3 ge shu zi
echo   3) img[0, 0:8]  qie pian, qia chu 8 ge ge zi
echo   4) bian hui + yu zhi: liang du ^> 150 de ge zi you duo shao
echo   5) sheng cheng out_er zhi tu.png
echo ============================================
echo.
"%PY%" "%~dp0see_image.py"
echo.
echo ---- jie shu / EXIT=%ERRORLEVEL% ----
pause >nul
