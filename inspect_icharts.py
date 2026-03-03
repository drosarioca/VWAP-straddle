
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def main():
    print("--- iCharts Inspector ---")
    print("Launching Browser...")
    
    # Setup Chrome
    options = Options()
    options.add_argument("--start-maximized")
    # Keep browser open even if script finishes? No, we control it.
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        target_url = "https://www.icharts.in/opt/StraddleChartsTV_Beta.php"
        driver.get(target_url)
        
        print(f"\nBrowser opened to: {target_url}")
        print("ACTION REQUIRED:")
        print("1. In the opened browser window, LOG IN manually with your credentials.")
        print("2. Ensure you are on the Straddle Charts page.")
        print("3. Try to load ONE chart (select a date and strike) to ensure data is loaded.")
        print("4. When ready, create a file named 'DONE.txt' in this folder: ")
        print(f"   {os.getcwd()}")
        print("\nWaiting for 'DONE.txt'...")
        
        # Remove DONE.txt if exists
        if os.path.exists("DONE.txt"):
            os.remove("DONE.txt")
            
        while not os.path.exists("DONE.txt"):
            time.sleep(1)
            
        print("Found DONE.txt! Capturing page source...")
        
        # Capture Source
        html = driver.page_source
        with open("icharts_source.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Success! Saved to 'icharts_source.html'.")
        print("You can now close the browser.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        if os.path.exists("DONE.txt"):
            os.remove("DONE.txt")
        # trigger close? Maybe keep open for user to close.
        # driver.quit() 

if __name__ == "__main__":
    main()
