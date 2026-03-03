
import time
from datetime import datetime, timedelta
# Import the actual downloader function
# We must ensure download_icharts.py is present (it is)
from download_icharts import download_straddle

def recover_data():
    print("--- Recovering Missing Oct 2025 Data ---")
    
    tasks = [
        ("09APR25", 22400),
        ("02SEP25", 24700)
    ]
    
    for expiry_code, strike in tasks:
        # Calculate start/end date for request
        exp_date = datetime.strptime(expiry_code, "%d%b%y")
        start_date = exp_date - timedelta(days=7)
        
        s_date_str = start_date.strftime("%Y-%m-%d")
        e_date_str = exp_date.strftime("%Y-%m-%d")
        
        print(f"Downloading {expiry_code} : {strike} ...")
        success = download_straddle(strike, expiry_code, s_date_str, e_date_str)
        
        if success:
            print("[OK] Success")
        else:
            print("[X] Failed")
            
        time.sleep(2) # Politeness delay

if __name__ == "__main__":
    recover_data()
