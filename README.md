# VWAP Strategy & Crosswalk Tool

A professional-grade backtesting and live-monitoring platform for NIFTY/SENSEX straddle strategies, featuring advanced analytics and automated parameter optimization.

## Key Features
- **VWAP Low Non-Rolling Dashboard**: Interactive Streamlit dashboard for strategy visualization.
- **Backtest Engine**: High-performance engine supporting multi-year data, slippage, and lot size variations.
- **Crosswalk Tool**: Batch processing for parameter optimization and extensive metric reporting.
- **Automated Data Retrieval**: Integration with iCharts and Zerodha Kite for seamless data fetching.

## Repository Structure
- `app.py`: Main Strategy Dashboard.
- `app_crosswalk.py`: Crosswalk Optimization Dashboard.
- `backtest_main.py`: Core Backtesting Logic for NIFTY.
- `backtest_sensex.py`: Backtesting Logic for SENSEX.
- `reporting_utils.py`: Enhanced Excel and Metric generation.
- `src/`: Core library components.

## Setup
1. Install dependencies: `pip install pandas streamlit plotly matplotlib requests openpyxl`
2. Configure credentials in `cookie.txt` and `zerodha_token.txt` (local only).
3. Run the dashboard: `streamlit run app.py`

---
*Developed for professional quantitative trading analysis.*
