
from backtest_main import run_day_analysis, IChartsDataManager, ICHARTS_DIR
import datetime

def debug_jan18():
    target_date = datetime.date(2024, 1, 18)
    print(f"--- Debugging {target_date} ---")
    
    # Run analysis with standard parameters
    # Rolling 80, Entry 30 min, Portfolio SL 70
    logs, df, trades = run_day_analysis(
        target_date,
        entry_window_mins=30,
        rolling_step=80,
        portfolio_sl=70
    )
    
    print("\n--- Event Logs ---")
    for log in logs:
        # Filter for relevant logs to reduce noise
        if "ROLL" in log or "Trade" in log or "Reference" in log or "VWAP" in log:
            print(log)
            
    print("\n--- Trades ---")
    for t in trades:
        print(t)

if __name__ == "__main__":
    debug_jan18()
