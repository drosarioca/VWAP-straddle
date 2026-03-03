
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
    'Cookie': COOKIE
}

# Target: July 5, 2024 (Friday) - Spot ~79800
STRIKE = 79800
EXPIRY = "05JUL24"
DATE = "2024-07-05"

templates = [
    f"SENSEX-{STRIKE}C-{EXPIRY}:SENSEX-{STRIKE}P-{EXPIRY}",
    f"SENSEX-{STRIKE}CE-{EXPIRY}:SENSEX-{STRIKE}PE-{EXPIRY}",
    f"BSE-SENSEX-{STRIKE}C-{EXPIRY}:BSE-SENSEX-{STRIKE}P-{EXPIRY}",
    f"BSX-{STRIKE}C-{EXPIRY}:BSX-{STRIKE}P-{EXPIRY}",
    f"SENSEX50-{STRIKE}C-{EXPIRY}:SENSEX50-{STRIKE}P-{EXPIRY}",
    # Try different expiry format?
    f"SENSEX-{STRIKE}C-05JUL2024:SENSEX-{STRIKE}P-05JUL2024"
]

print(f"Testing for {DATE} (Spot ~{STRIKE})...")

for sym in templates:
    print(f"Trying: {sym} ... ", end="")
    params = {
        'symbol': sym,
        'resolution': '1', 'from': DATE, 'to': DATE,
        'u': 'arung', 'mode': 'INTRA', 'DataRequest': '2', 'firstDataRequest': 'true'
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            if '"s":"ok"' in resp.text:
                print("SUCCESS!")
                print(resp.text[:200])
                break
            elif '"s":"no_data"' in resp.text:
                print("No Data")
            else:
                print(f"Unknown: {resp.text[:50]}")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
