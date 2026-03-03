
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

URL = "https://www.icharts.in/opt/StraddleChartsTV_Beta.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Cookie': COOKIE
}

print(f"Testing Main Page with Cookie...")
try:
    resp = requests.get(URL, headers=HEADERS, timeout=10)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        if "Logout" in resp.text or "arung" in resp.text:
            print("SUCCESS: Logged in as user.")
        elif "Login" in resp.text:
            print("FAILURE: Redirected to Login (Session Invalid)")
        else:
            print("UNKNOWN: Page loaded but login status unclear.")
            print(resp.text[:500])
    else:
        print(f"HTTP {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
