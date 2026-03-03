
import pandas as pd
import os
import sys
import datetime
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
import shutil

# Ensure we can import backtest_main
sys.path.append(os.getcwd())
try:
    from backtest_main import run_backtest
except ImportError:
    print("Could not import 'backtest_main.py'.")
    pass

# --- CONSTANTS ---
RESULTS_BASE_DIR = "results output"
INPUT_FILE = "optimization_smart.xlsx"

# --- WORKER FUNCTION ---
def run_variant_year(params, year):
    """
    Worker function to run backtest for a single year for a variant.
    Returns: (Year, DataFrame, Logs)
    """
    p = params
    try:
        # Construct Time Objects
        entry_time = datetime.time(int(p['Enter_Hour']), int(p['Enter_Min']))
        exit_time = datetime.time(int(p['Exit_Hour']), int(p['Exit_Min']))
        
        # Spot Check Time
        if 'Spot_Check_Hour' in p and pd.notna(p['Spot_Check_Hour']):
             spot_check_time = datetime.time(int(p['Spot_Check_Hour']), int(p['Spot_Check_Min']))
        else:
             spot_check_time = entry_time

        # Run Backtest
        result = run_backtest(
            min_entry_time=entry_time,
            spot_check_time=spot_check_time,
            entry_window_mins=int(p['Entry_Window_Mins']),
            exit_time=exit_time,
            sl_min_pts=int(p['SL_Min']),
            sl_max_pts=int(p['SL_Max']),
            trail_trigger=int(p['Trail_Trigger']),
            trail_step=int(p['Trail_Step']),
            rolling_step=int(p['Rolling_Step']),
            portfolio_sl=int(p['Portfolio_SL']),
            strategy_mode=p['Strategy_Mode'],
            years=[year]
        )
        
        # Handle Tuple Return
        if isinstance(result, tuple):
            df, daily_summaries = result
            logs = []
            for item in daily_summaries:
                 # logs.append(f"--- Date: {item['Date']} | PnL: {item['PnL']} ---")
                 if 'Detailed Events' in item:
                     logs.append(item['Detailed Events'])
        else:
            df = result
            logs = []
            
        return (year, df, logs)
        
    except Exception as e:
        return (year, pd.DataFrame(), [f"CRITICAL ERROR: {str(e)}"])

def process_batch():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print(f"Loading {INPUT_FILE}...")
    df_input = pd.read_excel(INPUT_FILE)
    
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(RESULTS_BASE_DIR, f"Crosswalk_{timestamp_str}")
    os.makedirs(batch_dir, exist_ok=True)
    
    summary_records = []
    
    total_variants = len(df_input)
    print(f"Starting batch execution for {total_variants} variants...")
    
    # iterate rows
    for i, row in df_input.iterrows():
        variant_name = str(row['Name_Tag'])
        print(f"[{i+1}/{total_variants}] Processing {variant_name}...")
        
        # Parse Years
        years_str = str(row['Years'])
        if "," in years_str:
            target_years = [int(y.strip()) for y in years_str.split(",") if y.strip().isdigit()]
        else:
            target_years = [int(years_str)] if years_str.isdigit() else []
            
        if not target_years:
             # Default to config if missing? No, user provided.
             # Check if we should use all years from config
             if hasattr(sys.modules.get('backtest_main'), 'DATA_YEARS'):
                 from backtest_main import DATA_YEARS
                 target_years = DATA_YEARS
             else:
                 target_years = [2021, 2022, 2023, 2024, 2025]
            
        # Create Variant Folder
        variant_dir = os.path.join(batch_dir, variant_name)
        os.makedirs(variant_dir, exist_ok=True)
        
        variant_dfs = []
        variant_logs = []
        
        # --- PARALLEL EXECUTION PER YEAR ---
        with ProcessPoolExecutor(max_workers=min(len(target_years), 4)) as executor:
            futures = {executor.submit(run_variant_year, row, year): year for year in target_years}
            
            for future in concurrent.futures.as_completed(futures):
                year = futures[future]
                try:
                    y, df, logs = future.result()
                    if not df.empty:
                        variant_dfs.append(df)
                    variant_logs.extend(logs)
                except Exception as exc:
                    variant_logs.append(f"Year {year} generated an exception: {exc}")
        
        # Aggregate Results
        if variant_dfs:
            final_df = pd.concat(variant_dfs, ignore_index=True)
            final_df.sort_values(by="Date", inplace=True)
            
            # Save Detailed Report
            report_path = os.path.join(variant_dir, "Report.xlsx")
            final_df.to_excel(report_path, index=False)
            
            # Calculate KPIs
            total_pnl = final_df['PnL'].sum()
            win_rate = (len(final_df[final_df['PnL'] > 0]) / len(final_df) * 100) if not final_df.empty else 0
            dd = (final_df['PnL'].cumsum() - final_df['PnL'].cumsum().cummax()).min()
            
            summary_records.append({
                "Name_Tag": variant_name,
                "Total_PnL": total_pnl,
                "Win_Rate": win_rate,
                "Max_DD": dd,
                "Trades": len(final_df),
                "Report_Path": report_path
            })
        else:
            summary_records.append({
                "Name_Tag": variant_name,
                "Status": "No Trades / Error"
            })
            
        # Save Logs
        with open(os.path.join(variant_dir, "execution.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(variant_logs))
            
    # Save Summary
    summary_df = pd.DataFrame(summary_records)
    summary_path = os.path.join(batch_dir, "Crosswalk_Summary.xlsx")
    summary_df.to_excel(summary_path, index=False)
    
    print(f"Batch Processing Complete! Results saved at: {batch_dir}")

if __name__ == "__main__":
    process_batch()
