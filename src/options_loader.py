import os
import pandas as pd
from glob import glob
from datetime import datetime
import re

class OptionsLoader:
    def __init__(self, base_paths):
        r"""
        base_paths: List of paths to the yearly options data folders.
                    e.g. [r'C:\...\NIFTY-2024-1min-options-data', ...]
        """
        self.base_paths = base_paths
        self.expiry_map = {} # {expiry_date_obj: folder_path}
        
        # Pre-scan directories to map Expiries
        self._scan_directories()

    def _scan_directories(self):
        print("Scanning options directories...")
        for base_path in self.base_paths:
            if not os.path.exists(base_path):
                print(f"Warning: Path not found: {base_path}")
                continue
                
            # Iterate through weekly folders (e.g., '2024Jan11')
            for folder_name in os.listdir(base_path):
                full_folder_path = os.path.join(base_path, folder_name)
                if not os.path.isdir(full_folder_path):
                    continue
                
                # Parse folder name to get Expiry Date
                try:
                    # Format: YYYYMonDD (e.g., 2024Jan11)
                    expiry_date = datetime.strptime(folder_name, "%Y%b%d").date()
                    self.expiry_map[expiry_date] = full_folder_path
                except ValueError:
                    # print(f"Skipping non-conforming folder: {folder_name}")
                    pass
        print(f"Index complete. Found {len(self.expiry_map)} weekly expiries.")

    def get_weekly_folder(self, expiry_date):
        """Returns the folder path for a specific expiry."""
        return self.expiry_map.get(expiry_date)

    def get_option_filepath(self, date, expiry_date, strike, option_type):
        """
        Constructs the expected filename and returns the full path if it exists.
        Format observed: YYYY-MM-DD-StrikeType.csv (e.g., 2024-01-05-21000CE.csv)
        """
        folder_path = self.get_weekly_folder(expiry_date)
        if not folder_path:
            return None
        
        # Format filename: YYYY-MM-DD-{Strike}{Type}.csv
        date_str = date.strftime("%Y-%m-%d")
        filename = f"{date_str}-{strike}{option_type}.csv"
        full_path = os.path.join(folder_path, filename)
        
        if os.path.exists(full_path):
            return full_path
        
        # Fallback: Sometimes NIFTY prefix might be present or naming varies slightly?
        # Based on file listing: "2024-01-05-20700CE.csv" - this matches the pattern above.
        return None

    def load_option_data(self, date, expiry_date, strike, option_type):
        """
        Loads 1-minute data for a specific option contract.
        """
        filepath = self.get_option_filepath(date, expiry_date, strike, option_type)
        if not filepath:
            # print(f"Data not found for {date} | Expiry: {expiry_date} | {strike}{option_type}")
            return None
            
        try:
            # Load CSV
            # Assuming columns might need mapping. Standard NIFTY files often have: Date, Time, Open, High, Low, Close, Volume
            df = pd.read_csv(filepath)
            
            # Normalize columns
            df.columns = [c.strip().lower() for c in df.columns]
            
            # Map back to Title Case
            rename_map = {
                'timestamp': 'Datetime', 'date': 'Date', 'time': 'Time', 'open': 'Open',
                'high': 'High', 'low': 'Low', 'close': 'Close',
                'volume': 'Volume', 'oi': 'OI'
            }
            df.rename(columns=rename_map, inplace=True)
            
            # Create datetime index
            if 'Datetime' in df.columns:
                df['Datetime'] = pd.to_datetime(df['Datetime'])
            elif 'Date' in df.columns and 'Time' in df.columns:
                df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
            
            # Normalize to minute floor (remove seconds if 59s)
            # This ensures alignment with Spot data which is usually HH:MM:00
            df['Datetime'] = df['Datetime'].dt.floor('min')
            
            # Calculate VWAP if missing
            if 'VWAP' not in df.columns and 'Close' in df.columns and 'Volume' in df.columns:
                # Standard Intraday VWAP (since file is daily)
                df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
            
            df.set_index('Datetime', inplace=True)
            
            return df
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None

    @staticmethod
    def find_nearest_expiry(current_date, available_expiries, min_dte=0):
        """
        Finds the nearest expiry date >= current_date + min_dte
        """
        # specialized logic can go here (e.g., filtering self.expiry_map.keys())
        future_expiries = sorted([d for d in available_expiries if d >= current_date])
        if future_expiries:
            return future_expiries[0] # Current/Next Week
        return None

    @staticmethod
    def get_atm_strike(index_value, step=50):
        """
        Returns the nearest ATM strike.
        """
        return round(index_value / step) * step

# Usage Example:
# loader = OptionsLoader([r"C:\Path\To\2024", r"C:\Path\To\2025"])
# df = loader.load_option_data(date(2024, 1, 5), date(2024, 1, 11), 21700, 'CE')
