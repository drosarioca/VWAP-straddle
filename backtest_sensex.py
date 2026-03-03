
import pandas as pd
import numpy as np
from datetime import time, timedelta, datetime
import os
import sys

# --- CONFIGURATION ---
# Sensex Specifics
LOT_SIZE = 20
STRIKE_INTERVAL = 100
DATA_YEARS = [2024, 2025, 2026]

# Paths
BASE_DIR = os.getcwd()
INDEX_DATA_PATH = os.path.join(BASE_DIR, "sensex_index_data")
ICHARTS_DIR = os.path.join(BASE_DIR, "sensex_straddle_download")

class IChartsDataManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.file_map = {} # (expiry_date, strike) -> filepath
        self.available_expiries = set()
        self._scan_files()

    def _scan_files(self):
        # Filename format: SENSEX_DDMMMYY_STRIKE_Straddle.csv
        print(f"Scanning Sensex data in {self.data_dir}...")
        if not os.path.exists(self.data_dir):
            print(f"Warning: {self.data_dir} does not exist.")
            return

        cnt = 0
        for fname in os.listdir(self.data_dir):
            if fname.endswith("_Straddle.csv") and fname.startswith("SENSEX_"):
                try:
                    parts = fname.split("_")
                    # parts[0] = SENSEX
                    # parts[1] = DDMMMYY (Expiry)
                    # parts[2] = STRIKE
                    
                    expiry_str = parts[1]
                    strike_str = parts[2]
                    
                    expiry_date = datetime.strptime(expiry_str, "%d%b%y").date()
                    strike = int(strike_str)
                    
                    self.file_map[(expiry_date, strike)] = os.path.join(self.data_dir, fname)
                    self.available_expiries.add(expiry_date)
                    cnt += 1
                except Exception as e:
                    pass
        print(f"Indexed {cnt} Sensex straddle files.")
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
            
            # Format: timestamp,open,high,low,close,volume,datetime
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            elif 'timestamp' in df.columns:
                 df['datetime'] = pd.to_datetime(df['timestamp'], unit='s') + timedelta(minutes=330)
            
            df['datetime'] = df['datetime'].dt.floor('min')
            
            # Filter for trading date
            df = df[df['datetime'].dt.date == trading_date].copy()
            
            if df.empty:
                return None
                
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
            
            # Normalize Columns
            df.rename(columns={
                'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
            }, inplace=True)
            
            # Calculate VWAP
            df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
            
            return df
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            return None

# Global Loader Instance
icharts_loader = None

# --- HELPER FUNCTIONS ---

def get_sensex_spot_file(date_obj):
    # Format: SENSEX-1minute-data-YYYY-MM-DD.csv
    date_str = date_obj.strftime("%Y-%m-%d")
    fname = f"SENSEX-1minute-data-{date_str}.csv"
    path = os.path.join(INDEX_DATA_PATH, fname)
    if os.path.exists(path):
        return path
    return None

def construct_straddle(date_obj, strike):
    global icharts_loader
    if icharts_loader is None:
        icharts_loader = IChartsDataManager(ICHARTS_DIR)
    return icharts_loader.load_straddle(date_obj, strike)

