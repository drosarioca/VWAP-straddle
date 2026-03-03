
import backtest_sensex
from datetime import date, time

print("TESTING LOG CAPTURE...")
logs, df, trades = backtest_sensex.run_day_analysis(
    target_date=date(2024, 7, 5), # Known active day from previous run
    min_entry_time=time(9, 34),
    entry_window_mins=30,
    exit_time=time(15, 20),
    sl_min_pts=10,
    sl_max_pts=20,
    trail_trigger=20,
    trail_step=10,
    rolling_step=100,
    portfolio_sl=70,
    strategy_mode="NON_ROLLING",
    spot_check_time=time(9, 15)
)

print(f"Captured {len(logs)} log lines.")
if len(logs) > 0:
    print("--- HEAD ---")
    print("\n".join(logs[:3]))
    print("--- TAIL ---")
    print("\n".join(logs[-3:]))
else:
    print("NO LOGS CAPTURED!")
