
from backtest_main import run_day_analysis
import datetime

def debug_apr24():
    target_date = datetime.date(2025, 4, 24)
    print(f"--- Debugging {target_date} ---")
    
    # Run analysis with standard parameters first
    logs, df, trades = run_day_analysis(
        target_date,
        entry_window_mins=30,
        rolling_step=80,
        portfolio_sl=70,
        strategy_mode="NON_ROLLING"
    )
    

from backtest_main import construct_straddle, icharts_loader, IChartsDataManager

# Need to ensure loader is initialized for construct_straddle
from backtest_main import ICHARTS_DIR
icharts_loader = IChartsDataManager(ICHARTS_DIR)

if __name__ == "__main__":
    target_date = datetime.date(2025, 4, 24)
    print(f"--- Debugging {target_date} (Raw Data) ---")
    
    # 24300 based on initial log
    strike = 24300
    df = construct_straddle(target_date, strike)
    
    if df is not None:
        start = datetime.time(9, 29)
        end = datetime.time(9, 45)
        m = (df.index.time >= start) & (df.index.time <= end)
        print(df.loc[m][['Open', 'High', 'Low', 'Close', 'VWAP']])
    else:
        print("Straddle 24300 not found.")

