
import streamlit as st
import pandas as pd
import datetime # Added back
import matplotlib.pyplot as plt
from datetime import time, timedelta
import sys
import os
import io # Added for Excel buffer
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Ensure we can import backters
sys.path.append(os.getcwd())
try:
    import backtest_main
    import backtest_sensex
    import reporting_utils
    import importlib
    importlib.reload(reporting_utils)
    from reporting_utils import generate_variant_report, calculate_extensive_metrics
except ImportError:
    st.error("Could not import logic modules. check directory.")

st.set_page_config(layout="wide", page_title="VWAP Low Non-Rolling")

# --- CUSTOM CSS FOR FINTECH LOOK ---
st.markdown("""
<style>
    /* Dark Theme Background is default in Streamlit, lets refine it */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #1E232F;
        border: 1px solid #2E3342;
        padding: 15px;
        border-radius: 8px;
        color: white;
    }
    
    /* Metric Values (Large Numbers) */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        word-break: break-all; 
    }
    
    /* Success/Failure Colors in Metrics */
    div[data-testid="stMetricDelta"] > div {
        font-weight: bold;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #E6EAF1 !important;
        font-family: 'Roboto', sans-serif;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #0E1117;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E232F;
        border-bottom: 2px solid #00D4FF;
    }

</style>
""", unsafe_allow_html=True)



# --- Sidebar Controls ---
st.sidebar.header("Strategy Parameters")
target_index = st.sidebar.selectbox("Select Index", ["NIFTY", "SENSEX"])

strategy_variant = st.sidebar.selectbox(
    "Strategy Variant",
    ("VWAP Low Non-Rolling", "VWAP Low Rolling"),
    index=1,
    help="Non-Rolling: Standard. Rolling: Filter updates to Low on SL."
)

if strategy_variant == "VWAP Low Non-Rolling":
    st.title("VWAP Low Non-Rolling Method 🎯")
    st.markdown("**Version**: Final (Feb 2026) | **Entry**: 30m | **Risk**: 70pt | **Mode**: Non-Rolling")
    STRATEGY_MODE = "NON_ROLLING"
else:
    st.title("VWAP Low Rolling Method 🔄")
    st.markdown("**Version**: Beta | **Entry**: 30m | **Risk**: 70pt | **Mode**: Rolling Filter (Ratchet)")
    STRATEGY_MODE = "ROLLING_VWAP"


# Defaults based on Index
if target_index == "SENSEX":
    def_spot_min = 15
    def_roll_step = 100
else:
    def_spot_min = 32
    def_roll_step = 80

st.sidebar.subheader("Timing Configuration")
spot_check_hour = st.sidebar.number_input("Spot Check Hour", 9, 15, 9, help="Time to identify initial ATM Setup")
spot_check_min = st.sidebar.number_input("Spot Check Minute", 0, 59, def_spot_min)
spot_check_time = time(spot_check_hour, spot_check_min)

entry_hour = st.sidebar.number_input("Trading Start Hour", 9, 15, 9, help="Time to start taking trades")
entry_min = st.sidebar.number_input("Trading Start Minute", 0, 59, 32)
min_entry_time = time(entry_hour, entry_min)

# Hardcoded 0DTE as per strategy definition
target_dte = 0 

entry_window = st.sidebar.slider("Entry Window (Minutes)", 5, 120, 30)

exit_hour = st.sidebar.number_input("Exit Hour", 9, 15, 15)
exit_min = st.sidebar.number_input("Exit Minute", 0, 59, 20)
exit_time = time(exit_hour, exit_min)

st.sidebar.subheader("Cutoff Configuration")
max_entry_hour = st.sidebar.number_input("Max Entry Hour", 9, 15, 14, help="No new trades after this time")
max_entry_min = st.sidebar.number_input("Max Entry Minute", 0, 59, 45)
max_entry_time = time(max_entry_hour, max_entry_min)

