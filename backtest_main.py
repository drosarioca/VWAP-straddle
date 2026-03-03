
import pandas as pd
import numpy as np
from datetime import time, timedelta, datetime
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))
from options_loader import OptionsLoader


# --- CONFIGURATION ---
DATA_YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
# BASE_PATH = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\new-data-download"
BASE_PATH = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\new-data-download" # Adjusted based on latest interaction
NIFTY_PATHS = [os.path.join(BASE_PATH, f"NIFTY-{year}-1min-options-data") for year in DATA_YEARS]
INDEX_DATA_PATH = r"C:\Users\Rosario\Desktop\vwap-backtesting-platform-revamped\NIFTY-index-data"
ICHARTS_DIR = r"C:\Users\Rosario\.gemini\antigravity\scratch\quant_trading\icharts_download"

MIN_ENTRY_TIME = time(9, 34)
ENTRY_WINDOW_MINS = 20 # New variable
EXIT_TIME = time(15, 20) # Updated exit time

# Logic Variables (Constants)
TRAIL_TRIGGER_1 = 20 # Points profit to move SL to cost
TRAIL_STEP = 10      # Points to trail further

class IChartsDataManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.file_map = {} # (expiry_date, strike) -> filepath
        self.available_expiries = set()
        self._scan_files()

    def _scan_files(self):
        # Filename format: NIFTY_DDMMMYY_STRIKE_Straddle.csv
        # Example: NIFTY_01AUG24_23000_Straddle.csv
        cnt = 0
        if not os.path.exists(self.data_dir):
            print(f"Warning: {self.data_dir} does not exist.")
            return
        
        # files = os.listdir(self.data_dir)
        # print(f"Found {len(files)} total files in {self.data_dir}")

        cnt = 0
        for fname in os.listdir(self.data_dir):
            if fname.endswith("-straddle-data.csv") and fname.startswith("NIFTY-"):
                try:
                    # New Format: NIFTY-YYYY-MM-DD-DDMMMYY-STRIKE-straddle-data.csv
                    # Example: NIFTY-2026-03-02-02MAR26-24000-straddle-data.csv
                    parts = fname.split("-")
                    # parts[0] = NIFTY
                    # parts[1..3] = Y, M, D
                    # parts[4] = DDMMMYY (Expiry)
                    # parts[5] = STRIKE
                    
                    expiry_str = parts[4]
                    strike_str = parts[5]
                    
                    expiry_date = datetime.strptime(expiry_str, "%d%b%y").date()
                    strike = int(strike_str)
                    
                    self.file_map[(expiry_date, strike)] = os.path.join(self.data_dir, fname)
                    self.available_expiries.add(expiry_date)
                    cnt += 1
                except Exception as e:
                    pass
            elif fname.endswith("_Straddle.csv") and fname.startswith("NIFTY_"):
                try:
                    parts = fname.split("_")
                    expiry_str = parts[1]
                    strike_str = parts[2]
                    expiry_date = datetime.strptime(expiry_str, "%d%b%y").date()
                    strike = int(strike_str)
                    self.file_map[(expiry_date, strike)] = os.path.join(self.data_dir, fname)
                    self.available_expiries.add(expiry_date)
                    cnt += 1
                except:
                    pass
        print(f"Indexed {cnt} iCharts straddle files.")
        self.sorted_expiries = sorted(list(self.available_expiries))

    def get_nearest_expiry(self, target_date):
        for exp in self.sorted_expiries:
            if exp >= target_date:
                return exp
        return None

    def load_straddle(self, trading_date, strike):
        expiry = self.get_nearest_expiry(trading_date)
        if not expiry:
            return None
            
        fpath = self.file_map.get((expiry, strike))
        if not fpath:
            return None
            
        try:
            df = pd.read_csv(fpath)
            
            # 1. Datetime Construction
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            elif 'date' in df.columns and 'time' in df.columns:
                df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
            else:
                raise KeyError("File must contain 'datetime' or 'date'+'time' columns")

            df['datetime'] = df['datetime'].dt.floor('min')
            
            # Filter for trading date
            df = df[df['datetime'].dt.date == trading_date].copy()
            if df.empty:
                return None
                
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
            
            # 2. Normalize columns: Rename columns to Title Case for compatibility
            # Handle "earlier format": LTP, volume, vwap
            if 'LTP' in df.columns:
                df['Close'] = df['LTP']
                df['Open'] = df['LTP']
                df['High'] = df['LTP']
                df['Low'] = df['LTP']
            else:
                df.rename(columns={
                    'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
                }, inplace=True)
            
            if 'Volume' not in df.columns and 'volume' in df.columns:
                df['Volume'] = df['volume']

            # 3. Calculate/Map VWAP - ALWAYS CALCULATE INTRADAY VWAP
            # We ignore pre-calculated 'vwap' column because it might be cumulative across multiple days
            if 'Close' in df.columns and 'Volume' in df.columns:
                # Intraday VWAP starts from 09:16 (Market opens at 9:15)
                # But some data starts slightly later. We just sum everything for THIS day.
                # Since we already filtered 'df' for 'trading_date' at line 114, 
                # a simple cumsum on this filtered df gives the correct intraday VWAP.
                df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
            elif 'vwap' in df.columns:
                # Fallback only if Volume is missing (unlikely for straddles)
                df['VWAP'] = df['vwap']
            
            return df
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            return None

