
from backtest_main import run_backtest
import pandas as pd

def verify():
    print("Running backtest for Year 2025 only...")
    # Run slightly faster? 
    # We can't easily make it faster without reducing data. 
    # But we can check if it initializes correctly.
    
    # Actually, run_backtest prints "Running backtest on X days...".
    # We can capture stdout or just run it and check results.
    
    res = run_backtest(years=[2025])
    
    if isinstance(res, tuple):
        df, logs = res
    else:
        df = res
        
    if df.empty:
        print("No trades for 2025, but that matches earlier results? (Checked: 2025 had trades)")
    else:
        print(f"Trades generated: {len(df)}")
        years_found = pd.to_datetime(df['Date']).dt.year.unique()
        print(f"Years found in result: {years_found}")
        
        if len(years_found) == 1 and years_found[0] == 2025:
            print("SUCCESS: Only 2025 data processed.")
        else:
            print(f"FAILURE: Found years {years_found}")

if __name__ == "__main__":
    verify()