st.sidebar.subheader("Stop Loss Settings")
sl_min = st.sidebar.number_input("Min SL Points", 1, 50, 10)
sl_max = st.sidebar.number_input("Max SL Points", 1, 100, 20)

st.sidebar.subheader("Trailing SL Settings")
trail_trigger = st.sidebar.number_input("Trigger Points (Move to Cost)", 5, 100, 20)
trail_step = st.sidebar.number_input("Trailing Step Points", 1, 50, 10)

st.sidebar.subheader("Strike Rolling")
rolling_step = st.sidebar.number_input("Rolling Step (pts)", 50, 500, def_roll_step)

portfolio_sl = st.sidebar.number_input("Max Portfolio SL (Points)", 0, 500, 70, help="Stop trading if daily loss exceeds this.")

st.sidebar.header("Financials & Slippage")
lot_size = st.sidebar.number_input("Lot Size (Multiplier)", 1, 100, 65 if target_index == "NIFTY" else 20)
trade_slippage = st.sidebar.number_input("Trade Slippage (Pts)", 0.0, 10.0, 0.0, step=0.5)

st.sidebar.subheader("Filter Results by Year")
# Using both multiselect and text input as requested
all_years = [2021, 2022, 2023, 2024, 2025, 2026]
selected_years = st.sidebar.multiselect("Select Years (Multi-select)", all_years, default=all_years)

year_text = st.sidebar.text_input("Type Year(s) (e.g. 2024, 2025)", help="If entered, this overrides the multi-select box.")

# Parsing Logic
filter_years = []
if year_text.strip():
    try:
        # Split by comma and clean
        parts = [y.strip() for y in year_text.split(',')]
        for p in parts:
            if p.isdigit() and len(p) == 4:
                filter_years.append(int(p))
    except:
        st.sidebar.error("Invalid year format.")
else:
    filter_years = selected_years

RESULTS_FILE = "backtest_results.csv"

def display_results(df):
    if df.empty:
        st.warning("No trades found in the results.")
        return

    # Clone and Apply Lot Size/Slippage
    df = df.copy()
    exec_types = ['Long Straddle', 'SL', 'EOD', 'Stop Loss', 'Trailing SL', 'Time Exit']
    mask = df['Type'].isin(exec_types)
    df.loc[mask, 'PnL'] = (df.loc[mask, 'PnL'] - trade_slippage) * lot_size
    
    # Ensure Date is datetime
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    # Calculate Detailed Metrics using utility
    daily_pnl = df.groupby('Date')['PnL'].sum().reset_index()
    daily_pnl['Cumulative PnL'] = daily_pnl['PnL'].cumsum()
    daily_pnl['Peak'] = daily_pnl['Cumulative PnL'].cummax()
    daily_pnl['Drawdown'] = daily_pnl['Cumulative PnL'] - daily_pnl['Peak']
    
    metrics_records = calculate_extensive_metrics(df, daily_pnl)
    metrics_df = pd.DataFrame(metrics_records)
    
    # Layout Stats (Top 4)
    total_pnl = daily_pnl['PnL'].sum()
    win_rate = metrics_records[3]['Value'] # Win Rate from calculated metrics
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total PnL (₹)", f"{total_pnl:,.2f}")
    col2.metric("Total Trades", len(df[mask]))
    col3.metric("Win Rate", win_rate)
    col4.metric("Avg PnL/Trade (₹)", f"{df.loc[mask, 'PnL'].mean():,.2f}")
    
    # Detailed Metrics Table
    with st.expander("📊 View Detailed Trading Metrics (30+ KPIs)", expanded=False):
        st.table(metrics_df)

    # Plots
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df['Cumulative_PnL'] = df['PnL'].cumsum()
    df['Drawdown'] = df['Cumulative_PnL'] - df['Cumulative_PnL'].cummax()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    # Equity
    ax1.plot(df['Date'], df['Cumulative_PnL'], label='Equity', color='green')
    ax1.set_title("Equity Curve")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Drawdown
    ax2.fill_between(df['Date'], df['Drawdown'], 0, color='red', alpha=0.3, label='Drawdown')
    ax2.set_ylabel("Drawdown")
    ax2.grid(True, alpha=0.3)
    
    st.pyplot(fig)
    
    # Data Table
    st.subheader("Trade Log")
    st.dataframe(df, width="stretch")

