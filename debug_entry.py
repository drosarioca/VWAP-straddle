import pandas as pd
from datetime import time, datetime

fpath = r"C:\Users\Rosario\.gemini\antigravity\scratch\quant_trading\icharts_download\NIFTY-2026-02-17-17FEB26-25600-straddle-data.csv"
df = pd.read_csv(fpath)
df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
df['datetime'] = df['datetime'].dt.floor('min')
df.set_index('datetime', inplace=True)

# Filter for the day and starting from 09:16 (standard market open/start for VWAP)
df_day = df[df.index.date == datetime(2026, 2, 17).date()].copy()
df_day = df_day[df_day.index.time >= time(9, 16)]

# Manual VWAP Calculation
df_day['manual_vwap'] = (df_day['LTP'] * df_day['volume']).cumsum() / df_day['volume'].cumsum()

# Target time 09:49:00
target_dt = datetime(2026, 2, 17, 9, 49)

# Check values at 09:49
row_949 = df_day.loc[target_dt]

print(f"Time: 09:49:00")
print(f"Price (LTP): {row_949['LTP']}")
print(f"CSV VWAP: {row_949['vwap']}")
print(f"Manual VWAP: {row_949['manual_vwap']}")

print(f"\nIs LTP > CSV VWAP? {row_949['LTP'] > row_949['vwap']}")
print(f"Is LTP > Manual VWAP? {row_949['LTP'] > row_949['manual_vwap']}")
