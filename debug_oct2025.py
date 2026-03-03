
import os
import sys
from datetime import datetime, date
import pandas as pd

# Mocking the path setup
sys.path.append(os.getcwd())
try:
    from backtest_main import IChartsDataManager, INDEX_DATA_PATH, ICHARTS_DIR
except ImportError:
    # Fallback if import fails (e.g. strict relative imports)
    pass

# Hardcode paths if import fails
if 'INDEX_DATA_PATH' not in locals():
    INDEX_DATA_PATH = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
    ICHARTS_DIR = os.path.join(os.getcwd(), 'icharts_download')

def check_oct_2025():
    print("--- Checking October 2025 ---")
    
    # 1. Initialize Loader
    loader = IChartsDataManager(ICHARTS_DIR)
    print(f"Loaded {len(loader.available_expiries)} expiries.")
    
    # Check specific expiries
    oct_expiries = [e for e in loader.sorted_expiries if e.month == 10 and e.year == 2025]
    print(f"Oct 2025 Expiries found in Straddle Data: {oct_expiries}")
    
    # 2. Check Index Data for Oct 2025
    if not os.path.exists(INDEX_DATA_PATH):
        print(f"Index Path not found: {INDEX_DATA_PATH}")
        return

    spot_files = sorted([f for f in os.listdir(INDEX_DATA_PATH) if "2025-10-" in f])
    print(f"Found {len(spot_files)} Spot Files for Oct 2025.")
    
    # 3. Simulate Backtest Date Loop
    print("\n--- Simulating Date Matching ---")
    
    target_dates = [
        date(2025, 10, 7),  # Tuesday
        date(2025, 10, 14), # Tuesday
        date(2025, 10, 20), # Monday
        date(2025, 10, 28)  # Tuesday
    ]
    
    for d in target_dates:
        print(f"\nTarget Date: {d}")
        
        # Check if Spot file exists
        fname = f"NIFTY-1minute-data-{d}.csv"
        if fname in spot_files:
            print(f"[OK] Spot File Exists: {fname}")
        else:
            print(f"[MISSING] Spot File Missing: {fname}")
            
        # Check Nearest Expiry
        nearest = loader.get_nearest_expiry(d)
        print(f"Nearest Expiry returned: {nearest}")
        
        if nearest:
            dte = (nearest - d).days
            print(f"Calculated DTE: {dte}")
            
            if dte == 0:
                print("[OK] STATUS: MATCH (0DTE)")
            else:
                print(f"[FAIL] STATUS: MISMATCH (DTE={dte})")
        else:
             print("[FAIL] STATUS: NO EXPIRY FOUND")

if __name__ == "__main__":
    # class MockLoader to avoid full import issues if needed
    class IChartsDataManager:
        def __init__(self, data_dir):
            self.data_dir = data_dir
            self.available_expiries = set()
            self._scan_files()
            
        def _scan_files(self):
            print(f"Scanning {self.data_dir}...")
            for fname in os.listdir(self.data_dir):
                if fname.endswith("_Straddle.csv") and fname.startswith("NIFTY_"):
                    try:
                        parts = fname.split("_")
                        expiry_str = parts[1] # 07OCT25
                        expiry_date = datetime.strptime(expiry_str, "%d%b%y").date()
                        # Removed Tuesday check as per latest code
                        self.available_expiries.add(expiry_date)
                    except: pass
            self.sorted_expiries = sorted(list(self.available_expiries))

        def get_nearest_expiry(self, target_date):
            for exp in self.sorted_expiries:
                if exp >= target_date:
                    return exp
            return None

    check_oct_2025()
