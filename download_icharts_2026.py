
import requests
import pandas as pd
import os
import time
import json
from datetime import datetime, date, timedelta

# --- CONFIG ---
DOWNLOAD_DIR = "icharts_download"
COOKIE_FILE = "cookie.txt"
INDEX_DATA_DIR = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
BASE_URL = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"
USER = "arung"

# Targeted Expiries will be parsed from HTML
TARGET_MONTHS = ["JAN26", "FEB26", "02MAR26"]

STRIKE_RANGE = 1000 # +/- points around ATM

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def load_sid():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            c = f.read().strip()
            return c.replace("PHPSESSID=", "")
    return None

def get_atm_for_date(target_date):
    """
    Tries to find NIFTY ATM strike from index data.
    """
    fname = f"NIFTY-1minute-data-{target_date.strftime('%Y-%m-%d')}.csv"
    fpath = os.path.join(INDEX_DATA_DIR, fname)
    
    if os.path.exists(fpath):
        try:
            df = pd.read_csv(fpath)
            df.columns = [c.strip().lower() for c in df.columns]
            # Use 9:16 open or first available
            if 'open' in df.columns:
                spot = df.iloc[0]['open']
                return round(spot / 50) * 50
        except:
            pass
    
    # Baseline fallback if index data is missing
    print(f"Warning: Index data missing for {target_date}. Using baseline 24000.")
    return 24000

def get_expiries_from_html():
    from bs4 import BeautifulSoup
    path = "icharts_source.html"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
        soup = BeautifulSoup(html, 'html.parser')
        select = soup.find('select', {'id': 'optExpDate_hist'})
        if not select: return []
        return [opt.get('value').strip() for opt in select.find_all('option') if opt.get('value')]

def download_and_format(sid, expiry_date, strike):
    exp_code = expiry_date.strftime("%d%b%y").upper()
    # Symbol: NIFTY-{strike}C-{expiry}:NIFTY-{strike}P-{expiry}
    symbol = f"NIFTY-{strike}C-{exp_code}:NIFTY-{strike}P-{exp_code}"
    
    # Filename: NIFTY-YYYY-MM-DD-DDMMMYY-STRIKE-straddle-data.csv
    filename = f"NIFTY-{expiry_date.strftime('%Y-%m-%d')}-{exp_code}-{strike}-straddle-data.csv"
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    
    if os.path.exists(filepath):
        # print(f"  {filename} exists. Skipping.")
        return True, "Exists"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php',
        'Cookie': f"PHPSESSID={sid}"
    }
    
    params = {
        'symbol': symbol,
        'resolution': '1',
        'from': expiry_date.strftime("%Y-%m-%d"),
        'to': expiry_date.strftime("%Y-%m-%d"),
        'u': USER,
        'sid': sid, # Pass confirmed sid
        'mode': 'INTRA',
        'DataRequest': '2',
        'firstDataRequest': 'true',
        'countback': '3000'
    }
    
    try:
        resp = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception as je:
                print(f"  Strike {strike}: JSON Error - Response: {resp.text[:200]}...")
                return False, f"JSON Decode Error: {je}"
                
            if 's' in data and data['s'] == 'ok' and 't' in data:
                df = pd.DataFrame({
                    'timestamp': data['t'],
                    'LTP': data['c'],
                    'volume': data.get('v', [0]*len(data['t']))
                })
                # Convert to IST
                df['dt_obj'] = pd.to_datetime(df['timestamp'], unit='s') + timedelta(minutes=330)
                df['date'] = df['dt_obj'].dt.strftime('%Y-%m-%d')
                df['time'] = df['dt_obj'].dt.strftime('%H:%M:%S')
                
                # Calculate VWAP
                df['vwap'] = (df['LTP'] * df['volume']).cumsum() / df['volume'].cumsum()
                # SD (Rolling) - matches 'earlier format' where it starts from 2nd candle
                df['sd'] = df['LTP'].expanding().std()
                
                # Save only required columns
                final_df = df[['date', 'time', 'LTP', 'volume', 'vwap', 'sd']]
                final_df.to_csv(filepath, index=False)
                return True, f"Saved {len(df)} rows"
            else:
                return False, f"No Data ({data.get('s', 'unknown')})"
        return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    sid = load_sid()
    if not sid:
        print("Error: No SID found in cookie.txt")
        return

    all_expiries = get_expiries_from_html()
    target_expCodes = [e for e in all_expiries if any(m in e for m in TARGET_MONTHS)]
    
    print(f"Found {len(target_expCodes)} target expiries: {target_expCodes}")
    
    for exp_code in target_expCodes:
        try:
            exp_date = datetime.strptime(exp_code, "%d%b%y").date()
        except:
            print(f"Error parsing expiry code: {exp_code}")
            continue
            
        atm = get_atm_for_date(exp_date)
        print(f"\nProcessing Expiry: {exp_code} | ATM: {atm}")
        
        strikes = range(atm - STRIKE_RANGE, atm + STRIKE_RANGE + 50, 50)
        
        success_count = 0
        for s in strikes:
            ok, msg = download_and_format(sid, exp_date, s)
            if ok:
                if msg != "Exists": success_count += 1
                print(f"  Strike {s}: OK {msg}", end='\r')
            else:
                print(f"  Strike {s}: FAILED - {msg}")
            
            if msg != "Exists":
                time.sleep(1.0) # Rate limit
                
        print(f"\nCompleted {exp_date}. Downloaded {success_count} files.")

if __name__ == "__main__":
    main()
