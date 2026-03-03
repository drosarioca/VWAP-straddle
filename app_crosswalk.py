
import streamlit as st
import pandas as pd
import os
import time
import sys
import datetime
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
import shutil

# Ensure we can import backtest_main
sys.path.append(os.getcwd())
try:
    from backtest_main import run_backtest
    import reporting_utils
    import importlib
    importlib.reload(reporting_utils)
    from reporting_utils import generate_variant_report
except ImportError:
    st.error("Could not import dependencies.")

st.set_page_config(
    layout="wide", 
    page_title="Crosswalk 🚦 Premium Batch Processor",
    page_icon="🚦"
)

# --- STYLING ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #2e7d32;
        color: white;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #1b5e20;
        transform: scale(1.02);
    }
    .variant-card {
        padding: 20px;
        border-radius: 15px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 10px;
    }
    .status-active { color: #4caf50; font-weight: bold; }
    .status-error { color: #f44336; font-weight: bold; }
    h1 {
        background: linear-gradient(90deg, #4caf50, #2196f3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/traffic-light.png", width=60)
    st.title("Crosswalk Pro")
    st.markdown("---")
    st.subheader("Configuration")
    max_workers = st.slider("Parallel Threads", 1, 8, 4, help="Number of years to process simultaneously per variant.")
    global_slippage = st.number_input("Global Slippage (Points)", min_value=0.0, max_value=10.0, value=0.0, step=0.5, help="Points to deduct from each trade (in addition to any Excel defined slippage).")
    st.markdown("---")
    st.info("System optimized for VWAP Low Non-Rolling variants.")

st.title("Crosswalk Batch Processor 🚦")
st.markdown("#### High-Performance Parameter Optimization & Reporting Engine")

# --- CONSTANTS ---
RESULTS_BASE_DIR = "results output"

# --- HELPER: WRAPPER FOR MULTIPROCESSING ---
def run_variant_year(params, year):
    """
    Worker function to run backtest for a single year for a variant.
    Returns: (Year, DataFrame, Logs, Usage_Stats)
    """
    # 1. Map Excel Params to Function Args
    # Note: Param names in Excel might differ slightly, need robust mapping
    
    # Extract params
    p = params
    
    try:
        # Construct Time Objects
        entry_time = datetime.time(int(p['Enter_Hour']), int(p['Enter_Min']))
        exit_time = datetime.time(int(p['Exit_Hour']), int(p['Exit_Min']))
        
        # Spot Check Time (Use .get with fallback to entry_time if missing/empty in excel)
        if 'Spot_Check_Hour' in p and pd.notna(p['Spot_Check_Hour']):
             spot_check_time = datetime.time(int(p['Spot_Check_Hour']), int(p['Spot_Check_Min']))
        else:
             spot_check_time = entry_time

        # Run Backtest
        # Capture stdout? No, just rely on logs returned.
        result = run_backtest(
            min_entry_time=entry_time,
            spot_check_time=spot_check_time, # Pass explicit spot check
            entry_window_mins=int(p['Entry_Window_Mins']),
            exit_time=exit_time,
            sl_min_pts=int(p['SL_Min']),
            sl_max_pts=int(p['SL_Max']),
            trail_trigger=int(p['Trail_Trigger']),
            trail_step=int(p['Trail_Step']),
            rolling_step=int(p['Rolling_Step']),
            portfolio_sl=int(p['Portfolio_SL']),
            strategy_mode=p['Strategy_Mode'],
            years=[year] # Pass single year list
        )
        
        # Handle Tuple Return
        if isinstance(result, tuple):
            df, daily_summaries = result
            # Fix: Extract logs from structured summaries
            logs = []
            for item in daily_summaries:
                 logs.append(f"--- Date: {item['Date']} | PnL: {item['PnL']} ---")
                 if 'Detailed Events' in item:
                     logs.append(item['Detailed Events'])
        else:
            df = result
            logs = []
            
        return (year, df, logs, daily_summaries if isinstance(result, tuple) else [])
        
    except Exception as e:
        return (year, pd.DataFrame(), [f"CRITICAL ERROR: {str(e)}"], [])

def process_batch(df_input):
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(RESULTS_BASE_DIR, f"Crosswalk_{timestamp_str}")
    os.makedirs(batch_dir, exist_ok=True)
    
    summary_records = []
    
    total_variants = len(df_input)
    prog_bar = st.progress(0)
    status_text = st.empty()
    
    # iterate rows
    for i, row in df_input.iterrows():
        variant_name = str(row['Name_Tag'])
        status_text.text(f"Processing {i+1}/{total_variants}: {variant_name}")
        
        # Parse Years
        years_str = str(row['Years'])
        if "," in years_str:
            target_years = [int(y.strip()) for y in years_str.split(",") if y.strip().isdigit()]
        else:
            target_years = [int(years_str)] if years_str.isdigit() else []
            
        if not target_years:
            st.error(f"Invalid Years for {variant_name}: {years_str}")
            continue
            
        # Create Variant Folder
        variant_dir = os.path.join(batch_dir, variant_name)
        os.makedirs(variant_dir, exist_ok=True)
        
        variant_dfs = []
        variant_logs = []
        variant_logs_structured = []
        
        variant_params = row.to_dict()
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**Processing Variant:** `{variant_name}`")
        with col2:
            st.markdown('<span class="status-active">▶ Running</span>', unsafe_allow_html=True)

        # --- PARALLEL EXECUTION PER YEAR ---
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Prepare futures
            futures = {executor.submit(run_variant_year, row, year): year for year in target_years}
            
            for future in concurrent.futures.as_completed(futures):
                year = futures[future]
                try:
                    # Fix: run_variant_year now returns (year, df, logs, logs_structured)
                    y, df, logs, logs_struct = future.result()
                    if not df.empty:
                        variant_dfs.append(df)
                    variant_logs.extend(logs)
                    variant_logs_structured.extend(logs_struct)
                except Exception as exc:
                    variant_logs.append(f"Year {year} generated an exception: {exc}")
        
        # Aggregate Results
        if variant_dfs:
            final_df = pd.concat(variant_dfs, ignore_index=True)
            final_df.sort_values(by="Date", inplace=True)
            
            # Prepare Params for Report
            variant_params = row.to_dict()
            
            # Determine Lot Size (Nifty: 65, Sensex: 20)
            # Check for 'Lot_Size' in Excel, or guess from Name_Tag
            lot_size = 65 # Default Nifty
            name_lower = variant_name.lower()
            if 'sensex' in name_lower:
                lot_size = 20
            elif 'nifty' in name_lower:
                lot_size = 65
            
            # Allow explicit override if 'Lot_Size' column exists
            if 'Lot_Size' in variant_params and pd.notna(variant_params['Lot_Size']):
                lot_size = float(variant_params['Lot_Size'])
            
            # Determine Slippage
            slippage = global_slippage
            if 'Slippage' in variant_params and pd.notna(variant_params['Slippage']):
                slippage = float(variant_params['Slippage'])
            
            variant_params['Calculated_Lot_Size'] = lot_size
            variant_params['Applied_Slippage'] = slippage
            
            # Save Detailed Multi-Sheet Report
            report_path = os.path.join(variant_dir, f"Detailed_Report_{variant_name}.xlsx")
            calc_metrics = generate_variant_report(report_path, final_df, variant_params, daily_summaries=variant_logs_structured, lot_size=lot_size, slippage=slippage)
            
            # Merge all original params and new metrics into the summary record
            record = variant_params.copy()
            if isinstance(calc_metrics, list):
                for m in calc_metrics:
                    record[m['Metric']] = m['Value']

            record.update({
                "Report_Link": report_path
            })
            summary_records.append(record)
        else:
            summary_records.append({
                "Name_Tag": variant_name,
                "Status": "No Trades / Error"
            })
            
        # Save Logs
        with open(os.path.join(variant_dir, "execution.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(variant_logs))
            
        prog_bar.progress((i + 1) / total_variants)
        
    # Save Summary
    summary_df = pd.DataFrame(summary_records)
    summary_path = os.path.join(batch_dir, "Crosswalk_Summary.xlsx")
    summary_df.to_excel(summary_path, index=False)
    
    st.success(f"Batch Processing Complete! Results saved at: {batch_dir}")
    st.dataframe(summary_df)


# --- UI ---
uploaded_file = st.file_uploader("Upload Crosswalk Input (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.write("Loaded Variants:")
    st.dataframe(df)
    
    if st.button("Run Batch Processor"):
        process_batch(df)
