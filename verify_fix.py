import backtest_main
from datetime import date, time
import pandas as pd
import sys

# Set stdout to utf-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Target Date
target_date = date(2026, 2, 17)

# Same parameters as the reported run
logs, day_df, daily_trades = backtest_main.run_day_analysis(
    target_date,
    min_entry_time=time(9, 32),
    entry_window_mins=30,
    exit_time=time(15, 20),
    sl_min_pts=10,
    sl_max_pts=20,
    trail_trigger=20,
    trail_step=10,
    rolling_step=80,
    portfolio_sl=70,
    strategy_mode="NON_ROLLING",
    spot_check_time=time(9, 32),
    max_entry_time=time(15, 20)
)

print(f"--- Logs for {target_date} ---")
for log in logs:
    print(log)

print("\n--- Trades ---")
for t in daily_trades:
    print(t)

# Check if 09:49 entry exists
has_949_entry = any("09:49:00" in log and "ENTRY" in log for log in logs)
if has_949_entry:
    print("\nFAIL: Entry at 09:49:00 still exists!")
else:
    print("\nSUCCESS: No entry at 09:49:00.")