# Global Loader Instance
icharts_loader = None


# ... (Loader functions remain same) ...


# --- HELPER FUNCTIONS ---

def get_nifty_spot_file(date_obj):
    # Format: NIFTY-1minute-data-YYYY-MM-DD.csv
    date_str = date_obj.strftime("%Y-%m-%d")
    fname = f"NIFTY-1minute-data-{date_str}.csv"
    path = os.path.join(INDEX_DATA_PATH, fname)
    if os.path.exists(path):
        return path
    return None

def get_atm_strike_at_time(date_obj, time_obj, loader):
    """
    Finds ATM strike by reading NIFTY Spot data closing price at specific time.
    """
    fpath = get_nifty_spot_file(date_obj)
    if not fpath:
        # print(f"Index data missing for {date_obj}")
        return None
    
    try:
        # Load CSV. All inspected files have a header: date,time,open,high,low,close
        df = pd.read_csv(fpath)
        
        # Normalize columns: strip spaces, lowercase
        df.columns = [c.strip().lower() for c in df.columns]
        
        target_time = time_obj.strftime("%H:%M")
        
        # Filter by time. 
        # Column 'time' usually has HH:MM:SS, target is HH:MM
        # We search for contains or startswith
        if 'time' not in df.columns or 'close' not in df.columns:
            # Fallback if header is totally different? Unlikely based on inspection.
            print(f"Unexpected columns in {fpath}: {df.columns}")
            return None

        row = df[df['time'].astype(str).str.startswith(target_time)]
        
        if row.empty:
            return None
            
        close_price = float(row.iloc[0]['close'])
        return round(close_price / 50) * 50
    except Exception as e:
        print(f"Error getting ATM from {fpath}: {e}")
        return None

def load_precalculated_straddle(target_date, strike):
    """
    Tries to load pre-calculated straddle data from the user's desktop folder structure.
    Returns DataFrame or None.
    """
    try:
        year = target_date.year
        # Search Pattern: NIFTY-{Year}-straddle-data / NIFTY-{YYYY}-{MM}-{DD}-*-{STRIKE}-straddle-data.csv
        # Example: NIFTY-2025-02-20-20FEB25-22850-straddle-data.csv
        
        date_str = target_date.strftime("%Y-%m-%d")
        search_pattern = os.path.join(
            STRADDLE_ROOT, 
            f"NIFTY-{year}-straddle-data", 
            f"NIFTY-{date_str}-*-{strike}-straddle-data.csv"
        )
        
        files = glob(search_pattern)
        if not files:
            return None
            
        # Use first match
        file_path = files[0]
        df = pd.read_csv(file_path)
        
        # Parse Columns
        # Expected: date,time,LTP,volume,vwap,sd
        
        # 1. Datetime Construction
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        elif 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
        else:
            raise KeyError("File must contain 'datetime' or 'date'+'time' columns")

        df['datetime'] = df['datetime'].dt.floor('min') # Align to 00 seconds
        df.set_index('datetime', inplace=True)
        
        # 2. Map Columns
        # Use LTP as Close. Since OHLC is missing, set Open=High=Low=Close=LTP
        df['Close'] = df['LTP']
        df['Open'] = df['LTP']
        df['High'] = df['LTP']
        df['Low'] = df['LTP']
        
        if 'vwap' in df.columns:
            df['VWAP'] = df['vwap']
        else:
            # Fallback calc if missing (unlikely based on file checks)
            df['VWAP'] = (df['Close'] * df['volume']).cumsum() / df['volume'].cumsum()
            
        return df[['Open', 'High', 'Low', 'Close', 'VWAP']]
        
    except Exception as e:
        print(f"Error loading straddle {target_date} {strike}: {e}")
        return None

