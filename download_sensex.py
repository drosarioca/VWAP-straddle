
import pandas as pd
import requests
import os
import datetime
import time
import glob

# --- CONFIG ---
INDEX_DIR = "sensex_index_data"
OUTPUT_DIR = "sensex_straddle_download"
COOKIE_FILE = "cookie.txt"
START_DATE = datetime.date(2024, 7, 1)
END_DATE = datetime.date(2026, 2, 28)

BASE_URL = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"
SID_DEFAULT = "9t9743jovml17qfhjc09p1lid4" 
USER = "arung"

# Logic for Rolling
STRIKE_INTERVAL = 100
STRIKES_UP = 20
STRIKES_DOWN = 20

# Symbol Formats to Try (Priority Order)
SYMBOL_TEMPLATES = [
    "SENSEX-{strike}C-{expiry}:SENSEX-{strike}P-{expiry}",
    "BSE-SENSEX-{strike}C-{expiry}:BSE-SENSEX-{strike}P-{expiry}",
    "BSX-{strike}C-{expiry}:BSX-{strike}P-{expiry}",
    "SENSEX50-{strike}C-{expiry}:SENSEX50-{strike}P-{expiry}"
]

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def load_cookie_and_sid():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            c = f.read().strip()
            # Extract SID
            if "PHPSESSID=" in c:
                sid = c.replace("PHPSESSID=", "").strip()
                cookie = c
            else:
                sid = c
                cookie = f"PHPSESSID={c}"
            return cookie, sid
    return f"PHPSESSID={SID_DEFAULT}", SID_DEFAULT

def load_index_data():
    print(f"Loading Index Data from {INDEX_DIR}...")
    files = glob.glob(os.path.join(INDEX_DIR, "*.csv"))
    if not files:
        print("No index files found.")
        return {}
    
    price_map = {}
    
    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = [c.strip().lower() for c in df.columns]
            
            if 'date' in df.columns and 'time' in df.columns:
                df['dt'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
            elif 'datetime' in df.columns:
                df['dt'] = pd.to_datetime(df['datetime'])
            else:
                continue
                
            df['day'] = df['dt'].dt.date
            
            daily_groups = df.groupby('day')
            for day, group in daily_groups:
                if isinstance(day, str):
                     day = datetime.datetime.strptime(day, "%Y-%m-%d").date()
                     
                if day < START_DATE or day > END_DATE: continue
                
                group = group.sort_values('dt')
                if group.empty: continue
                
                spot = group.iloc[0]['open'] # Open of first candle
                price_map[day] = spot
                
        except Exception as e:
            pass
            
    print(f"Loaded {len(price_map)} trading days from Index Data.")
    return price_map

def download_specific_file(symbol, target_date, cookie, sid, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        # Optimization: Don't re-download if exists
        return True, "Exists"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php',
        'X-Requested-With': 'XMLHttpRequest',
        'Cookie': cookie
    }
    
    params = {
        'symbol': symbol,
        'resolution': '1',
        'from': target_date.strftime("%Y-%m-%d"),
        'to': target_date.strftime("%Y-%m-%d"),
        'u': USER,
        'sid': sid,
        'mode': 'INTRA',
        'DataRequest': '2',
        'firstDataRequest': 'true',
        'countback': '375'
    }
    
    try:
        resp = requests.get(BASE_URL, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if 's' in data and data['s'] == 'ok':
                if 't' not in data or len(data['t']) < 5:
                     return False, "Empty"
                     
                df = pd.DataFrame({
                    'timestamp': data['t'],
                    'open': data['o'],
                    'high': data['h'],
                    'low': data['l'],
                    'close': data['c'],
                    'volume': data.get('v', [])
                })
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='s') + datetime.timedelta(minutes=330)
                
                df.to_csv(filepath, index=False)
                return True, f"Downloaded ({len(df)} rows)"
            elif resp.status_code == 403:
                return False, "403"
    except:
        pass
    return False, "Fail"

def process_date(target_date, spot_price, cookie, sid):
    # 1. Determine ATM
    atm_strike = round(spot_price / STRIKE_INTERVAL) * STRIKE_INTERVAL
    expiry_str = target_date.strftime("%d%b%y").upper()
    
    # 2. Check if this is a valid expiry by testing ATM first
    # This prevents looping 40 times for non-expiry days
    fname_atm = f"SENSEX_{expiry_str}_{atm_strike}_Straddle.csv"
    valid_template = None
    
    print(f"Checking Expiry {target_date} ({expiry_str}) | ATM {atm_strike}...", end="", flush=True)
    
    # Try finding working template on ATM
    for tmpl in SYMBOL_TEMPLATES:
        sym = tmpl.format(strike=atm_strike, expiry=expiry_str)
        success, msg = download_specific_file(sym, target_date, cookie, sid, fname_atm)
        if success:
            valid_template = tmpl
            print(f" [CONFIRMED] {msg}")
            break
        if msg == "403":
            print(" [403 ERROR]")
            return # Critical failure
            
    if not valid_template:
        print(" [No Data/Not Expiry]")
        return # Not an expiry, skip
        
    # 3. Download Range
    print(f"  Downloading +/- {STRIKES_UP} strikes for {target_date}...")
    
    # Range: from (ATM - 20*100) to (ATM + 20*100)
    start_strike = atm_strike - (STRIKES_DOWN * STRIKE_INTERVAL)
    end_strike = atm_strike + (STRIKES_UP * STRIKE_INTERVAL)
    
    download_count = 0
    
    for s in range(start_strike, end_strike + STRIKE_INTERVAL, STRIKE_INTERVAL):
        if s == atm_strike: continue # Already done
        
        sym = valid_template.format(strike=s, expiry=expiry_str)
        fname = f"SENSEX_{expiry_str}_{s}_Straddle.csv"
        
        success, msg = download_specific_file(sym, target_date, cookie, sid, fname)
        if success:
            download_count += 1
            # print(f"    {s}: OK", end="\r")
        # Sliently skip failures for OTMs if they don't exist
        
    print(f"  Completed {target_date}: {download_count + 1} files total.")

def main():
    cookie, sid = load_cookie_and_sid()
    index_map = load_index_data()
    
    if not index_map:
        return

    sorted_dates = sorted(index_map.keys())
    print(f"Starting Bulk Download (Deep Scan) | SID: {sid}")
    
    for d in sorted_dates:
        process_date(d, index_map[d], cookie, sid)

if __name__ == "__main__":
    main()
