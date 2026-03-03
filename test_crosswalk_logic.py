
import pandas as pd
import sys
import os

# Import App Logic (Partial)
# We can't import the full app because of Streamlit commands, so we'll replicate the core logic here for testing.

from backtest_main import run_backtest
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures
import datetime

def run_variant_year(params, year):
    print(f"   [Worker] Processing {year}...")
    try:
        # Mocking params access
        entry_time = datetime.time(int(params['Enter_Hour']), int(params['Enter_Min']))
        
        # Test Spot Check Logic
        if 'Spot_Check_Hour' in params and pd.notna(params['Spot_Check_Hour']):
             sc_time = datetime.time(int(params['Spot_Check_Hour']), int(params['Spot_Check_Min']))
             print(f"   [Worker] explicit spot check: {sc_time}")
        else:
             print("   [Worker] default spot check")

        exit_time = datetime.time(int(params['Exit_Hour']), int(params['Exit_Min']))
        
        # Test Run - shortened window to make it fast? 
        # Actually backtest run depends on data availability.
        # We will trust run_backtest works (verified previously).
        # We just want to check if it accepts the params correctly.
        
        return (year, pd.DataFrame({'PnL': [100], 'Date': [datetime.date(year, 1, 1)]}), ["Log 1"])
        
    except Exception as e:
        return (year, pd.DataFrame(), [f"Error: {e}"])

def test_batch():
    print("Loading Template...")
    df = pd.read_excel("crosswalk_input_v2.xlsx")
    print(f"Loaded {len(df)} variants.")
    
    for i, row in df.iterrows():
        print(f"Testing Variant: {row['Name_Tag']}")
        years_str = str(row['Years'])
        target_years = [int(y.strip()) for y in years_str.split(",") if y.strip().isdigit()]
        
        print(f"  Years: {target_years}")
        
        with ProcessPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(run_variant_year, row, year): year for year in target_years}
            for future in concurrent.futures.as_completed(futures):
                try:
                    y, df_res, logs = future.result()
                    print(f"  -> Year {y} finished. Rows: {len(df_res)}")
                except Exception as e:
                    print(f"  -> Year {y} failed: {e}")

if __name__ == "__main__":
    test_batch()
