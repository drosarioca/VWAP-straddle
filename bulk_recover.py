
import json
import time
import datetime
import os
from backtest_main import IChartsDataManager, ICHARTS_DIR
from download_icharts import download_straddle

def bulk_recover():
    if not os.path.exists("missing_data_report.json"):
        print("No 'missing_data_report.json' found. Run audit first.")
        return

    with open("missing_data_report.json", "r") as f:
        missing_items = json.load(f)
        
    print(f"--- Starting Bulk Recovery for {len(missing_items)} items ---")
    
    # Initialize Loader to find expiries
    loader = IChartsDataManager(ICHARTS_DIR)
    
    success_count = 0
    fail_count = 0
    
    # Deduplicate logic again just in case
    # Format in JSON is list of dicts.
    # We process each unique (Date, Strike).
    
    processed = set()
    
    for item in missing_items:
        date_str = item['Date']
        strike = item['Strike']
        
        if (date_str, strike) in processed:
            continue
        processed.add((date_str, strike))
        
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Resolve Expiry
        expiry_date = loader.get_nearest_expiry(target_date)
        if not expiry_date:
            print(f" [X] No Expiry found for {target_date}, skipping strike {strike}")
            fail_count += 1
            continue
            
        expiry_code = expiry_date.strftime("%d%b%y").upper()
        
        print(f"Recovering {strike} for {expiry_code} (Date: {target_date})...")
        
        # Call Download
        # Need timestamp for from/to
        # Use target_date - 3 to target_date + 3
        dt_from = datetime.datetime.combine(target_date - datetime.timedelta(days=3), datetime.time(9,0))
        dt_to = datetime.datetime.combine(target_date + datetime.timedelta(days=3), datetime.time(15,30))
        
        ts_from = int(dt_from.timestamp())
        ts_to = int(dt_to.timestamp())
        
        try:
            res = download_straddle(strike, expiry_code, ts_from, ts_to)
            if res:
                print(f"  [OK] Success.")
                success_count += 1
            else:
                print(f"  [FAIL] Failed (API returned False).")
                fail_count += 1
        except Exception as e:
            print(f"  [ERROR] Error: {e}")
            fail_count += 1
            
        # Courtesy delay
        time.sleep(1.5) 
        
    print("\n--- Recovery Complete ---")
    print(f"Success: {success_count}, Failed: {fail_count}")
    if fail_count > 0:
        print("Tip: If failures persist, check your cookie/session validity.")

if __name__ == "__main__":
    bulk_recover()
