@echo off
title Semantic Taxonomy Pipeline Launcher
color 0A

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:MENU
cls
echo ======================================================================
echo           SEMANTIC TAXONOMY EXTRACTION & LINKING PIPELINE
echo ======================================================================
echo.
echo   [1] Run FULL End-to-End Pipeline (Ingest, Consolidate, Link, Render)
echo   [2] Ingest & Chunk Pending Books Only (Step 1)
echo   [3] Run Global Taxonomy Consolidation & Leader Re-classification (Step 2)
echo   [4] Run Bi-Directional Semantic Cross-Linking & Strength Scoring (Step 3)
echo   [5] Re-render Inline Hyperlinks & Master Index (Step 4)
echo   [6] Start Live Folder Watcher Service (Background Monitor)
echo   [7] Run Background Services & Notification Diagnostics (Step 5)
echo   [8] Exit
echo.
echo ======================================================================
set /p CHOICE="Select an option [1-8]: "

if "%CHOICE%"=="1" goto FULL_PIPELINE
if "%CHOICE%"=="2" goto INGEST_ONLY
if "%CHOICE%"=="3" goto CONSOLIDATE_ONLY
if "%CHOICE%"=="4" goto LINK_ONLY
if "%CHOICE%"=="5" goto RENDER_ONLY
if "%CHOICE%"=="6" goto WATCHER
if "%CHOICE%"=="7" goto DIAGNOSTICS
if "%CHOICE%"=="8" goto END
goto MENU

:FULL_PIPELINE
echo.
echo Launching Full End-to-End Pipeline...
python scripts\main.py
pause
goto MENU

:INGEST_ONLY
echo.
echo Running Ingestion & Task Queue Check...
python scripts\add_all_to_queue.py
pause
goto MENU

:CONSOLIDATE_ONLY
echo.
echo Running Global Taxonomy Consolidation & Leader Reclassification...
python scripts\consolidate_taxonomy.py
pause
goto MENU

:LINK_ONLY
echo.
echo Running Bi-Directional Semantic Cross-Linking...
python scripts\semantic_linker.py
pause
goto MENU

:RENDER_ONLY
echo.
echo Re-rendering Markdown Documents & Master Taxonomy Index...
python scripts\format_markdown_output.py
pause
goto MENU

:WATCHER
echo.
echo Starting Live Folder Watcher Service...
python scripts\watch_folder.py
pause
goto MENU

:DIAGNOSTICS
echo.
echo Running Service & Notification Diagnostics...
python scripts\diagnose_services.py
pause
goto MENU

:END
echo Exiting launcher.
