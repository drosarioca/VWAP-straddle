
import requests
import json
import os
import sys

SID = "9t9743jovml17qfhjc09p1lid4"
USER = "arung"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php',
    'Cookie': f"PHPSESSID={SID}"
}

def check(url_suffix, params={}):
    url = f"https://www.icharts.in/opt/hcharts/stx8req/php/{url_suffix}"
    try:
        print(f"Check: {url_suffix}...", flush=True)
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        print(f"--- {url_suffix} ---", flush=True)
        try:
            data = resp.json()
            print(str(data)[:500], flush=True)
        except:
            print(resp.text[:500], flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

# 1. Check Spot Metadata
check("getLatestSpotPrice_fair.php")
# check("getHistPriceInfo.php")

# 2. Brute Force Symbol
BASE_URL = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"

def test(symbol):
    print(f"Testing: {symbol}", flush=True)
    params = {
        'symbol': symbol,
        'resolution': '1', 'from': '2026-02-12', 'to': '2026-02-13',
        'u': USER, 'sid': SID, 'mode': 'INTRA', 'DataRequest': '2', 'firstDataRequest': 'true'
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=2)
        if resp.status_code == 200:
            if '"s":"ok"' in resp.text:
                print(f"\n[SUCCESS] FOUND: {symbol}", flush=True)
                return True
    except: pass
    return False

prefixes = ["SENSEX", "BSE-SENSEX", "BSX", "SENSEX50"]
strikes = [76000, 77000]
expiries = ["20FEB26", "27FEB26", "13FEB26", "29JAN26"] # 29JAN might work?

print("\n--- Brute Force ---", flush=True)
found = False
for p in prefixes:
    if found: break
    for s in strikes:
        if found: break
        for e in expiries:
            # Try C/P
            sym = f"{p}-{s}C-{e}:{p}-{s}P-{e}"
            if test(sym):
                found = True; break