def run_backtest(
    min_entry_time=time(9, 34),
    entry_window_mins=30,
    exit_time=time(15, 20),
    sl_min_pts=10,
    sl_max_pts=20,
    trail_trigger=20,
    trail_step=10,
    rolling_step=100, # Increased default for Sensex? Or keep 100?
    target_dte=0,
    portfolio_sl=70,  # Points?
    strategy_mode="NON_ROLLING",
    spot_check_time=None,
    years=None,
    max_entry_time=time(14, 45)
):
    if spot_check_time is None:
        spot_check_time = time(9, 15)
        
    global icharts_loader
    icharts_loader = IChartsDataManager(ICHARTS_DIR)
    
    active_years = years if years else DATA_YEARS

    # 1. Get List of Trading Dates
    spot_files = os.listdir(INDEX_DATA_PATH)
    dates = []
    for f in spot_files:
        if f.startswith("SENSEX-1minute-data-") and f.endswith(".csv"):
             ds = f.replace("SENSEX-1minute-data-", "").replace(".csv", "")
             try:
                 d = datetime.strptime(ds, "%Y-%m-%d").date()
                 if d.year in active_years:
                     dates.append(d)
             except: pass
             
    dates = sorted(dates)
    results = []
    daily_summaries = []
    
    print(f"Running SENSEX backtest on {len(dates)} days... (Target DTE: {target_dte})")
    
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
            t['DTE'] = actual_dte
            # Calculate Value PnL
            t['PnL Points'] = t.get('PnL', 0)
            t['PnL Value'] = t.get('PnL', 0) * LOT_SIZE
            results.append(t)
            
        # Collect Daily Summary
        day_pnl_pts = sum(t.get('PnL', 0) for t in daily_trades)
        day_pnl_val = day_pnl_pts * LOT_SIZE
        
        day_type = "No Trade"
        if daily_trades:
            if any(t.get('Type') == 'Data Error' for t in daily_trades):
                day_type = "Data Error"
            elif all(t.get('Type') == 'No Entry' for t in daily_trades):
                day_type = "No Entry"
            else:
                day_type = "Active"
                
        daily_summaries.append({
            "Date": d,
            "Day Type": day_type,
            "PnL Points": day_pnl_pts,
            "PnL Value": day_pnl_val,
            "Trade Count": len(daily_trades),
            "Detailed Events": "\n".join(logs)
        })

    if results:
        res_df = pd.DataFrame(results)
        cols = ['Date', 'DTE', 'PnL Value', 'PnL Points', 'Type', 'Entry Time', 'Exit Time', 'Strike', 'Reason']
        final_cols = [c for c in cols if c in res_df.columns]
        return res_df[final_cols], daily_summaries
    return pd.DataFrame(), daily_summaries

def load_index_data(date_obj):
    fpath = get_sensex_spot_file(date_obj)
    if not fpath: return None
    try:
        df = pd.read_csv(fpath)
        df.columns = [c.strip().lower() for c in df.columns]
        
        if 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time']) 
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        df.set_index('datetime', inplace=True)
        return df
    except Exception as e:
        return None

