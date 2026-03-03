
import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_equity_curve():
    csv_path = 'backtest_results.csv'
    if not os.path.exists(csv_path):
        print("Results file not found.")
        return

    df = pd.read_csv(csv_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    # Calculate Metrics
    df['Cumulative_PnL'] = df['PnL'].cumsum()
    df['Peak'] = df['Cumulative_PnL'].cummax()
    df['Drawdown'] = df['Cumulative_PnL'] - df['Peak']
    
    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    # Equity Curve
    ax1.plot(df['Date'], df['Cumulative_PnL'], label='Equity Curve', color='green', linewidth=2)
    ax1.set_title('Strategy Equity Curve (0DTE Straddle)', fontsize=14)
    ax1.set_ylabel('Total Points PnL')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Drawdown
    ax2.fill_between(df['Date'], df['Drawdown'], 0, color='red', alpha=0.3, label='Drawdown')
    ax2.set_ylabel('Drawdown (Pts)')
    ax2.set_xlabel('Date')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('equity_curve.png')
    print("Plot saved as equity_curve.png")
    
    # Text Stats
    print("\n--- Strategy Statistics ---")
    print(f"Total Net PnL: {df['Cumulative_PnL'].iloc[-1]:.2f}")
    print(f"Max Drawdown: {df['Drawdown'].min():.2f}")
    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {(len(df[df['PnL'] > 0]) / len(df)) * 100:.1f}%")
    print(f"Avg Trade: {df['PnL'].mean():.2f}")

if __name__ == "__main__":
    plot_equity_curve()
