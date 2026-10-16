@echo off
title fospeed vision - ROI: qie xia yi kuai lai kan
set PY=python
echo ============================================
echo   fospeed vision : ROI = qie xia yi kuai
echo --------------------------------------------
echo   1) zheng zhang tu : 480 x 640 = 307200 ge
echo   2) img[240:480, 160:480] = qie yi kuai (240 x 320)
echo   3) han kai shi, bu han jie shu (he s[0:3] yi ge gui ju)
echo   14) zhi suan roi = shao suan 230400 ge, zhe jiu shi zhen lv
echo   5) tong yi ge yu zhi, bai zhan bi hui bian
echo   6) sheng cheng out_roi se kuai / er zhi tu .png
echo ============================================
echo.
"%PY%" "%~dp0see_roi.py"
echo.
echo ---- jie shu / EXIT=%ERRORLEVEL% ----
pause >nul
