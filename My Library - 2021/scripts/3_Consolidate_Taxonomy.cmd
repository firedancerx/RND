@echo off
title 3_Consolidate_Taxonomy.cmd
cd /d "%~dp0.."
python scripts\consolidate_taxonomy.py
echo.
pause
