
import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Config
OUTPUT_DIR = "icharts_download"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_expiries_from_html():
    """Reads expiries from saved HTML file."""
    if not os.path.exists("icharts_source.html"):
        return []
    with open("icharts_source.html", "r", encoding="utf-8") as f:
        try:
            soup = BeautifulSoup(f.read(), 'html.parser')
            select = soup.find('select', {'id': 'optExpDate_hist'})
            return [o.get('value').strip() for o in select.find_all('option') if o.get('value')]
        except:
            return []

def generate_backups():
    """Generates all Thursday expiries for 2024-2025."""
    expiries = []
    for year in [2024, 2025]:
        d = datetime(year, 1, 1)
        # Find first Thursday
        while d.weekday() != 3:
            d += timedelta(days=1)
        
        while d.year == year:
            # Format: DDMMMYY e.g. 04JAN24
            code = d.strftime("%d%b%y").upper()
            expiries.append(code)
            d += timedelta(days=7)
    return expiries

def main():
    print("--- iCharts Browser Downloader ---")
    
    # Setup Chrome with Stealth Options ... (omitted) ...
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # CDP Stealth
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    try:
        # 1. Login Phase
        driver.get("https://www.icharts.in/opt/StraddleChartsTV_Beta.php")
        print("\nACTION REQUIRED: Log in, Load Chart, Create DONE.txt")
        
        if os.path.exists("DONE.txt"): os.remove("DONE.txt")
        while not os.path.exists("DONE.txt"):
            time.sleep(1)
            
        print("Starting Download Sequence...")
        
        # Capture Session ID
        cookies = driver.get_cookies()
        sid = None
        for c in cookies:
            if c['name'] == 'PHPSESSID':
                sid = c['value']
                break
        print(f"Session ID (Cookie): {sid}")
        
        # 2. Prepare Queue
        print("Extracting Expiries...")
        target_expiries = []
        try:
            # Wait for element
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "optExpDate_hist")))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            select = soup.find('select', {'id': 'optExpDate_hist'})
            all_expiries = [o.get('value').strip() for o in select.find_all('option') if o.get('value')] if select else []
            target_expiries = [e for e in all_expiries if e.endswith("24") or e.endswith("25")]
        except Exception as e:
            print(f"Live extraction failed: {e}")
            
        if not target_expiries:
            print("Fallback: Generating Standard Thursday Expiries for 2024-2025.")
            target_expiries = generate_backups()
            
        print(f"Targeting {len(target_expiries)} expiries.")
        
        # Strikes
        strikes = range(20000, 27000, 100)
        
        # 3. Iterate
        for expiry in target_expiries:
            try:
                # Calculate Dates
                exp_date = datetime.strptime(expiry, "%d%b%y")
                start_date = exp_date - timedelta(days=7) # 1 week
                s_str = start_date.strftime("%Y-%m-%d")
                e_str = exp_date.strftime("%Y-%m-%d")
                
                print(f"Processing {expiry} ({s_str} to {e_str})")
                
                for strike in strikes:
                    # Construct URL WITH SID
                    symbol = f"NIFTY-{strike}C-{expiry}:NIFTY-{strike}P-{expiry}"
                    
                    # Update: Must include 'sid' parameter matching cookie
                    sid_param = f"&sid={sid}" if sid else ""
                    
                    data_url = (
                        f"https://www.icharts.in/opt/getdata_Straddle_Chart_Tv_Charts_Daily_v3.php?"
                        f"symbol={symbol}&resolution=1&from={s_str}&to={e_str}"
                        f"&u=arung&q1=1&q2=1&mode=INTRA&DataRequest=2&firstDataRequest=true&countback=3000"
                        f"{sid_param}"
                    )
                    # We inject the cookie driven session
                    driver.get(data_url)
                    
                    # Wait for body text
                    time.sleep(0.5) # Gentle wait
                    content = driver.find_element(By.TAG_NAME, "body").text
                    
                    # Parse JSON
                    try:
                        data = json.loads(content)
                        if 's' in data and data['s'] == 'no_data':
                            # print(f"No Data: {symbol}")
                            continue
                        
                        if 't' in data and len(data['t']) > 0:
                            # Save
                            df = pd.DataFrame({
                                'timestamp': data['t'],
                                'open': data['o'],
                                'high': data['h'],
                                'low': data['l'],
                                'close': data['c'],
                                'volume': data['v'] if 'v' in data else 0
                            })
                            # Convert Time
                            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s') + timedelta(minutes=330)
                            
                            filename = f"NIFTY_{expiry}_{strike}_Straddle.csv"
                            path = os.path.join(OUTPUT_DIR, filename)
                            df.to_csv(path, index=False)
                            print(f"Saved {filename} ({len(df)} rows)")
                            
                    except json.JSONDecodeError:
                        # Maybe invalid session?
                        if "Invalid Session" in content:
                            print("Session Lost! Please re-login and create DONE.txt again.")
                            if os.path.exists("DONE.txt"): os.remove("DONE.txt")
                            while not os.path.exists("DONE.txt"):
                                time.sleep(1)
                        else:
                            print(f"JSON Error: {content[:50]}...")
                            
            except Exception as e:
                print(f"Error processing expiry {expiry}: {e}")
                
        print("Download Complete.")
        
    except Exception as main_e:
        print(f"Critical Error: {main_e}")
    finally:
        print("Browser staying open for inspection. Close manually if done.")
        # driver.quit()

if __name__ == "__main__":
    main()
