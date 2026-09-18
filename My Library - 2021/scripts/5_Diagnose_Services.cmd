@echo off
title 5_Diagnose_Services.cmd
cd /d "%~dp0.."
python scripts\diagnose_services.py
echo.
pause
