
import requests
import json

sid = "483qmssvqhs6ork9klkguoh5nl" # User provided
url = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"
user = "arung"

# Try an expiry found in the HTML: 06JAN26
expiry = "06JAN26"
strike = "24200" # A strike seen in HTML
symbol = f"NIFTY-{strike}C-{expiry}:NIFTY-{strike}P-{expiry}"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php',
    'Cookie': f"PHPSESSID={sid}"
}

params = {
    'symbol': symbol,
    'resolution': '1',
    'from': '2026-01-06',
    'to': '2026-01-06',
    'u': user,
    'sid': "vaeivu938o473n5e741ummbgri", # SID from HTML source
    'mode': 'INTRA',
    'DataRequest': '2',
    'firstDataRequest': 'true',
    'countback': '1000'
}

print(f"Testing with User SID in Cookie and HTML SID in Params...")
resp = requests.get(url, params=params, headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
print(f"Resp text: {resp.text[:500]}")

if "no_data" in resp.text:
    print("\nRetrying with User SID in Params too...")
    params['sid'] = sid
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Resp text: {resp.text[:500]}")
