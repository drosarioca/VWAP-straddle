
import requests
import json
import os
import pandas as pd
from datetime import datetime, timedelta, date

# --- CONFIGURATION ---
TOKEN_FILE = "zerodha_token.txt"
# Target path from backtest_main.py
OUTPUT_DIR = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
INSTRUMENT_TOKEN = "256265" # NIFTY 50

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def load_enctoken():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r") as f:
        return f.read().strip()

def download_day(token, target_date):
    """
    Downloads 1-min data for a specific date.
    Zerodha historical API expects 'from' and 'to' params.
    """
    url = f"https://kite.zerodha.com/oms/instruments/historical/{INSTRUMENT_TOKEN}/minute"
    
    # Zerodha API usually allows chunks of 60 days for 'minute' resolution
    # but here we download day-by-day to match the backtester's file structure.
    from_str = target_date.strftime("%Y-%m-%d") + " 09:15:00"
    to_str = target_date.strftime("%Y-%m-%d") + " 15:30:00"
    
    headers = {
        "Authorization": f"enctoken {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    params = {
        "from": from_str,
        "to": to_str
    }
    
    print(f"Downloading {target_date}...", end=" ", flush=True)
    resp = requests.get(url, params=params, headers=headers)
    
    if resp.status_code != 200:
        print(f"Failed (Status {resp.status_code})")
        print(f"Response: {resp.text}")
        return False
        
    try:
        data = resp.json()
        if data['status'] != 'success':
            print(f"Error: {data.get('message', 'Unknown error')}")
            return False
            
        candles = data['data']['candles']
        if not candles:
            print("No data received.")
            return False
            
        # Format: timestamp, open, high, low, close, volume, oi
        # Target Format: date,time,open,high,low,close
        formatted_rows = []
        for c in candles:
            # Zerodha timestamp format: "2024-01-01T09:15:00+0530"
            dt_raw = c[0]
            dt = datetime.strptime(dt_raw, "%Y-%m-%dT%H:%M:%S%z")
            
            formatted_rows.append({
                'date': dt.strftime("%Y-%m-%d"),
                'time': dt.strftime("%H:%M:%S"),
                'open': c[1],
                'high': c[2],
                'low': c[3],
                'close': c[4]
            })
            
        df = pd.DataFrame(formatted_rows)
        # NIFTY-1minute-data-2026-01-01.csv
        out_name = f"NIFTY-1minute-data-{target_date.strftime('%Y-%m-%d')}.csv"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        df.to_csv(out_path, index=False)
        print(f"Saved {len(df)} rows to {out_name}")
        return True
        
    except Exception as e:
        print(f"Exception: {e}")
        return False

def main():
    token = load_enctoken()
    if not token:
        print(f"Error: Please paste your enctoken into '{TOKEN_FILE}'")
        return

    # Target Dates: Jan 2026 to March 02, 2026
    start_date = date(2026, 1, 1)
    end_date = date(2026, 3, 2)
    
    curr = start_date
    while curr <= end_date:
        # Skip weekends (Sat=5, Sun=6)
        if curr.weekday() < 5:
            download_day(token, curr)
        curr += timedelta(days=1)

if __name__ == "__main__":
    main()
