
import sys
import os
from datetime import date, time
sys.path.append(os.getcwd())
from backtest_main import run_day_analysis, load_index_data

target_date = date(2024, 1, 11)
print(f"--- Diagnosing Rolling Logic for {target_date} ---")

# 1. Test Spot Data Load
spot = load_index_data(target_date)
print(f"Spot Data Loaded: {len(spot) if spot is not None else 'None'}")
if spot is not None:
    print(f"Spot Head: \n{spot.head(3)}")

# 2. Run Analysis with logs
# We pass rolling_step=100
logs, df = run_day_analysis(target_date, rolling_step=100)

print("\n--- Event Logs ---")
for l in logs:
    print(l)

print("\n--- DataFrame Summary ---")
if df is not None and not df.empty:
    print(df.head())
    print(f"Rows: {len(df)}")
else:
    print("Empty DataFrame returned.")
