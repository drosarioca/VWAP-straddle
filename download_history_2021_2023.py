
import os
import requests
import pandas as pd
from datetime import date, timedelta, datetime
import time
import glob

# Configuration
COOKIE_FILE = "cookie.txt"
INDEX_DATA_DIR = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
DOWNLOAD_DIR = "icharts_download"
START_YEAR = 2021
END_YEAR = 2023

# iCharts API (Proven endpoint from download_icharts.py)
BASE_URL = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"
# Headers (will be populated with cookie)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php',
    'X-Requested-With': 'XMLHttpRequest'
}

def load_cookie():
    if not os.path.exists(COOKIE_FILE):
        print(f"Error: {COOKIE_FILE} not found!", flush=True)
        return None
    with open(COOKIE_FILE, "r") as f:
        content = f.read().strip()
        # Clean up if user pasted "PHPSESSID=..."
        return content.replace("PHPSESSID=", "")

def get_atm_from_file(file_path):
    try:
        df = pd.read_csv(file_path)
        # Just take the first row 'Open' as the opening ATM reference.
        df.columns = [c.lower() for c in df.columns]
        if 'open' in df.columns:
            open_price = df['open'].iloc[0]
            return round(open_price / 50) * 50
        elif 'close' in df.columns:
             # Fallback
            return round(df['close'].iloc[0] / 50) * 50
    except Exception as e:
        print(f"Error reading {file_path}: {e}", flush=True)
        return None
    return None

