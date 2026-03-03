
import os
import pandas as pd
from datetime import datetime, time, date

# MOCK CONFIG
INDEX_DATA_PATH = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
ICHARTS_DIR = r"c:\Users\Rosario\.gemini\antigravity\scratch\quant_trading\icharts_download"

def get_nearest_expiry(target_date, data_years=[2024, 2025]):
    # Simplified mock of IChartsDataManager.get_nearest_expiry
    # We just want to see if we find a file for the date itself
    # Since these ARE expiry dates, we expect nearest_expiry == target_date
    return target_date

def check_dates():
    dates_to_check = [
        date(2025, 4, 9),
        date(2025, 9, 2)
    ]
    
    print("--- DEBUGGING MISSING DATES ---")
    
    for d in dates_to_check:
        print(f"\nTarget Date: {d}")
        
        # 1. Load Spot Data
        spot_file = os.path.join(INDEX_DATA_PATH, f"NIFTY-1minute-data-{d}.csv")
        if not os.path.exists(spot_file):
            print(f"[FAIL] Spot file missing: {spot_file}")
            continue
            
        try:
            df = pd.read_csv(spot_file)
            # Simulate backtester ATM selection at 09:34 (min_entry_time) 
            # OR start of day?
            # Backtester uses:
            # atm_strike = round(spot_price / 50) * 50
            # BUT at what time? 
            # run_day_analysis -> iterates candles.
            # It loads the straddle file *before* iterating?
            # No, backtest_main.py: construct_straddle(d, atm_strike)
            # is called *inside* the loop or before? 
            
            # Actually, `run_day_analysis` calculates ATM at `min_entry_time` (09:34)
            # AND it loads a specific strike.
            
            # Let's check price at 09:20 (commonly used for 'selection' in my verify script)
            # vs 09:30 vs 09:34.
            
            time_cols = ['09:15:00', '09:20:00', '09:30:00', '09:34:00']
            
            print(f"Spot Prices:")
            rows = df[df['time'].isin(time_cols)]
            for _, row in rows.iterrows():
                t = row['time']
                p = row['close']
                s = round(p / 50) * 50
                print(f"  {t} : {p} -> ATM {s}")
                
            # Simulate Trade Logic (Simplified)
            # Group A: 9:15-9:29 (first 3 candles of 5min? No, strategy uses 1-min aggregated?)
            # Strategy: 
            # 1. Wait for candle close > 09:30
            # 2. Check Min Low of previous candles
            
            print("  --- Logic Check ---")
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
            df.set_index('datetime', inplace=True)
            
            # 5-min resampling (approximate)
            df_5m = df['close'].resample('5min').ohlc()
            
            # Setup: 9:15, 9:20, 9:25
            setup_candles = df_5m.between_time('09:15', '09:29')
            if len(setup_candles) >= 3:
                ref_low = setup_candles['low'].min()
                print(f"    Ref Low (Group A): {ref_low}")
                
                # Check Entry Candles (09:30+)
                entry_candles = df_5m.between_time('09:30', '09:50')
                triggered = False
                for t, row in entry_candles.iterrows():
                    close = row['close']
                    if close < ref_low:
                        print(f"    [MATCH] {t.time()} Close {close} < Ref {ref_low} -> ENTRY SIGNAL")
                        triggered = True
                        break
                    else:
                        print(f"    [WAIT] {t.time()} Close {close} >= Ref {ref_low}")
                
                if not triggered:
                    print("    [RESULT] No Entry Triggered (Consolidation/Gap Up)")
            else:
                print("    [FAIL] Not enough setup candles")

        except Exception as e:
            print(f"Error reading spot: {e}")

if __name__ == "__main__":
    check_dates()
