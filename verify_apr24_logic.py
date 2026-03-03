
from backtest_main import construct_straddle, IChartsDataManager, ICHARTS_DIR
import pandas as pd
import datetime

icharts_loader = IChartsDataManager(ICHARTS_DIR)

def check_conditions():
    target_date = datetime.date(2025, 4, 24)
    strike = 24300
    df = construct_straddle(target_date, strike)
    
    start_dt = datetime.datetime.combine(target_date, datetime.time(9, 34))
    end_dt = start_dt + datetime.timedelta(minutes=30)
    
    print(f"--- Logic Check for {target_date} ---")
    
    for curr_time in df.index:
        if curr_time < start_dt or curr_time > end_dt:
            continue
            
        # Get Index Location
        idx_loc = df.index.get_loc(curr_time)
        
        # Slices
        # Group A: idx-5 to idx-2
        grp_a = df.iloc[idx_loc-5 : idx_loc-2]
        # Group B: idx-2 to idx+1
        grp_b = df.iloc[idx_loc-2 : idx_loc+1]
        
        # Check VWAP Conditions
        fail_reasons = []
        
        # Cond 1: Group A < VWAP
        for t, row in grp_a.iterrows():
            if row['Close'] >= row['VWAP']:
                fail_reasons.append(f"GrpA {t.time()} Close({row['Close']}) >= VWAP({row['VWAP']:.2f})")
                
        # Cond 2: Group B < VWAP
        for t, row in grp_b.iterrows():
            if row['Close'] >= row['VWAP']:
                fail_reasons.append(f"GrpB {t.time()} Close({row['Close']}) >= VWAP({row['VWAP']:.2f})")
                
        # Cond 3: Current Close < Min Low A
        min_low_a = grp_a['Low'].min()
        if df.loc[curr_time]['Close'] >= min_low_a:
             fail_reasons.append(f"Trigger {curr_time.time()} Close({df.loc[curr_time]['Close']}) >= LowA({min_low_a})")

        if fail_reasons:
            print(f"[{curr_time.time()}] NO ENTRY. Reasons:")
            for r in fail_reasons[:3]: # Print top 3 reasons
                print(f"  - {r}")
        else:
            print(f"[{curr_time.time()}] *** ENTRY SIGNAL ***")
            break

if __name__ == "__main__":
    check_conditions()
