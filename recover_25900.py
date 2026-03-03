
from download_icharts import download_straddle, HEADERS, USER, SID
import datetime

def recover_data():
    expiry = "28OCT25"
    strike = 25900
    
    # Range: A few days before and after 28th to ensure data
    d_from = "2025-10-25" 
    d_to = "2025-10-29"
    
    # Convert to timestamps/format expected by iCharts?
    # download_straddle expects standard int timestamps usually? 
    # Let's check download_icharts implementation logic in detail if needed.
    # Ah, lines 86-87 pass directly 'from' and 'to'.
    # Usually these API expect UNIX timestamps.
    
    # Re-reading download_icharts: it uses `from` and `to`. 
    # Let's convert to UNIX timestamp just to be safe as that's standard for TVs.
    
    dt_from = datetime.datetime.strptime(d_from, "%Y-%m-%d")
    ts_from = int(dt_from.timestamp())
    
    dt_to = datetime.datetime.strptime(d_to, "%Y-%m-%d")
    ts_to = int(dt_to.timestamp())
    
    print(f"Attempting to recover 25900 for {expiry}...")
    
    success = download_straddle(strike, expiry, ts_from, ts_to)
    
    if success:
        print("Successfully downloaded 25900!")
    else:
        print("Download returned False (maybe file exists or failed).")

if __name__ == "__main__":
    recover_data()
