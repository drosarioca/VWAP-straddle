
import pandas as pd
from datetime import date, time, datetime, timedelta
from backtest_main import run_day_analysis, load_index_data

# Force specific date
target_date = date(2025, 12, 9)

print(f"--- Debugging Rolling Logic for {target_date} ---")

# Run analysis with default params (entry 09:34)
logs, df, trades = run_day_analysis(
    target_date, 
    min_entry_time=time(9, 34),
    entry_window_mins=20,
    exit_time=time(15, 20),
    sl_min_pts=10,
    sl_max_pts=20,
    trail_trigger=20,
    trail_step=10,
    rolling_step=100
)

print("\n--- Filtered Rolling Logs ---")
for log in logs:
    if "ROLL" in log or "Initial" in log:
        print(log)

print("\n--- Trade Result ---")
print(trades)
