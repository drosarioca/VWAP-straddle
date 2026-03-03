
import pandas as pd
from datetime import date, timedelta, time
import backtest_main
from backtest_main import run_day_analysis, IChartsDataManager, ICHARTS_DIR

def check_2026():
    print("Checking Jan 2026 Performance...")
    backtest_main.icharts_loader = IChartsDataManager(ICHARTS_DIR)
    
    start_d = date(2026, 1, 1)
    end_d = date(2026, 2, 10)
    
    curr = start_d
    total_pnl = 0.0
    days = 0
    
    # Use User's PnL Combo: 09:32, 80 Step
    t_start = time(9, 32)
    
    while curr <= end_d:
        if curr.weekday() < 5:
            logs, df, trades = run_day_analysis(
                curr,
                min_entry_time=t_start,
                entry_window_mins=30,
                rolling_step=80,
                portfolio_sl=70,
                strategy_mode="ROLLING_VWAP",
                spot_check_time=t_start
            )
            
            pnl = 0.0
            if trades:
                pnl = sum(t.get('PnL', 0) for t in trades)
                
            total_pnl += pnl
            days += 1
            print(f"  {curr}: {pnl:.2f}")
            
        curr += timedelta(days=1)
        
    print(f"Total Jan-Feb 2026 PnL: {total_pnl:.2f}")

if __name__ == "__main__":
    check_2026()
