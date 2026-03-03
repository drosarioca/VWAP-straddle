import json
import os
import sys

# Set stdout to utf-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

log_path = r"C:\Users\Rosario\.gemini\antigravity\scratch\quant_trading\backtest_logs.json"

with open(log_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Params: {data.get('params')}")

for entry in data.get('logs', []):
    if entry.get('Date') == '2026-02-17':
        print(f"\n--- 2026-02-17 Logs ---")
        print(f"Day Type: {entry.get('Day Type')}")
        print(f"PnL: {entry.get('PnL')}")
        print(f"Events:\n{entry.get('Detailed Events')}")