def monte_carlo_simulation(trades_df, n_sims=1000):
    if trades_df.empty: return None
    
    pnl_sequence = trades_df['PnL'].values
    sim_results = []
    
    for _ in range(n_sims):
        np.random.shuffle(pnl_sequence)
        sim_results.append(np.cumsum(pnl_sequence))
        
    return np.array(sim_results)

tab1, tab2, tab3 = st.tabs(["Backtest Results", "Single Day Analysis", "Advanced Analytics"])

with tab1:
    # Auto-load existing results
    if os.path.exists(RESULTS_FILE):
        st.success(f"Loaded existing results from {RESULTS_FILE}")
        try:
            existing_df = pd.read_csv(RESULTS_FILE)
            
            # Apply Year Filter
            existing_df['Date'] = pd.to_datetime(existing_df['Date'])
            if filter_years:
                existing_df = existing_df[existing_df['Date'].dt.year.isin(filter_years)]
            
            display_results(existing_df)
        except Exception as e:
            st.error(f"Error reading existing results: {e}")
    else:
        st.info("No existing results found. Run backtest to generate.")

    if st.button("Run New Backtest"):
        with st.spinner("Running Backtest... This may take a minute..."):
            # Execute Backtest
            # Execute Backtest
            # Execute Backtest
            if target_index == "NIFTY":
                import backtest_main
                import importlib
                importlib.reload(backtest_main)
                
                df = backtest_main.run_backtest(
                    min_entry_time=min_entry_time,
                    entry_window_mins=entry_window,
                    exit_time=exit_time,
                    sl_min_pts=sl_min,
                    sl_max_pts=sl_max,
                    trail_trigger=trail_trigger,
                    trail_step=trail_step,
                    rolling_step=rolling_step,
                    target_dte=target_dte,
                    portfolio_sl=portfolio_sl,
                    strategy_mode=STRATEGY_MODE,
                    spot_check_time=spot_check_time,
                    years=filter_years,
                    max_entry_time=max_entry_time
                )
            else:
                # Sensex
                import backtest_sensex
                import importlib
                importlib.reload(backtest_sensex)
                
                df = backtest_sensex.run_backtest(
                    min_entry_time=min_entry_time,
                    entry_window_mins=entry_window,
                    exit_time=exit_time,
                    sl_min_pts=sl_min,
                    sl_max_pts=sl_max,
                    trail_trigger=trail_trigger,
                    trail_step=trail_step,
                    rolling_step=rolling_step,
                    target_dte=target_dte,
                    portfolio_sl=portfolio_sl,
                    strategy_mode=STRATEGY_MODE,
                    spot_check_time=spot_check_time,
                    years=filter_years,
                    max_entry_time=max_entry_time
                )
                # Map PnL Value to PnL for dashboard compatibility
                if isinstance(df, tuple):
                    if not df[0].empty and 'PnL Value' in df[0].columns:
                        df[0]['PnL'] = df[0]['PnL Value']
                elif not df.empty and 'PnL Value' in df.columns:
                    df['PnL'] = df['PnL Value']
            
            # Unpack results (Tuple: df, daily_logs)
            if isinstance(df, tuple):
                df_trades, daily_logs = df
            else:
                df_trades = df
                daily_logs = []
            
            st.write(f"DEBUG: Backtest finished. captured logs: {len(daily_logs)}") # DEBUG
            
            # Persist Logs to File (More robust than Session State)
            import json
            LOGS_FILE = "backtest_logs.json"
            
            # Add Params to logs or separate? separate is fine.
            # actually, let's wrap it.
            full_data = {
                "params": {
                    "Strategy Mode": STRATEGY_MODE,
                    "Spot Check Time": str(spot_check_time),
                    "Trading Start Time": str(min_entry_time),
                    "Entry Window": f"{entry_window} mins",
                    "Exit Time": str(exit_time),
                    "Rolling Step": rolling_step,
                    "Portfolio SL": portfolio_sl,
                },
                "logs": daily_logs
            }
            
            try:
                # Convert dates to string for JSON serialization
                # daily_logs has 'Date' object (date).
                # rapid fix: serialize
                with open(LOGS_FILE, 'w') as f:
                     # Helper to serialize date
                     def date_handler(obj):
                        if hasattr(obj, 'isoformat'):
                            return obj.isoformat()
                        return str(obj)
                     json.dump(full_data, f, default=date_handler)
            except Exception as e:
                st.error(f"Failed to save logs: {e}")

            # Store in session state for Detailed Report (Backup)
            st.session_state['daily_logs'] = daily_logs
            
            if df_trades.empty:
                st.warning("No trades generated with these settings.")
            else:
                df_trades.to_csv(RESULTS_FILE, index=False)
                st.success("Backtest Completed! Results saved.")
                st.rerun() # Rerun to load from file and display properly

