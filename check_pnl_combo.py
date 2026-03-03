
import pandas as pd
from datetime import time, date, timedelta
import backtest_main
from backtest_main import run_day_analysis, IChartsDataManager, ICHARTS_DIR

def run_combo(start_h, start_m, step):
    print(f"Testing {start_h}:{start_m}, Step {step}...")
    backtest_main.icharts_loader = IChartsDataManager(ICHARTS_DIR)
    
    start_d = date(2024, 1, 1)
    end_d = date(2026, 2, 11) # Include 2026 to see if it causes the drop
    total_pnl = 0.0
    
    curr = start_d
    count = 0
    t_start = time(start_h, start_m)
    
    dates = []
    while curr <= end_d:
        if curr.weekday() < 5:
            dates.append(curr)
        curr += timedelta(days=1)
        
    for d in dates:
        # Quick expiry check optimization?
        # Loader handles it?
        # run_day_analysis returns empty if no expiry/data
        
        # We need to filter properly or rely on run_day_analysis
        # run_day_analysis calls loader.get_nearest_expiry
        
        logs, df, trades = run_day_analysis(
            d,
            min_entry_time=t_start,
            entry_window_mins=30,
            rolling_step=step,
            portfolio_sl=70,
            strategy_mode="ROLLING_VWAP",
            spot_check_time=t_start # Assuming same spot check time
        )
        
        if trades:
            pnl = sum(t.get('PnL', 0) for t in trades)
            total_pnl += pnl
            
        count += 1
        # if count % 50 == 0: print(f"  {count} days: {total_pnl:.2f}...", end='\r')
        
    print(f"Total PnL: {total_pnl:.2f}")

if __name__ == "__main__":
    # Test 09:32, 80
    run_combo(9, 32, 80)
    # Test 09:32, 100 (Already know ~1097)
    # Test 09:35, 80
    run_combo(9, 35, 80)
