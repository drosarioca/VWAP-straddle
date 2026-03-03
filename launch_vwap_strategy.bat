@echo off
echo ========================================================
echo   Launching VWAP Low Non-Rolling Dashboard (Final Version)
echo ========================================================
echo.
echo Activating Environment...
cd /d "c:\Users\Rosario\.gemini\antigravity\scratch\quant_trading"

echo Starting Dashboard...
echo Access at: http://localhost:8501
echo.
streamlit run app.py
pause
