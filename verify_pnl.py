
import pandas as pd
import os

def check_pnl():
    fpath = "Backtest_Detailed_Report_Rolling.xlsx"
    if not os.path.exists(fpath):
        print("File not found.")
        return

    try:
        df = pd.read_excel(fpath, sheet_name="Daily Logs")
        total_pnl = df['PnL'].sum()
        print(f"Total PnL in report: {total_pnl:.2f}")
        
        # Check params sheet too
        df_params = pd.read_excel(fpath, sheet_name="Input Parameters")
        print("\nParameters in report:")
        print(df_params)
        
    except Exception as e:
        print(f"Error reading excel: {e}")

if __name__ == "__main__":
    check_pnl()