def run_day_analysis(
    target_date,
    min_entry_time, entry_window_mins, exit_time, 
    sl_min_pts, sl_max_pts, trail_trigger, trail_step, rolling_step,
    portfolio_sl, strategy_mode, spot_check_time,
    max_entry_time=time(14, 45)
):
    logs = []
    trades = []
    current_trade = None
    
    spot_df = load_index_data(target_date)
    if spot_df is None or spot_df.empty:
        return logs, None, [{'Type': 'Data Error', 'Reason': 'No Index Data'}]
        
    spot_check_dt = datetime.combine(target_date, spot_check_time)
    if spot_check_dt not in spot_df.index:
         # Try finding nearest?
         temp = spot_df[spot_df.index >= spot_check_dt]
         if temp.empty:
             return logs, None, [{'Type': 'Data Error', 'Reason': 'Index Data Partial'}]
         start_row = temp.iloc[0]
    else:
         start_row = spot_df.loc[spot_check_dt]
         
    initial_spot = float(start_row['close'])
    current_strike = round(initial_spot / STRIKE_INTERVAL) * STRIKE_INTERVAL
    
    current_straddle = construct_straddle(target_date, current_strike)
    if current_straddle is None:
        return logs, None, [{'Type': 'Data Error', 'Reason': f'Missing Straddle {current_strike}', 'Strike': current_strike}]

    trading_start_dt = datetime.combine(target_date, min_entry_time)
    entry_window_end = trading_start_dt + timedelta(minutes=entry_window_mins)
    
    in_position = False
    entry_price = 0.0
    sl_price = 0.0
    sl_moved_to_cost = False
    last_trail_milestone = 0
    trade_pnl = 0.0
    
    is_rolled = False
    fixed_vwap_level = None
    straddle_cache = {current_strike: current_straddle}
    
    # Data Collection for Plotting
    day_records = []

    # Process Loop
    market_start = datetime.combine(target_date, time(9, 15))
    spot_iter = spot_df[spot_df.index >= market_start].sort_index()
    
    for curr_time, row in spot_iter.iterrows():
        if curr_time.time() > exit_time: break
        
        spot_close = row['close']
        
        # --- ROLLING CHECK ---
        if not in_position and curr_time.time() >= min_entry_time:
            diff = spot_close - current_strike
            roll_needed = False
            new_strike = current_strike
            
            if diff >= rolling_step:
                new_strike = int(round((current_strike + rolling_step) / STRIKE_INTERVAL) * STRIKE_INTERVAL)
                roll_needed = True
            elif diff <= -rolling_step:
                new_strike = int(round((current_strike - rolling_step) / STRIKE_INTERVAL) * STRIKE_INTERVAL)
                roll_needed = True
                
            if roll_needed:
                if new_strike not in straddle_cache:
                    straddle_cache[new_strike] = construct_straddle(target_date, new_strike)
                
                if straddle_cache[new_strike] is not None:
                    current_strike = new_strike
                    current_straddle = straddle_cache[new_strike]
                    is_rolled = True
                    logs.append(f"[{curr_time.strftime('%H:%M:%S')}] ROLL TRIGGERED: Spot moved {diff:.2f}. New Strike: {new_strike}")
                    
                    hist = current_straddle[(current_straddle.index.time >= time(9, 16)) & (current_straddle.index <= curr_time)]
                    if not hist.empty:
                        fixed_vwap_level = hist['Low'].min()
                        logs.append(f"[{curr_time.strftime('%H:%M:%S')}] REFERENCE LINE SET: {fixed_vwap_level:.2f}")
                    else:
                        fixed_vwap_level = None # Should not happen usually

        # --- CANDLE LOGIC ---
        # Data Record Default
        rec = {
            'Time': curr_time,
            'Strike': current_strike,
            'Spot': spot_close,
            'Close': np.nan,
            'VWAP': np.nan,
            'Ref': np.nan
        }

        if curr_time in current_straddle.index:
            s_row = current_straddle.loc[curr_time]
            vwap_val = fixed_vwap_level if is_rolled and fixed_vwap_level else s_row['VWAP']
            
            rec['Close'] = s_row['Close']
            rec['VWAP'] = s_row['VWAP']
            if is_rolled and fixed_vwap_level:
                rec['Ref'] = fixed_vwap_level

            if in_position:
                current_profit = entry_price - s_row['Close']
                
                # Trail to Cost
                if not sl_moved_to_cost and current_profit >= trail_trigger:
                    sl_price = entry_price
                    sl_moved_to_cost = True
                    logs.append(f"[{curr_time.strftime('%H:%M:%S')}] TRAIL TO COST: Profit {current_profit:.2f} >= {trail_trigger}. SL: {sl_price}")
                    
                # Deep Trail
                if sl_moved_to_cost:
                    add_prof = current_profit - trail_trigger
                    if add_prof >= 10:
                        steps = int(add_prof // trail_step)
                        if steps > last_trail_milestone:
                            new_sl = entry_price - (steps * trail_step)
                            if new_sl < sl_price:
                                sl_price = new_sl
                                last_trail_milestone = steps
                                logs.append(f"[{curr_time.strftime('%H:%M:%S')}] DEEP TRAIL: Step {steps}. New SL: {sl_price:.2f}")
                                
                # Check SL/Time Exit
                exit_reason = None
                if s_row['Close'] >= sl_price:
                    exit_reason = 'Stop Loss' if not sl_moved_to_cost else 'Trailing SL'
                elif curr_time.time() >= exit_time:
                    exit_reason = 'Time Exit'
                    
                if exit_reason:
                    pnl = entry_price - s_row['Close']
                    trade_pnl += pnl
                    in_position = False
                    current_trade['Exit Time'] = curr_time.time()
                    current_trade['Exit Price'] = s_row['Close']
                    current_trade['PnL'] = pnl
                    current_trade['Reason'] = exit_reason
                    trades.append(current_trade)
                    logs.append(f"[{curr_time.strftime('%H:%M:%S')}] EXIT ({exit_reason}): Price {s_row['Close']:.2f}, PnL {pnl:.2f}. (Entry: {entry_price:.2f})")
                    current_trade = None
                    
                    # Extend Window
                    entry_window_end = curr_time + timedelta(minutes=entry_window_mins)
                    
                    if strategy_mode == "ROLLING_VWAP" and exit_reason != 'Time Exit':
                         hist = current_straddle[(current_straddle.index.time >= time(9, 16)) & (current_straddle.index <= curr_time)]
                         if not hist.empty:
                             fixed_vwap_level = hist['Low'].min()

            elif not in_position:
                # Check Portfolio SL
                if portfolio_sl > 0 and trade_pnl <= -portfolio_sl:
                    pass # Day Stop Hit
                elif curr_time.time() > max_entry_time:
                    # Past max entry time
                    pass
                elif curr_time >= trading_start_dt and curr_time <= entry_window_end:
                    # Entry Check
                    idx_loc = current_straddle.index.get_loc(curr_time)
                    if idx_loc >= 5:
                        grp_a = current_straddle.iloc[idx_loc-5 : idx_loc-2]
                        grp_b = current_straddle.iloc[idx_loc-2 : idx_loc+1]
                        
                        ref_line = fixed_vwap_level if (strategy_mode == "ROLLING_VWAP" or is_rolled) and fixed_vwap_level else None
                        
                        def check_under(series, vwap_series, fixed):
                            if fixed: return (series < fixed).all()
                            return (series < vwap_series).all()
                            
                        cond1 = check_under(grp_a['Close'], grp_a['VWAP'], ref_line)
                        cond2 = check_under(grp_b['Close'], grp_b['VWAP'], ref_line)
                        cond3 = s_row['Close'] < grp_a['Low'].min()
                        
                        if cond1 and cond2 and cond3:
                            entry_price = s_row['Close']
                            high_a = grp_a['High'].max()
                            calc_sl = high_a - entry_price
                            real_sl = max(sl_min_pts, min(calc_sl, sl_max_pts))
                            sl_price = entry_price + real_sl
                            in_position = True
                            sl_moved_to_cost = False
                            last_trail_milestone = 0
                            
                            current_trade = {
                                'Strike': current_strike,
                                'Entry Time': curr_time.time(),
                                'Entry Price': entry_price,
                                'Type': 'Long Straddle',
                                'Migrated': is_rolled
                            }
                            
                            logs.append(f"[{curr_time.strftime('%H:%M:%S')}] ENTRY: Strike {current_strike} @ {entry_price:.2f}. SL: {sl_price:.2f} (Calc SL: {calc_sl:.2f} -> Real: {real_sl:.2f})")
                            if is_rolled:
                                 logs.append(f"  (Note: This entry is on a Rolled Strike {current_strike})")

        day_records.append(rec)

    if not trades:
        trades.append({'Type': 'No Entry', 'PnL': 0.0, 'Strike': current_strike})
        
    df_res = pd.DataFrame(day_records)
    if not df_res.empty:
        df_res.set_index('Time', inplace=True)
        
    return logs, df_res, trades

if __name__ == "__main__":
    res_df, daily = run_backtest()
    if not res_df.empty:
        print(f"\nTotal PnL Value: {res_df['PnL Value'].sum():.2f}")
        print(res_df)
        res_df.to_csv("sensex_backtest_results.csv")
    else:
        print("No trades found.")