with tab2:
    st.subheader("Deep Dive into a Single Day")
    # Default to a known valid date from the recent data inspection
    target_date = st.date_input("Select Date", datetime.date(2024, 7, 22))
    
    if st.button("Analyze Day"):
        if target_index == "NIFTY":
            logs, day_df, daily_trades = backtest_main.run_day_analysis(
                target_date,
                min_entry_time=min_entry_time,
                entry_window_mins=entry_window,
                exit_time=exit_time,
                sl_min_pts=sl_min,
                sl_max_pts=sl_max,
                trail_trigger=trail_trigger,
                trail_step=trail_step,
                rolling_step=rolling_step,
                portfolio_sl=portfolio_sl,
                strategy_mode=STRATEGY_MODE,
                spot_check_time=spot_check_time,
                max_entry_time=max_entry_time
            )
        else:
             logs, day_df, daily_trades = backtest_sensex.run_day_analysis(
                target_date,
                min_entry_time=min_entry_time,
                entry_window_mins=entry_window,
                exit_time=exit_time,
                sl_min_pts=sl_min,
                sl_max_pts=sl_max,
                trail_trigger=trail_trigger,
                trail_step=trail_step,
                rolling_step=rolling_step,
                portfolio_sl=portfolio_sl,
                strategy_mode=STRATEGY_MODE,
                spot_check_time=spot_check_time,
                max_entry_time=max_entry_time
            )
        
        if day_df is not None and not day_df.empty:
            st.subheader("Price vs VWAP Chart")
            
            # Create interactive Logic Labels if available in day_df columns? 
            # Currently day_df has: Close, VWAP, RefMode, Strike
            
            fig_d, ax_d = plt.subplots(figsize=(12, 5))
            ax_d.plot(day_df.index, day_df['Close'], label=f'Straddle Price (Strike {day_df["Strike"].iloc[-1]})', color='blue')
            ax_d.plot(day_df.index, day_df['VWAP'], label='Ref VWAP', color='orange', linestyle='--')
            
            ax_d.set_title(f"Intraday Action: {target_date}")
            ax_d.legend(loc='upper left')
            ax_d.grid(True, alpha=0.3)
            st.pyplot(fig_d)
            
            # --- Event Parsing for Table ---
            event_data = []
            for log in logs:
                # Basic parsing based on keywords
                # Log format: [HH:MM:SS] MSG
                try:
                    parts = log.split("] ", 1)
                    if len(parts) == 2:
                        timestr = parts[0].replace("[", "")
                        msg = parts[1]
                        
                        category = "Info"
                        if "ENTRY" in msg: category = "Entry 🟢"
                        elif "EXIT" in msg or "SL HIT" in msg: category = "Exit 🔴"
                        elif "ROLL" in msg: category = "Roll 🔄"
                        elif "REFERENCE LINE" in msg: category = "Ref Line 📏"
                        elif "Entry Window" in msg: category = "Window ⏳"
                        
                        event_data.append({"Time": timestr, "Category": category, "Message": msg})
                except:
                    pass
            
            if event_data:
                st.subheader("Key Events")
                evt_df = pd.DataFrame(event_data)
                st.dataframe(evt_df, width="stretch")

            st.markdown("### Trade Data")
            st.dataframe(day_df)
        
        st.subheader("Raw Logs")
        log_text = "\n".join(logs)
        st.text_area("Full Calculation Log", log_text, height=300)

