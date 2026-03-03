
import pandas as pd
from datetime import date, time, datetime, timedelta
from backtest_main import run_day_analysis, load_index_data, construct_straddle

target_date = date(2025, 12, 9)
entry_window_mins = 20
min_entry_time = time(9, 34)

# Re-simulate manually to debug loop variables
print(f"--- Deep Debug Re-Entry {target_date} ---")

logs, df, trades = run_day_analysis(
    target_date, 
    min_entry_time=min_entry_time,
    entry_window_mins=entry_window_mins,
    exit_time=time(15, 20),
    sl_min_pts=10,
    sl_max_pts=20,
    trail_trigger=20,
    trail_step=10,
    rolling_step=100
)

# Parse logs to see why no entry after 10:18
print("\n--- Detailed Log Analysis ---")
for log in logs:
    try:
        print(log)
    except UnicodeEncodeError:
        print(log.encode('ascii', 'replace').decode('ascii'))

print("\n--- Market Data Check (Strike 25850) ---")
# Manually load the straddle file to verify the User's hypothesis
try:
    s_df = construct_straddle(target_date, 25850)
    if s_df is not None:
        window_df = s_df[(s_df.index.time >= time(10, 19)) & (s_df.index.time <= time(10, 48))]
        min_close = window_df['Close'].min()
        print(f"Min Close between 10:19 and 10:48: {min_close}")
        print(f"Did it break 98.8? {min_close < 98.8}")
        print("\nDetail:")
        print(window_df[['Close', 'Low']].head(10))
except Exception as e:
    print(f"Error checking manual straddle: {e}")
