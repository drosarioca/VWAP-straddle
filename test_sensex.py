
import requests
import json
import os
import datetime

# Configuration
SID = "9t9743jovml17qfhjc09p1lid4"
BASE_URL = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"
USER = "arung"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php'
}

# Try loading cookie
if os.path.exists("cookie.txt"):
    with open("cookie.txt", "r") as f:
        HEADERS['Cookie'] = f.read().strip()
elif SID:
    HEADERS['Cookie'] = f"PHPSESSID={SID}"

def test_symbol(symbol_name):
    print(f"Testing Symbol: {symbol_name}")
    params = {
        'symbol': symbol_name,
        'resolution': '1',
        'from': '2026-02-12', 
        'to': '2026-02-13',
        'u': USER,
        'sid': SID,
        'q1': '1', 'q2': '1', 'mode': 'INTRA', 'DataRequest': '2', 'firstDataRequest': 'true', 'countback': '100'
    }
    
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            try:
                data = resp.json()
                if 's' in data and data['s'] == 'ok':
                    print("SUCCESS! Data found.")
                    print(f"Rows: {len(data.get('t', []))}")
                    return True
                else:
                    print(f"Response: {data.get('s', 'Unknown')}")
            except:
                print("Response is not JSON.")
    except Exception as e:
        print(f"Error: {e}")
    return False

# 1. Validate with Nifty (Known Good from logs)
# Nifty ~ 25050 in Feb 2026 based on URLs
print("--- Validating Session (Nifty) ---")
test_symbol("NIFTY-25050C-03FEB26:NIFTY-25050P-03FEB26")

# 2. Test Sensex Candidates
print("\n--- Testing Sensex ---")
expiry = "20FEB26" # Upcoming Friday
strike = 77000 

candidates = [
    f"SENSEX-{strike}C-{expiry}:SENSEX-{strike}P-{expiry}",
    f"BSE-SENSEX-{strike}C-{expiry}:BSE-SENSEX-{strike}P-{expiry}",
    f"SENSEX50-{strike}C-{expiry}:SENSEX50-{strike}P-{expiry}",
    f"BSX-{strike}C-{expiry}:BSX-{strike}P-{expiry}",
    # Try different expiry format?
    # Maybe check if there are other expiries
]

for cand in candidates:
    if test_symbol(cand):
        print(f"FOUND VALID SYMBOL: {cand}")
        break
