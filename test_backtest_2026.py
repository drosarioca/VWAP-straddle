
import sys
import os
from datetime import date, time
# Ensure we can import from current dir
sys.path.append(os.getcwd())
from backtest_main import run_backtest

# Run for a 2026 date
# March 2, 2026 is an expiry (DTE 0)
print("Testing Backtest for 2026-03-02...")
try:
    results, summaries = run_backtest(
        years=[2026],
        target_dte=0
    )
    print(f"Results Columns: {results.columns.tolist() if not results.empty else 'Empty'}")
    print(f"Total Trades: {len(results)}")
    if not results.empty:
        print(results.head())
    
    for s in summaries:
        if s['Date'] == date(2026, 3, 2):
            print(f"Summary for 2026-03-02: {s['Day Type']}")
            print(f"PnL: {s['PnL']}")
            # print(f"Logs: {s['Detailed Events']}")
except Exception as e:
    print(f"Error: {e}")
