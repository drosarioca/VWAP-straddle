
import requests
import os

# CONFIG
COOKIE_FILE = "cookie.txt"
if os.path.exists(COOKIE_FILE):
    with open(COOKIE_FILE, "r") as f:
        COOKIE = f.read().strip()
        if "PHPSESSID" not in COOKIE: COOKIE = f"PHPSESSID={COOKIE}"
else:
    print("No cookie found")
    exit()

BASE_URL = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php',
    'X-Requested-With': 'XMLHttpRequest',
    'Cookie': COOKIE
}

# Test with a symbol we expect might exist or at least give "no_data" (200 OK) instead of 403
# Using a far-dated Nifty or a recent past Nifty
DATE = "2025-01-30"
EXPIRY = "30JAN25"
STRIKE = 23000
SYMBOL = f"NIFTY-{STRIKE}C-{EXPIRY}:NIFTY-{STRIKE}P-{EXPIRY}"

# Extract SID from Cookie String
SID_VAL = COOKIE.replace("PHPSESSID=", "").strip()

print(f"Testing Nifty with Cookie: {SYMBOL} | SID: {SID_VAL}")
params = {
    'symbol': SYMBOL,
    'resolution': '1', 'from': DATE, 'to': DATE,
    'u': 'arung', 'sid': SID_VAL, 'mode': 'INTRA', 'DataRequest': '2', 'firstDataRequest': 'true'
}

try:
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=5)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success (Cookie is Good)")
        print(resp.text[:200])
    elif resp.status_code == 403:
        print("403 Forbidden (Cookie/Auth Issue)")
    else:
        print(f"Other Error: {resp.status_code}")
except Exception as e:
    print(f"Exception: {e}")
