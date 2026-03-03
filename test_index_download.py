
import requests
import json
import os

sid = "483qmssvqhs6ork9klkguoh5nl"
url = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"
user = "arung"

target_date = "2026-02-03"
# Symbol Guess 1: NIFTY
# Symbol Guess 2: NIFTY 50
# Symbol Guess 3: NIFTY-I (Spot)

for sym in ["NIFTY", "NIFTY 50", "NIFTY-I"]:
    print(f"Testing Symbol: {sym}...")
    params = {
        'symbol': sym,
        'resolution': '1',
        'from': target_date,
        'to': target_date,
        'u': user,
        'sid': sid,
        'mode': 'INTRA',
        'DataRequest': '2',
        'firstDataRequest': 'true',
        'countback': '1000'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php',
        'Cookie': f"PHPSESSID={sid}"
    }

    resp = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Resp text: {resp.text[:200]}")
    if "ok" in resp.text:
        print(f"SUCCESS with symbol {sym}!")
        break
