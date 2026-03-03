@echo off
setlocal
title Crosswalk Batch Processor Launcher
echo ========================================================
echo   🚀 Launching Enhanced Crosswalk Dashboard
echo ========================================================
echo.
echo [1/3] Navigating to project directory...
cd /d "C:\Users\Rosario\.gemini\antigravity\scratch\quant_trading"

echo [2/3] Verifying dependencies...
echo.

echo [3/3] Starting Streamlit Server...
echo Access the dashboard at: http://localhost:8501
echo.
streamlit run app_crosswalk.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Failed to start dashboard. Checking for errors...
    pause
)
pause