with tab3:
    st.header("Advanced Analytics")
    
    if os.path.exists(RESULTS_FILE):
        df = pd.read_csv(RESULTS_FILE)
        if not df.empty:
            
            # --- TOP ROW METRICS ---
            # Filter out "No Entry" / "Data Error" logs for statistics
            
            # Apply Year Filter to Analytics df too
            df['Date'] = pd.to_datetime(df['Date'])
            if filter_years:
                df = df[df['Date'].dt.year.isin(filter_years)]
            
            stats_df = df[~df['Type'].isin(['No Entry', 'Data Error'])]
            
            total_pnl = df['PnL'].sum() # Total PnL is same
            
            if not stats_df.empty:
                win_rate = (len(stats_df[stats_df['PnL'] > 0]) / len(stats_df)) * 100
                won_trades = stats_df[stats_df['PnL'] > 0]
                lost_trades = stats_df[stats_df['PnL'] <= 0]
                
                avg_win = won_trades['PnL'].mean() if not won_trades.empty else 0
                avg_loss = lost_trades['PnL'].mean() if not lost_trades.empty else 0
                profit_factor = abs(won_trades['PnL'].sum() / lost_trades['PnL'].sum()) if lost_trades['PnL'].sum() != 0 else float('inf')
                
                rr_ratio = abs(avg_win/avg_loss) if avg_loss != 0 else 0
            else:
                win_rate = 0
                profit_factor = 0
                rr_ratio = 0
                won_trades = []
                lost_trades = []
            
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Net PnL", f"₹ {total_pnl:.2f}", delta_color="normal")
            kpi2.metric("Win Rate", f"{win_rate:.1f}%", f"{len(won_trades)}W / {len(lost_trades)}L")
            kpi3.metric("Profit Factor", f"{profit_factor:.2f}")
            kpi4.metric("Risk:Reward", f"1:{rr_ratio:.2f}")
            
            # --- PLOTLY EQUITY CURVE ---
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            df['Cumulative PnL'] = df['PnL'].cumsum()
            df['Drawdown'] = df['Cumulative PnL'] - df['Cumulative PnL'].cummax()
            
            fig = px.line(df, x='Date', y='Cumulative PnL', title='Portfolio Equity Curve', template='plotly_dark')
            fig.add_scatter(x=df['Date'], y=df['Cumulative PnL'], fill='tozeroy', mode='lines', line=dict(color='#00D4FF'))
            st.plotly_chart(fig, width="stretch")
            
            # --- DRAWDOWN AREA ---
            fig_dd = px.area(df, x='Date', y='Drawdown', title='Drawdown Analysis', template='plotly_dark')
            fig_dd.update_traces(line_color='#FF4B4B', fillcolor='rgba(255, 75, 75, 0.3)')
            st.plotly_chart(fig_dd, width="stretch")
            
            # --- MONTE CARLO ---
            st.subheader("Monte Carlo Simulation (1000 Runs)")
            if st.button("Run Simulation"):
                with st.spinner("Simulating..."):
                    sims = monte_carlo_simulation(df)
                    if sims is not None:
                        # Plot Cloud
                        fig_mc = go.Figure()
                        
                        # Plot random subset of paths
                        for i in range(min(50, len(sims))):
                             fig_mc.add_trace(go.Scatter(y=sims[i], mode='lines', line=dict(color='gray', width=0.5), opacity=0.3, showlegend=False))
                        
                        # Median
                        median_equity = np.median(sims, axis=0)
                        fig_mc.add_trace(go.Scatter(y=median_equity, mode='lines', name='Median', line=dict(color='yellow', width=2)))
                        
                        # Actual
                        fig_mc.add_trace(go.Scatter(y=df['Cumulative PnL'].values, mode='lines', name='Actual', line=dict(color='#00D4FF', width=3)))

                        fig_mc.update_layout(title="Equity Cloud", template="plotly_dark", xaxis_title="Trade Count", yaxis_title="PnL")
                        st.plotly_chart(fig_mc, width="stretch")
            
            # --- PERIOD ANALYSIS ---
            st.markdown("### Monthly Performance")
            df['Year'] = df['Date'].dt.year
            df['Month'] = df['Date'].dt.strftime('%b')
            monthly = df.groupby(['Year', 'Month'])['PnL'].sum().reset_index()
            # Pivot for Heatmap-like table?
            pivot_table = monthly.pivot(index='Year', columns='Month', values='PnL').fillna(0)
            # Reorder months
            month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            pivot_table = pivot_table.reindex(columns=month_order)
            
            st.dataframe(pivot_table.style.background_gradient(cmap='RdYlGn', axis=None), width="stretch")
            
            # --- DETAILED TRADE LOG ---
            st.markdown("### Detailed Trade Log")
            st.dataframe(df, width="stretch")
            
            # Download Button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Report (CSV)",
                csv,
                "fintech_report.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("No data available.")
    else:
        st.warning("Run a backtest first to unlock analytics.")

