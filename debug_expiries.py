
import os
import pandas as pd
from datetime import datetime

DATA_DIR = r"c:\Users\Rosario\.gemini\antigravity\scratch\quant_trading\icharts_download"

def analyze_expiries():
    print(f"Scanning {DATA_DIR}...")
    files = os.listdir(DATA_DIR)
    
    expiries = set()
    for f in files:
        if f.startswith("NIFTY_") and f.endswith("_Straddle.csv"):
            try:
                # NIFTY_02DEC25_26950_Straddle.csv
                parts = f.split("_")
                exp_str = parts[1]
                exp_date = datetime.strptime(exp_str, "%d%b%y").date()
                expiries.add(exp_date)
            except:
                pass
                
    sorted_exps = sorted(list(expiries))
    print(f"Found {len(sorted_exps)} unique expiries.")
    
    print("\n--- Non-Thursday Expiries ---")
    non_thurs = 0
    for e in sorted_exps:
        if e.weekday() != 3: # 3 = Thursday
            print(f"{e} ({e.strftime('%A')})")
            non_thurs += 1
            
    print(f"\nTotal Non-Thursday Expiries: {non_thurs}")
    
    print("\n--- Sample Prices from a Non-Thursday ---")
    # Let's peek at one if exists
    for e in sorted_exps:
        if e.weekday() != 3:
            # Find a file for this expiry
            pat = e.strftime("%d%b%y").upper()
            target_f = next((f for f in files if pat in f), None)
            if target_f:
                fp = os.path.join(DATA_DIR, target_f)
                df = pd.read_csv(fp)
                # Check price at 09:30
                # Parsing
                # 2024-01-01 09:15:00
                if 'datetime' in df.columns:
                     sample = df.tail(5)
                     print(f"File: {target_f}")
                     print(sample[['datetime', 'close']].to_string())
                     break

if __name__ == "__main__":
    analyze_expiries()