def construct_straddle(date_obj, strike):
    """
    Retrieves straddle OHLCV dataframe from iCharts loader.
    """
    global icharts_loader
    if icharts_loader is None:
        icharts_loader = IChartsDataManager(ICHARTS_DIR)
        
    return icharts_loader.load_straddle(date_obj, strike)


def run_backtest(
    min_entry_time=time(9, 34),
    spot_check_time=None, # New param
    entry_window_mins=30,

    exit_time=time(15, 20),
    sl_min_pts=10,
    sl_max_pts=20,
    trail_trigger=20,
    trail_step=10,
    rolling_step=80,
    target_dte=0,
    portfolio_sl=70,
    strategy_mode="NON_ROLLING", # "NON_ROLLING" or "ROLLING_VWAP"
    years=None, # New param for Crosswalk
    max_entry_time=time(14, 45)
):
    # Default spot_check_time if not provided
    if spot_check_time is None:
        spot_check_time = min_entry_time
    global icharts_loader
    icharts_loader = IChartsDataManager(ICHARTS_DIR)
    
    # Determined Active Years
    active_years = years if years is not None else DATA_YEARS

    # 1. Get List of Trading Dates from Index Data
    spot_files = os.listdir(INDEX_DATA_PATH)
    dates = []
    for f in spot_files:
        if f.startswith("NIFTY-1minute-data-") and f.endswith(".csv"):
             # extract date
             ds = f.replace("NIFTY-1minute-data-", "").replace(".csv", "")
             try:
                 d = datetime.strptime(ds, "%Y-%m-%d").date()
                 if d.year in active_years:
                     dates.append(d)
             except: pass
             
    dates = sorted(dates)
    results = []
    daily_summaries = []
    
    print(f"Running backtest on {len(dates)} days...")
    
    print(f"Running backtest on {len(dates)} days... (Target DTE: {target_dte})")
    
    for d in dates:
        # DTE Filter
        nearest_expiry = icharts_loader.get_nearest_expiry(d)
        if not nearest_expiry: continue
        
        actual_dte = (nearest_expiry - d).days
        if actual_dte != target_dte:
            continue

        # Run daily logic
        logs, df, daily_trades = run_day_analysis(
            d, min_entry_time, entry_window_mins, exit_time, 
            sl_min_pts, sl_max_pts, trail_trigger, trail_step, rolling_step,
            portfolio_sl, strategy_mode, spot_check_time, max_entry_time
        )
        
        # Aggregate Structured Trades
        for t in daily_trades:
            t['Date'] = d
            t['DTE'] = actual_dte # Inject DTE into trade records
            results.append(t)
            
        # Collect Daily Summary for Detailed Report
        day_pnl = sum(t.get('PnL', 0) for t in daily_trades)
        day_type = "No Trade Day"
        if daily_trades:
            has_sl = any(t.get('Type') in ['SL', 'Stop Loss', 'Trailing SL'] for t in daily_trades)
            has_eod = any(t.get('Type') in ['EOD', 'Time Exit'] for t in daily_trades)
            is_no_entry = all(t.get('Type') == 'No Entry' or t.get('Type') == 'Data Error' for t in daily_trades)
            
            if is_no_entry:
                day_type = "No Trade Day"
                if any(t.get('Type') == 'Data Error' for t in daily_trades): day_type = "Data Error"
            elif has_sl:
                day_type = "SL Day"
            elif has_eod:
                day_type = "EOD Day"
            else:
                day_type = "Active"
                
        daily_summaries.append({
            "Date": d,
            "Day Type": day_type,
            "PnL": day_pnl,
            "Detailed Events": "\n".join(logs)
        })

    if results:
        # Convert to DataFrame
        res_df = pd.DataFrame(results)
        # Reorder columns for readability
        cols = ['Date', 'DTE', 'PnL', 'Type', 'Entry Time', 'Entry Price', 'Exit Time', 'Exit Price', 'Strike', 'Reason', 'Migrated']
        # Only select cols that exist
        final_cols = [c for c in cols if c in res_df.columns]
        return res_df[final_cols], daily_summaries
    return pd.DataFrame(columns=['Date', 'Type', 'PnL']), daily_summaries


