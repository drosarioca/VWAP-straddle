@echo off
title Nifty 0 DTE Expiry Analysis Dashboard
echo ============================================================
echo   Nifty 0 DTE Expiry Day Analysis
echo   Launch: http://localhost:8502
echo ============================================================
echo.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
streamlit run app_0dte_analysis.py --server.port 8502
pause
