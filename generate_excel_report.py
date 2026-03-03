
import pandas as pd
from datetime import date, timedelta
import backtest_main
from backtest_main import run_day_analysis

# Parameters (Matching Manual v3)
ROLLING_STEP = 80
PORTFOLIO_SL = 70
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)

def generate_report():
    print("Initializing Detailed Report Generation...")
    print(f"Parameters: Rolling={ROLLING_STEP}, PortfolioSL={PORTFOLIO_SL}")
    
    # Ensure loader is initialized
    backtest_main.icharts_loader = backtest_main.IChartsDataManager(backtest_main.ICHARTS_DIR)
    
    # Generate Date Range
    dates = []
    curr = START_DATE
    while curr <= END_DATE:
        dates.append(curr)
        curr += timedelta(days=1)
        
    records = []
    print(f"Scanning {len(dates)} days for valid 0DTE sessions...")
    
    count = 0
    for d in dates:
        # Skip Weekends
        if d.weekday() >= 5: continue
        
        # Check Expiry (0DTE only)
        nearest = backtest_main.icharts_loader.get_nearest_expiry(d)
        if not nearest: continue
        if (nearest - d).days != 0: continue 
        
        # Run Analysis
        logs, df, trades = run_day_analysis(
            d, 
            rolling_step=ROLLING_STEP, 
            portfolio_sl=PORTFOLIO_SL,
            entry_window_mins=30  # Explicitly set to 30
        )
        
        # Classification Logic
        day_type = "No Trade Day"
        pnl = 0.0
        details = ""
        
        if trades:
            pnl = sum(t.get('PnL', 0) for t in trades)
            
            # Determine Day Type based on primary outcome
            # Check if any trade was SL -> SL Day takes precedence?
            # Or if profitable? 
            # User request: "EOD day , or SL day or no trade day"
            
            has_sl = any(t.get('Type') in ['SL', 'Stop Loss', 'Trailing SL'] for t in trades)
            has_eod = any(t.get('Type') in ['EOD', 'Time Exit'] for t in trades)
            is_no_entry = all(t.get('Type') == 'No Entry' or t.get('Type') == 'Data Error' for t in trades)
            
            if is_no_entry:
                # Distinguish between Data Error vs Conditions Not Met
                if any(t.get('Type') == 'Data Error' for t in trades):
                    day_type = "Data Error"
                else:
                    day_type = "No Trade Day"
            elif has_sl:
                day_type = "SL Day"
            elif has_eod:
                day_type = "EOD Day"
            else:
                day_type = "Active" # Fallback
                
        # Format Logs
        events_str = "\n".join(logs)
        
        records.append({
            "Date": d,
            "Day Type": day_type,
            "PnL": pnl,
            "Detailed Events": events_str
        })
        
        count += 1
        if count % 10 == 0:
            print(f"Processed {count} days... (Last: {d})", end='\r')

    # Export
    print(f"\nCompiling Excel Report for {len(records)} active days...")
    df_report = pd.DataFrame(records)
    
    # Reorder columns
    cols = ["Date", "Day Type", "PnL", "Detailed Events"]
    df_report = df_report[cols]
    
    output_file = "Backtest_Detailed_Report_30min.xlsx"
    df_report.to_excel(output_file, index=False)
    print(f"Success! Report saved to: {output_file}")

if __name__ == "__main__":
    generate_report()
