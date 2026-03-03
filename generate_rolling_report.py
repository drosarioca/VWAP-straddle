
import pandas as pd
from datetime import date, timedelta, time
import backtest_main
from backtest_main import run_day_analysis

# Use existing config from backtest_main defaults or override
ROLLING_STEP = 80
PORTFOLIO_SL = 70
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)

# Timing
SPOT_CHECK_TIME = time(9, 32)
TRADING_START_TIME = time(9, 32) # Updated to 09:32 per user request
ENTRY_WINDOW = 30 

def generate_rolling_report():
    print("Initializing Rolling Strategy Report...")
    
    # Ensure loader is initialized
    backtest_main.icharts_loader = backtest_main.IChartsDataManager(backtest_main.ICHARTS_DIR)
    
    # 1. Create Parameters Dataframe
    params_data = {
        "Parameter": [
            "Strategy Mode", "Spot Check Time", "Trading Start Time", 
            "Entry Window", "Rolling Step", "Portfolio SL", 
            "Data Range Start", "Data Range End"
        ],
        "Value": [
            "VWAP Low Rolling (Ratchet)", str(SPOT_CHECK_TIME), str(TRADING_START_TIME),
            f"{ENTRY_WINDOW} Mins", f"{ROLLING_STEP} Pts", f"{PORTFOLIO_SL} Pts",
            str(START_DATE), str(END_DATE)
        ],
        "Description": [
            "Filter updates to Lowest Low on SL/Roll", "Time to identify initial ATM", "Time to start monitoring entries",
            "Duration of entry seeking window", "Spot move trigger for strike change", "Max daily loss cap",
            "-", "-"
        ]
    }
    df_params = pd.DataFrame(params_data)

    # 2. Run Backtest Loop
    dates = []
    curr = START_DATE
    while curr <= END_DATE:
        dates.append(curr)
        curr += timedelta(days=1)
        
    records = []
    print(f"Scanning {len(dates)} days...")
    
    count = 0
    for d in dates:
        if d.weekday() >= 5: continue
        
        nearest = backtest_main.icharts_loader.get_nearest_expiry(d)
        if not nearest: continue
        # if (nearest - d).days != 0: continue 
        
        # Run Analysis in ROLLING Mode
        logs, df, trades = run_day_analysis(
            d, 
            min_entry_time=TRADING_START_TIME,
            entry_window_mins=ENTRY_WINDOW,
            rolling_step=ROLLING_STEP, 
            portfolio_sl=PORTFOLIO_SL,
            strategy_mode="ROLLING_VWAP",
            spot_check_time=SPOT_CHECK_TIME
        )
        
        # Day Type Classification
        day_type = "No Trade Day"
        pnl = 0.0
        
        if trades:
            pnl = sum(t.get('PnL', 0) for t in trades)
            has_sl = any(t.get('Type') in ['SL', 'Stop Loss', 'Trailing SL'] for t in trades)
            has_eod = any(t.get('Type') in ['EOD', 'Time Exit'] for t in trades)
            is_no_entry = all(t.get('Type') == 'No Entry' or t.get('Type') == 'Data Error' for t in trades)
            
            if is_no_entry:
                day_type = "No Trade Day"
                if any(t.get('Type') == 'Data Error' for t in trades): day_type = "Data Error"
            elif has_sl:
                day_type = "SL Day"
            elif has_eod:
                day_type = "EOD Day"
            else:
                day_type = "Active"
                
        events_str = "\n".join(logs)
        
        records.append({
            "Date": d,
            "Day Type": day_type,
            "PnL": pnl,
            "Detailed Events": events_str
        })
        
        count += 1
        if count % 10 == 0:
            print(f"Processed {count} days...", end='\r')

    # 3. Export to Excel with Multiple Sheets
    print(f"\nCompiling Excel Report ({len(records)} days)...")
    df_report = pd.DataFrame(records)
    cols = ["Date", "Day Type", "PnL", "Detailed Events"]
    df_report = df_report[cols]
    
    output_file = "Backtest_Detailed_Report_Rolling.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_report.to_excel(writer, sheet_name='Daily Logs', index=False)
        df_params.to_excel(writer, sheet_name='Input Parameters', index=False)
        
        # Adjust column widths for readability (optional but nice)
        worksheet = writer.sheets['Daily Logs']
        worksheet.column_dimensions['A'].width = 12 # Date
        worksheet.column_dimensions['B'].width = 15 # Type
        worksheet.column_dimensions['C'].width = 10 # PnL
        worksheet.column_dimensions['D'].width = 100 # Events (Large)
        
        worksheet2 = writer.sheets['Input Parameters']
        worksheet2.column_dimensions['A'].width = 25
        worksheet2.column_dimensions['B'].width = 30
        worksheet2.column_dimensions['C'].width = 50

    print(f"Success! Report saved to: {output_file}")

if __name__ == "__main__":
    generate_rolling_report()