def download_straddle(session_id, symbol_name, expiry_date, strike_price):
    # Construct Symbol: NIFTY-{strike}C-{expiry_code}:NIFTY-{strike}P-{expiry_code}
    # Expiry Code Format: DDMMMYY (e.g., 07JAN21)
    expiry_code = expiry_date.strftime("%d%b%y").upper()
    
    # Combined Symbol for Straddle
    symbol = f"NIFTY-{strike_price}C-{expiry_code}:NIFTY-{strike_price}P-{expiry_code}"
    
    filename = f"NIFTY_{expiry_code}_{strike_price}_Straddle.csv"
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    
    if os.path.exists(filepath):
        if os.path.getsize(filepath) > 500: # Valid size check
            return "Skipped (Exists)"
    
    # Date Range: Fetch ~7 days leading up to expiry to capture the "week"
    # Actually, recovery_download.py uses: start = exp - 7 days.
    # Timestamps are UNIX.
    
    to_date = expiry_date
    from_date = expiry_date - timedelta(days=10) # Safe buffer
    
    # API expects UNIX timestamps for `from`/`to` in this specific endpoint?
    # Wait, download_icharts.py uses `date_from` and `date_to` in params.
    # Let's check `download_icharts.py` Step 2974 again.
    # Line 86: 'from': date_from, 'to': date_to.
    # And recovery_download.py passes `strftime("%Y-%m-%d")` strings.
    # But `download_icharts.py` line 129 uses `data['t']` which is unix.
    # The REQUEST params are likely UNIX timestamps for TradingView API.
    # RE-VERIFYING download_icharts.py logic in your mind:
    # Most TV charts accept UNIX. But recovery_download.py passed strings "2025-04-09".
    # PHP backend might convert strings. I will stick to what WORKED: strings "YYYY-MM-DD".
    
    s_date_str = from_date.strftime("%Y-%m-%d")
    e_date_str = to_date.strftime("%Y-%m-%d")

    params = {
        'symbol': symbol,
        'resolution': '1', # 1 minute
        'from': s_date_str,
        'to': e_date_str, 
        'u': 'arung', # Default user from script
        'sid': '9t9743jovml17qfhjc09p1lid4', # Placeholder, overwritten by cookie?
        'q1': '1',
        'q2': '1',
        'mode': 'INTRA',
        'DataRequest': '2',
        'firstDataRequest': 'true',
        'countback': '3000' # Countback is priority usually
    }
    
    # Cookie Header
    req_headers = HEADERS.copy()
    req_headers['Cookie'] = f"PHPSESSID={session_id}"
    
    try:
        resp = requests.get(BASE_URL, params=params, headers=req_headers, timeout=15)
        
        if resp.status_code != 200:
            return f"HTTP {resp.status_code}"
            
        try:
            data = resp.json()
        except:
            return "Invalid JSON"
            
        if 's' in data and data['s'] == 'no_data':
            return "No Data"
            
        if 't' in data and len(data['t']) > 0:
            # We have data!
            # Format: t (timestamp), o, h, l, c (straddle price), v (volume)
            # We need to save it in the Backtester format.
            # Backtester expects: Date, Time, CE_Price, PE_Price?
            # Wait, this endpoint returns the *Straddle Chart* data (Sum of CE+PE).
            # It does NOT return individual CE/PE prices.
            
            # CRITICAL CHECK:
            # The User said "download data as straddle... attaching your earlier download as example".
            # Does the backtester support "Straddle Combined Price"?
            # `backtest_main.py`: `row['CE_Price'] + row['PE_Price']`
            # If the CSV has "Close", "Open" etc for the *Straddle*, we can't perform SL checks on individual legs.
            # BUT `download_icharts.py` was saving `NIFTY_..._Straddle.csv` with `open, high, low, close`.
            # Let's check if `backtest_main.py` handles this.
            # If not, the previous "successful" download might be useless for leg-based SL.
            # However, the user *explicitly* asked for this format.
            # "download data as straddle , not indicuaidaul ce an pe".
            
            # I will save the data exactly as `download_icharts.py` did.
            # Columns: timestamp, open, high, low, close, volume, datetime
            
            df = pd.DataFrame({
                'timestamp': data['t'],
                'open': data['o'],
                'high': data['h'],
                'low': data['l'],
                'close': data['c'],
                'volume': data.get('v', [])
            })
            
            # Convert timestamp (Unix) to Datetime (IST)
            # Assuming server returns UTC unix, +5.5h for IST
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s') + timedelta(hours=5, minutes=30)
            
            # Filter for the specific expiry date only? 
            # Or keep the whole week? 
            # The user wants "data for these years... expiry date data".
            # Usually we filter for the expiry day itself.
            # `df = df[df['datetime'].dt.date == expiry_date]`
            # Let's keep all captured data for safety, but maybe filter in backtest.
            # Actually, to match file size and relevance, let's filter to Expiry Day 09:15-15:30.
            
            mask = df['datetime'].dt.date == expiry_date
            df_day = df[mask].copy()
            
            if df_day.empty:
                return "Data Mismatch (Date)"
            
            # Save
            df_day.to_csv(filepath, index=False)
            return f"Downloaded ({len(df_day)} rows)"
            
    except Exception as e:
        return f"Error: {e}"
        
    return "Unknown Error"

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        
    session_id = load_cookie()
    if not session_id: return

    print(f"Scanning Index Data in: {INDEX_DATA_DIR}", flush=True)
    
    # 1. Identify all valid trading dates from files
    # Pattern: NIFTY-1minute-data-YYYY-MM-DD.csv
    files = glob.glob(os.path.join(INDEX_DATA_DIR, "NIFTY-1minute-data-*.csv"))
    valid_dates = {} # date -> filepath
    
    for f in files:
        fname = os.path.basename(f)
        try:
            date_str = fname.replace("NIFTY-1minute-data-", "").replace(".csv", "")
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if START_YEAR <= d.year <= END_YEAR:
                valid_dates[d] = f
        except: pass
        
    print(f"Found {len(valid_dates)} trading dates between {START_YEAR}-{END_YEAR}.", flush=True)
    
    # 2. Identify Weekly Expiries (Thursday, then Wednesday)
    expiries = []
    
    curr = date(START_YEAR, 1, 1)
    end = date(END_YEAR, 12, 31)
    
    while curr <= end:
        # Check if it's a Thursday
        if curr.weekday() == 3: # Thursday
            if curr in valid_dates:
                expiries.append(curr)
            else:
                # Thursday holiday? Check Wednesday
                wed = curr - timedelta(days=1)
                if wed in valid_dates:
                    expiries.append(wed)
        curr += timedelta(days=1)
        
    print(f" identified {len(expiries)} expiry dates.", flush=True)
    
    # 3. Download Logic
    for exp_date in expiries:
        fpath = valid_dates[exp_date]
        atm = get_atm_from_file(fpath)
        if not atm:
            print(f"Warning: Could not determine ATM for {exp_date}. Skipping.", flush=True)
            continue
            
        print(f"\nProcessing Expiry: {exp_date} | ATM: {atm}", flush=True)
        
        # Download Range: +/- 1000 points (20 strikes @ 50)
        start_strike = int(atm - 1000)
        end_strike = int(atm + 1000)
        
        strikes = range(start_strike, end_strike + 50, 50)
        
        for k in strikes:
            status = download_straddle(session_id, "NIFTY", exp_date, k)
            print(f"  Strike {k}: {status}", end='\r', flush=True)
            if status != "Skipped (Exists)":
                time.sleep(0.5) # Rate limit
                
        print(f"  Strike {k}: Done.", flush=True)

if __name__ == "__main__":
    main()
