
import json
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def main():
    print("--- iCharts Auto-Capture ---")
    print("Launching Chrome...")
    
    options = Options()
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        print("Navigating to iCharts...")
        driver.get("https://www.icharts.in/opt/StraddleChartsTV_Beta.php")
        
        print("\n" + "="*40)
        print("   PLEASE LOG IN TO ICHARTS NOW")
        print("   I am watching for the session cookie...")
        print("="*40 + "\n")
        
        while True:
            try:
                # Check cookies
                cookies = driver.get_cookies()
                phpsessid = next((c['value'] for c in cookies if c['name'] == 'PHPSESSID'), None)
                
                if phpsessid:
                    print(f"\n✅ SUCCESS! Detected Session ID: {phpsessid[:6]}...")
                    
                    # Construct Headers
                    cookie_str = f"PHPSESSID={phpsessid}"
                    
                    # Get UA
                    ua = driver.execute_script("return navigator.userAgent")
                    
                    headers = {
                        "Cookie": cookie_str,
                        "User-Agent": ua,
                        "Referer": "https://www.icharts.in/opt/StraddleChartsTV_Beta.php"
                    }
                    
                    # Save for my system
                    with open("icharts_headers.json", "w") as f:
                        json.dump(headers, f, indent=4)
                        
                    # Also save pure cookie text for backup
                    with open("cookie.txt", "w") as f:
                        f.write(cookie_str)
                        
                    print("Session saved. Closing browser in 3 seconds...")
                    time.sleep(3)
                    break
                else:
                    print("Waiting for login... (PHPSESSID not found yet)", end='\r')
                    time.sleep(2)
                    
            except Exception as e:
                print(f"Loop Error: {e}")
                break
                
    except Exception as e:
        print(f"Critical Error: {e}")
        input("Press Enter to close...")
    finally:
        try:
            driver.quit()
        except: pass
        print("Capture script finished.")

if __name__ == "__main__":
    main()