with tab3:
    st.header("Advanced Analytics & Reports")
    
    # Check for Logs File
    import json
    import os
    LOGS_FILE = "backtest_logs.json"
    has_logs = os.path.exists(LOGS_FILE)
    
    if has_logs:
        st.subheader("Professional Backtest Report")
        st.markdown("Download the full multi-sheet Excel report with detailed trade logs, interactive charts, and 30+ metrics.")
        
        if st.button("Generate Enhanced Excel Report 📊"):
            with st.spinner("Generating Report..."):
                try:
                    # Load Trades and Logs
                    if os.path.exists(RESULTS_FILE):
                        current_trades = pd.read_csv(RESULTS_FILE)
                        with open(LOGS_FILE, 'r') as f:
                            full_data = json.load(f)
                        
                        logs_data = full_data.get('logs', [])
                        params_data = full_data.get('params', {})
                        
                        # Add dynamic lot size and slippage to params
                        params_data['Applied Lot Size'] = lot_size
                        params_data['Applied Slippage'] = trade_slippage
                        
                        # Output path
                        tmp_report = "Strategy_Detailed_Report.xlsx"
                        generate_variant_report(tmp_report, current_trades, params_data, daily_summaries=logs_data, lot_size=lot_size, slippage=trade_slippage)
                        
                        with open(tmp_report, "rb") as file:
                            st.download_button(
                                label="Download Detailed Excel 📥",
                                data=file,
                                file_name="Strategy_Backtest_Report.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error("No trade data found to generate report.")
                except Exception as e:
                    st.error(f"Error generating report: {e}")
    else:
        st.info("Run a backtest first to generate the detailed report.")
        # Debug info
        if 'daily_logs' in st.session_state:
             st.write(f"DEBUG: Session has {len(st.session_state['daily_logs'])} logs but file {LOGS_FILE} not found.")

    # Existing Analytics Content (if any, moved below)
