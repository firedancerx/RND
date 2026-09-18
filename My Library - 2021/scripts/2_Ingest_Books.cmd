@echo off
title 2_Ingest_Books.cmd
cd /d "%~dp0.."
python scripts\add_all_to_queue.py
echo.
pause