# --- HELPER: Load Index Data ---
def load_index_data(date_obj):
    fpath = get_nifty_spot_file(date_obj)
    if not fpath: return None
    try:
        df = pd.read_csv(fpath)
        df.columns = [c.strip().lower() for c in df.columns]
        
        if 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time']) 
        elif 'time' in df.columns:
             df['datetime'] = pd.to_datetime(date_obj.strftime("%Y-%m-%d") + ' ' + df['time'])
        
        df.set_index('datetime', inplace=True)
        return df
    except Exception as e:
        print(f"Error loading index {fpath}: {e}")
        return None

def run_day_analysis(
    target_date,
    min_entry_time=time(9, 34),
    entry_window_mins=30,
    exit_time=time(15, 20),
    sl_min_pts=10,
    sl_max_pts=20,
    trail_trigger=20,
    trail_step=10,
    rolling_step=100,
    portfolio_sl=50,
    strategy_mode="NON_ROLLING",
    spot_check_time=None,
    max_entry_time=time(14, 45)
):
    if spot_check_time is None:
        spot_check_time = min_entry_time
    # loader = OptionsLoader(NIFTY_PATHS) # Not used
    logs = []
    trades = []
    current_trade = None
    
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        
    logs.append(f"Analyzing {target_date}...")
    
    # 1. Load Spot Data
    spot_df = load_index_data(target_date)
    if spot_df is None or spot_df.empty:
        logs.append("No Index Data found.")
    if spot_df is None or spot_df.empty:
        logs.append("No Index Data found.")
        return logs, None, [{
            'Date': target_date,
            'Type': 'Data Error',
            'PnL': 0.0,
            'Reason': 'No Index Data',
            'Strike': 0,
            'Entry Time': None, 'Exit Time': None, 'Entry Price': 0, 'Exit Price': 0, 'Migrated': False
        }]
        
    # 2. Initial ATM Strike
    # Use spot_check_time for initial determination
    spot_check_dt = datetime.combine(target_date, spot_check_time)
    
    # We need to find the spot row at or after spot_check_dt
    if spot_check_dt not in spot_df.index:
        temp = spot_df[spot_df.index >= spot_check_dt]
        if temp.empty: 
            logs.append("Index data ends before spot check time.")
            return logs, None, [{
                'Date': target_date,
                'Type': 'Data Error',
                'PnL': 0.0,
                'Reason': 'Index Data Partial',
                'Strike': 0,
                'Entry Time': None, 'Exit Time': None, 'Entry Price': 0, 'Exit Price': 0, 'Migrated': False
            }]
        start_row = temp.iloc[0]
        # We don't change spot_check_dt here, just use the row found
    else:
        start_row = spot_df.loc[spot_check_dt]
        
    initial_spot = float(start_row['close'])
    current_strike = round(initial_spot / 50) * 50
    logs.append(f"Initial Spot: {initial_spot} (at {spot_check_time}). Initial ATM: {current_strike}")
    
    # Define Trading Start Time
    trading_start_dt = datetime.combine(target_date, min_entry_time)
    
    # 3. Setup Loop
    current_straddle = construct_straddle(target_date, current_strike)
    if current_straddle is None:
        logs.append(f"No Straddle Data for {current_strike}")
    if current_straddle is None:
        logs.append(f"No Straddle Data for {current_strike}")
        return logs, None, [{
            'Date': target_date,
            'Type': 'Data Error',
            'PnL': 0.0,
            'Reason': f"Missing Straddle {current_strike}",
            'Strike': current_strike,
            'Entry Time': None, 'Exit Time': None, 'Entry Price': 0, 'Exit Price': 0, 'Migrated': False
        }]

    # Reference Logic State
    is_rolled = False
    fixed_vwap_level = None
    
    in_position = False
    entry_price = 0.0
    sl_price = 0.0
    sl_moved_to_cost = False
    last_trail_milestone = 0
    trade_pnl = 0.0
    
    day_records = []
    market_start = datetime.combine(target_date, time(9, 15))
    spot_iter = spot_df[spot_df.index >= market_start].sort_index()
    max_entry_dt = datetime.combine(target_date, min_entry_time) + timedelta(minutes=entry_window_mins)
    
    straddle_cache = {current_strike: current_straddle}
    
    # Dynamic Entry Window
    # Window starts from Trading Start Time
    entry_window_end = trading_start_dt + timedelta(minutes=entry_window_mins)
    
    for curr_time, row in spot_iter.iterrows():
        spot_close = row['close']
        
        # --- ROLLING CHECK ---
        # Only check rolling if NOT in a trade AND time >= min_entry_time
        # User Fix: "Intially spot has to idetified at 934(entry time) only there after rolling should work"
        if not in_position and curr_time.time() >= min_entry_time:
            diff = spot_close - current_strike
            
            roll_needed = False
            new_strike = current_strike
            
            if diff >= rolling_step:
                new_strike = int(round((current_strike + rolling_step) / 50) * 50)
                roll_needed = True
            elif diff <= -rolling_step:
                new_strike = int(round((current_strike - rolling_step) / 50) * 50)
                roll_needed = True
            
            if roll_needed:
                logs.append(f"[{curr_time.time()}] SPOT ROLL TRIGGER. Spot {spot_close} vs Strike {current_strike} (Diff {diff:.2f}). Rolling to {new_strike}")
                
                # Reset Entry Window on Roll - REMOVED per user constraint
                # Rule: "Mere strike rolling is not considered as entry... if no entry in window, then no entry full day"
                # Window is only defined by Start Time or SL Hit Time.
                logs.append(f"[{curr_time.time()}] ℹ️ Spot Roll Triggered. (Window NOT extended, remains {entry_window_end.time()})")
                
                if new_strike not in straddle_cache:
                    s_df = construct_straddle(target_date, new_strike)
                    straddle_cache[new_strike] = s_df
                
                if straddle_cache[new_strike] is not None:
                    current_strike = new_strike
                    current_straddle = straddle_cache[new_strike]
                    is_rolled = True
                    
                    # Calculate Reference Level (Min Low of history from 9:16 to Now)
                    # Note: User mentioned "low of that straddle". We use available history.
                    valid_hist = current_straddle[(current_straddle.index.time >= time(9, 16)) & (current_straddle.index <= curr_time)]
                    if not valid_hist.empty:
                        fixed_vwap_level = valid_hist['Low'].min()
                        logs.append(f"[{curr_time.time()}] 📏 NEW REFERENCE LINE SET: {fixed_vwap_level}")
                        logs.append(f"    (Calculated as Min Low of {new_strike} Straddle from 09:16 to {curr_time.time()})")
                    else:
                        fixed_vwap_level = None
                        logs.append(f"[{curr_time.time()}] ⚠️ No history for {new_strike} to set Reference Line.")
                else:
                    logs.append(f"[{curr_time.time()}] ❌ FAILED TO LOAD NEW STRIKE {new_strike}. Staying on {current_strike}")

        # --- PROCESS CANDLE ---
        if curr_time not in current_straddle.index:
            tick_data = {'Close': np.nan, 'VWAP': np.nan}
        else:
            s_row = current_straddle.loc[curr_time]
            vwap_val = fixed_vwap_level if is_rolled and fixed_vwap_level else s_row['VWAP']
            tick_data = {
                'Close': s_row['Close'],
                'VWAP': vwap_val,
                'RefMode': 'Fixed' if is_rolled else 'Dynamic',
                'Strike': current_strike
            }
            
            # --- STRATEGY LOGIC ---
            if in_position:
                current_profit = entry_price - s_row['Close']
                
                if not sl_moved_to_cost and current_profit >= trail_trigger:
                    sl_price = entry_price
                    sl_moved_to_cost = True
                    logs.append(f"[{curr_time.time()}] Profit {current_profit:.2f}. SL to Cost.")
                
                if sl_moved_to_cost:
                    add_prof = current_profit - trail_trigger
                    if add_prof >= 10:
                        steps = int(add_prof // trail_step)
                        if steps > last_trail_milestone:
                            new_sl = entry_price - (steps * trail_step)
                            if new_sl < sl_price:
                                sl_price = new_sl
                                last_trail_milestone = steps
                                logs.append(f"[{curr_time.time()}] Trailing Step {steps}. New SL: {sl_price:.2f}")

                if s_row['Close'] >= sl_price:
                    pnl = entry_price - s_row['Close']
                    trade_pnl += pnl
                    logs.append(f"[{curr_time.time()}] SL HIT. PnL: {pnl:.2f}")
                    in_position = False
                    
                    if current_trade:
                        current_trade['Exit Time'] = curr_time.time()
                        current_trade['Exit Price'] = s_row['Close']
                        current_trade['PnL'] = pnl
                        current_trade['Type'] = 'SL'
                        current_trade['Reason'] = 'Stop Loss' if not sl_moved_to_cost else 'Trailing SL'
                        trades.append(current_trade)
                        current_trade = None
                    
                    
                    # Reset Entry Window on Exit
                    entry_window_end = curr_time + timedelta(minutes=entry_window_mins)
                    logs.append(f"[{curr_time.time()}] Trade Exit. Window extended to {entry_window_end.time()}")

                    # --- CRITICAL UPDATE FOR ROLLING_VWAP MODE ---
                    if strategy_mode == "ROLLING_VWAP":
                        # After SL Hit, update Filter to Lowest Low of THIS straddle (09:16 to Now)
                        valid_hist = current_straddle[(current_straddle.index.time >= time(9, 16)) & (current_straddle.index <= curr_time)]
                        if not valid_hist.empty:
                            fixed_vwap_level = valid_hist['Low'].min()
                            logs.append(f"[{curr_time.time()}] 📉 SL Hit (Rolling Mode). Filter Updated vs Lowest Low: {fixed_vwap_level}")
                        else:
                            logs.append(f"[{curr_time.time()}] ⚠️ No history to update Rolling Filter.")
                
                elif curr_time.time() >= exit_time:
                    pnl = entry_price - s_row['Close']
                    trade_pnl += pnl
                    logs.append(f"[{curr_time.time()}] TIME EXIT. PnL: {pnl:.2f}")
                    in_position = False
                    
                    if current_trade:
                        current_trade['Exit Time'] = curr_time.time()
                        current_trade['Exit Price'] = s_row['Close']
                        current_trade['PnL'] = pnl
                        current_trade['Type'] = 'EOD'
                        current_trade['Reason'] = 'Time Exit'
                        trades.append(current_trade)
                        current_trade = None
                    
            elif not in_position:
                # Portfolio SL Check
                if (portfolio_sl > 0) and (trade_pnl <= -portfolio_sl):
                    # Daily Stop Hit
                    # Only log once if needed, or just pass
                    # But we iterate every minute, so we will spam logs if we are not careful.
                    # We can assume if we are not in position and reached max loss, we just break or pass.
                    # Let's break to save time, but we need to record data?
                    # "fill" remainder with empty? No, just continue to record tick data but no trades.
                    pass
                
                # Entry Logic
                # Must be within dynamic window AND after start time
                elif curr_time > entry_window_end:
                     # Just continue monitoring spot, no entry allowed
                     pass 
                elif curr_time.time() > max_entry_time:
                     # Past max entry time - no entry allowed
                     pass
                elif curr_time < trading_start_dt:
                    pass
                else:
                    # Check Entry Conditions
                    idx_loc = current_straddle.index.get_loc(curr_time) if curr_time in current_straddle.index else -1
                    if idx_loc >= 5:
                        grp_a = current_straddle.iloc[idx_loc-5 : idx_loc-2]
                        grp_b = current_straddle.iloc[idx_loc-2 : idx_loc+1]
                        
                        if strategy_mode == "ROLLING_VWAP":
                            # In Rolling Mode, if fixed_vwap_level is set (by Roll OR by SL), use it.
                            # Initially it is None (using Real VWAP).
                            ref_line = fixed_vwap_level
                        else:
                            # Standard Non-Rolling Mode: Only use Fixed line if Rolled.
                            ref_line = fixed_vwap_level if is_rolled and fixed_vwap_level else None
                        
                        def check_under(series, vwap_series, fixed_val):
                            if fixed_val is not None:
                                return (series < fixed_val).all()
                            return (series < vwap_series).all()

                        cond1 = check_under(grp_a['Close'], grp_a['VWAP'], ref_line)
                        cond2 = check_under(grp_b['Close'], grp_b['VWAP'], ref_line)
                        
                        cond1 = check_under(grp_a['Close'], grp_a['VWAP'], ref_line)
                        cond2 = check_under(grp_b['Close'], grp_b['VWAP'], ref_line)
                        
                        # Modified: Use Minimum LOW of Group A as Reference
                        low_a = grp_a['Low'].min()
                        # Condition: Low(Group A) > Close(3rd Candle of Group B)
                        # Equivalent to: Close(3rd Candle of B) < Low(Group A)
                        cond3 = s_row['Close'] < low_a
                        
                        if cond1 and cond2 and cond3:
                            entry_price = s_row['Close']
                            high_a = grp_a['High'].max()
                            calc_sl = high_a - entry_price
                            real_sl = max(sl_min_pts, min(calc_sl, sl_max_pts))
                            sl_price = entry_price + real_sl
                            in_position = True
                            sl_moved_to_cost = False
                            last_trail_milestone = 0
                            logs.append(f"[{curr_time.time()}] ENTRY ({current_strike}). Price: {entry_price:.2f}. SL: {sl_price:.2f}")
                            
                            current_trade = {
                                'Date': target_date,
                                'Strike': current_strike,
                                'Entry Time': curr_time.time(),
                                'Entry Price': entry_price,
                                'Type': 'Long Straddle', # Or Short? Strategy seems to be Shorting based on "Profit = Entry - Close"
                                'Migrated': is_rolled # If we rolled BEFORE entry
                            }


        day_records.append(tick_data)
        if curr_time.time() >= exit_time:
             if in_position and current_trade:
                 # Force close at EOD if not already
                 pnl = entry_price - row['close'] # Use SPOT? No, use straddle close
                 # But we might not have straddle row if out of index?
                 # Handled by prev block generally.
                 pass
             break
             
    df_res = pd.DataFrame(day_records, index=spot_iter[spot_iter.index <= curr_time].index)
    
    # If no trades occurred by EOD, record "No Entry"
    if not trades:
        trades.append({
            'Date': target_date,
            'Type': 'No Entry',
            'PnL': 0.0,
            'Reason': 'Conditions Not Met',
            'Strike': current_strike,
            'Entry Time': None, 'Exit Time': None, 'Entry Price': 0, 'Exit Price': 0, 'Migrated': False
        })
        
    return logs, df_res, trades

if __name__ == "__main__":
    result = run_backtest()
    
    # Handle Tuple Return
    if isinstance(result, tuple):
        df, daily_summaries = result
    else:
        df = result
        
    if not df.empty:
        print("\n--- Backtest Results ---")
        print(f"Total PnL: {df['PnL'].sum():.2f}")
        print(df)
        df.to_csv("backtest_results.csv")
    else:
        print("No trades generated.")
