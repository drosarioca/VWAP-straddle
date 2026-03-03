
import requests

SID = "gvvrmg9lb4n2dl0dvct48j0ver" 
USER = "arung"
BASE_URL = "https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php"

# Test one known valid symbol
symbol = "NIFTY-25000C-03FEB26:NIFTY-25000P-03FEB26"
    
params = {
    'symbol': symbol,
    'resolution': '1',
    'from': "2026-01-20",
    'to': "2026-02-02",
    'u': USER,
    'sid': SID,
    'q1': '1',
    'q2': '1',
    'mode': 'INTRA',
    'DataRequest': '2',
    'firstDataRequest': 'true',
    'countback': '100'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # Added Referer just in case
    'Referer': 'https://www.icharts.in/opt/StraddleChartsTV_Beta.php',
    'Origin': 'https://www.icharts.in',
    'X-Requested-With': 'XMLHttpRequest'
}

print(f"Testing URL: {BASE_URL}")
resp = requests.get(BASE_URL, params=params, headers=headers)
print(f"Status: {resp.status_code}")
print("Response Headers:", resp.headers)
print("Response Body Snippet:")
print(resp.text[:500])
