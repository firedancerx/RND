@echo off
title 4_Render_Markdown.cmd
cd /d "%~dp0.."
python scripts\format_markdown_output.py
echo.
pause
