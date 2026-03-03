
import requests
import os
import datetime

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
    'Cookie': COOKIE
}

# Start Checking from Sept 2024
start_date = datetime.date(2024, 9, 2)
end_date = datetime.date(2024, 9, 15)

strike_map = {
    # Approx spot for early Sept 2024 was ~82000? Let's guess or use standard range
    # Actually let's use a wide range of strikes for a single date to be sure
}

# 6 Sept 2024 (Friday)
# Spot ~ 81000 - 82000? 
# Let's try to get data for 6th Sept (Friday)
DATE = "2024-09-06"
EXPIRY = "06SEP24"
STRIKES = [80000, 81000, 81100, 81200, 81500, 82000]

print(f"Testing {DATE} (Expiry {EXPIRY})...")

for s in STRIKES:
    sym = f"SENSEX-{s}C-{EXPIRY}:SENSEX-{s}P-{EXPIRY}" # Try standard first
    params = {
        'symbol': sym,
        'resolution': '1', 'from': DATE, 'to': DATE,
        'u': 'arung', 'mode': 'INTRA', 'DataRequest': '2', 'firstDataRequest': 'true'
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=5)
        print(f"{sym} -> {resp.status_code}")
        if resp.status_code == 200 and '"s":"ok"' in resp.text:
            print("SUCCESS DATA FOUND!")
            print(resp.text[:500])
            break
        elif resp.status_code == 403:
            print("403 Forbidden - Cookie might be limited or invalid for this segment?")
            # If 403, it often means the symbols are valid but user doesn't have access? 
            # OR the format is so wrong it triggers WAF?
            # Actually 403 usually means "Access Denied" which implies authentication concept.
    except Exception as e:
        print(e)
