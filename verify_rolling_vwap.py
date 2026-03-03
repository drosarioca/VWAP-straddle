
from backtest_main import run_day_analysis
import datetime

def test_rolling_vwap():
    target_date = datetime.date(2024, 1, 18)
    print(f"--- Testing ROLLING_VWAP Mode on {target_date} ---")
    
    logs, df, trades = run_day_analysis(
        target_date,
        entry_window_mins=30,
        rolling_step=80,
        portfolio_sl=70,
        strategy_mode="ROLLING_VWAP"
    )
    
    print("\n--- Relevant Logs ---")
    for log in logs:
        if "Filter Updated" in log or "SL Hit" in log:
            print(log.encode('ascii', 'ignore').decode())
            
    print("\n--- Trades ---")
    for t in trades:
        print(t)

if __name__ == "__main__":
    test_rolling_vwap()
