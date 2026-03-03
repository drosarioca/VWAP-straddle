
import requests
import pandas as pd
import os
import time
import re
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Global Config
SID = "9t9743jovml17qfhjc09p1lid4" # Updated from capture
USER = "arung"
BASE_URL = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"
OUTPUT_DIR = "icharts_download"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

import json
HEADERS = {}

# 1. Check for Manual Cookie (Highest Priority)
if os.path.exists("cookie.txt"):
    with open("cookie.txt", "r") as f:
        cookie_str = f.read().strip()
        if cookie_str and "PHPSESSID" in cookie_str:
            HEADERS['Cookie'] = cookie_str
            # Default headers if missing
            HEADERS['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            HEADERS['Referer'] = 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php'
            print(f"Loaded Manual Cookie from 'cookie.txt'")

# 2. Check for Captured Headers (Fallback)
elif os.path.exists("icharts_headers.json"):
    with open("icharts_headers.json", "r") as f:
        HEADERS = json.load(f)
    print("Loaded headers from icharts_headers.json")
else:
    print("Warning: No headers/cookies found. Using minimal default.")

def get_expiries_from_html():
    """
    Parses 'icharts_source.html' to get the list of valid expiry codes.
    Returns list of strings e.g. ['27JAN26', '31DEC30']
    """
    if not os.path.exists("icharts_source.html"):
        print("Error: icharts_source.html not found.")
        return []
    
    with open("icharts_source.html", "r", encoding="utf-8") as f:
        try:
            html = f.read()
            soup = BeautifulSoup(html, 'html.parser')
            select = soup.find('select', {'id': 'optExpDate_hist'})
            
            expiries = []
            if select:
                options = select.find_all('option')
                for opt in options:
                    val = opt.get('value').strip()
                    if val:
                        expiries.append(val)
            return expiries
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            return []

def download_straddle(strike, expiry_code, date_from, date_to):
    """
    Downloads straddle data for specific parameters.
    """
    # Symbol Format: NIFTY-25050C-03FEB26:NIFTY-25050P-03FEB26
    symbol = f"NIFTY-{strike}C-{expiry_code}:NIFTY-{strike}P-{expiry_code}"
    
    filename = f"NIFTY_{expiry_code}_{strike}_Straddle.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if os.path.exists(filepath):
        # print(f"Skipping {filename} (Already exists)")
        return False

    params = {
        'symbol': symbol,
        'resolution': '1',
        'from': date_from,
        'to': date_to, # iCharts seems to buffer around this
        'u': USER,
        'sid': SID,
        'q1': '1',
        'q2': '1',
        'mode': 'INTRA',
        'DataRequest': '2',
        'firstDataRequest': 'true',
        'countback': '3000' # Try to get max
    }
    
    # Use captured headers if available, else default
    req_headers = HEADERS.copy() if HEADERS else {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # Inject Cookie if missing
    if 'Cookie' not in req_headers and SID:
        req_headers['Cookie'] = f"PHPSESSID={SID}"
    
    try:
        # print(f"Downloading {symbol}...") # Reduce noise
        resp = requests.get(BASE_URL, params=params, headers=req_headers, timeout=10)
        
        if resp.status_code != 200:
            print(f"Failed: HTTP {resp.status_code}", flush=True)
            return False
            
        try:
            data = resp.json()
        except Exception:
             # Likely HTML/Invalid Session
             print(f"Error: Invalid JSON response (Session invalid?) for {symbol}", flush=True)
             return False

        if 's' in data and data['s'] == 'no_data':
            print("No Data.", flush=True)
            return False
            
        if 't' in data and len(data['t']) > 0:
            # Save to CSV
            df = pd.DataFrame({
                'timestamp': data['t'],
                'open': data['o'],
                'high': data['h'],
                'low': data['l'],
                'close': data['c'],
                'volume': data['v'] if 'v' in data else 0
            })
            
            # timestamp is unix
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s') + timedelta(minutes=330) # UTC to IST (5.30)
            # Actually, check if source is UTC or IST. Typically TradingView feeds are seconds. 
            # The timestamp 1769938000 is likely UTC. 
            
            filename = f"NIFTY_{expiry_code}_{strike}_Straddle.csv"
            filepath = os.path.join(OUTPUT_DIR, filename)
            df.to_csv(filepath, index=False)
            print(f"Saved {len(df)} rows to {filename}")
            return True
            
    except Exception as e:
        print(f"Error: {e}")
        
    return False

def main():
    print("--- iCharts Bulk Downloader ---")
    print(f"Using Session ID: {SID}")
    
    expiries = get_expiries_from_html()
    print(f"Found {len(expiries)} expiries.")
    
    # Filter 2024 and 2025 Expiries (Strict Suffix Check)
    target_expiries = [e for e in expiries if e.endswith("24") or e.endswith("25")]
    # Sort Chronologically (Jan 2024 -> Dec 2025)
    target_expiries.sort(key=lambda x: datetime.strptime(x, "%d%b%y"))
    
    print(f"Targeting {len(target_expiries)} expiries in 2024-2025 (Chronological Order).")
    
    # Expanded Strike Range
    strikes = range(20000, 27000, 50) 
    print(f"Scanning {len(strikes)} strikes per expiry (skipping 100s).")
    
    count = 0
    for expiry in target_expiries:
        try:
            exp_date = datetime.strptime(expiry, "%d%b%y")
            start_date = exp_date - timedelta(days=7) 
            
            s_date_str = start_date.strftime("%Y-%m-%d")
            e_date_str = exp_date.strftime("%Y-%m-%d")
            
            print(f"\nProcessing Expiry: {expiry} ({s_date_str} to {e_date_str})")
            
            for k in strikes:
                # OPTIMIZATION: Skip 100-point strikes (keep only 50s: 20050, 20150...)
                if k % 100 == 0:
                    continue

                success = download_straddle(k, expiry, s_date_str, e_date_str)
                if success:
                    count += 1
                
                # Randomized Delay to avoid detection (1.5s to 3.5s)
                delay = random.uniform(1.5, 3.5)
                time.sleep(delay)
                
        except Exception as e:
            print(f"Skipping expiry {expiry}: {e}")
            
    print(f"Download Complete. Saved {count} files.")

if __name__ == "__main__":
    main()
