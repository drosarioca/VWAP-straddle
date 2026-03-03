
import time
from backtest_main import run_backtest
import datetime

start = time.time()
print("Starting benchmark run (2024-2025)...")

# Run typical params
run_backtest(
    min_entry_time=datetime.time(9, 32),
    entry_window_mins=30,
    exit_time=datetime.time(15, 20),
    years=[2024, 2025]
)

end = time.time()
duration = end - start
print(f"Benchmark completed in {duration:.2f} seconds.")
