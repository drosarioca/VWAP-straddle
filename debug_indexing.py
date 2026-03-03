
from backtest_main import IChartsDataManager
from datetime import date
import os

loader = IChartsDataManager("icharts_download")
print(f"Total files indexed: {len(loader.file_map)}")

target_date = date(2026, 2, 10)
target_strike = 25900

expiry = loader.get_nearest_expiry(target_date)
print(f"Nearest Expiry for {target_date}: {expiry}")

fpath = loader.file_map.get((expiry, target_strike))
print(f"File Path for ({expiry}, {target_strike}): {fpath}")

if fpath:
    print(f"File exists: {os.path.exists(fpath)}")
else:
    print("SEARCHING MANUALLY...")
    found = False
    for (exp, strike), path in loader.file_map.items():
        if exp == target_date:
            if strike == target_strike:
                print(f"MATCH FOUND: {exp}, {strike}")
                found = True
            # else:
            #    print(f"Strike mismatch: {strike} vs {target_strike}")
    if not found:
        print("No match found for date in file_map.")
        # Check all expiries for Feb 2026
        feb_expiries = [e for e in loader.available_expiries if e.month == 2 and e.year == 2026]
        print(f"Available Feb 2026 expiries: {sorted(feb_expiries)}")
