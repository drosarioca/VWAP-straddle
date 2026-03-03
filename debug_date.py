
import sys
import os
from datetime import date, time
sys.path.append(os.getcwd())
from backtest_main import run_day_analysis

target_date = date(2025, 10, 14)
print(f"--- Diagnosing {target_date} ---")
logs = run_day_analysis(target_date)
for log in logs:
    print(log)
