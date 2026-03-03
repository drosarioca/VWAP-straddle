
from datetime import date
from backtest_main import construct_straddle
import pandas as pd

def test_load():
    target_date = date(2025, 9, 9)
    strike = 24850
    print(f"Attempting to load: {target_date} Strike {strike}...")
    
    try:
        df = construct_straddle(target_date, strike)
        if df is not None and not df.empty:
            print("[OK] SUCCESS: Dataframe loaded correctly!")
            print(df.head())
            print("Columns:", df.columns)
            # Check if datetime index is correct
            print("Index:", df.index)
        else:
            print("[X] FAILED: Returned None or Empty")
    except Exception as e:
        print(f"[X] CRASH: {e}")

if __name__ == "__main__":
    test_load()
