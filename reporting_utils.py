
import pandas as pd
import numpy as np
import os
import xlsxwriter
from datetime import datetime, timedelta
import math

def generate_variant_report(report_path, trades_df, params, daily_summaries=None, lot_size=1, slippage=0):
    """
    Generates a multi-sheet Excel report for a single variant.
    PnL values are reduced by slippage (points) and then converted to Rupees using lot_size.
    """
    # Clone dataframes to avoid modifying originals
    trades_df = trades_df.copy()
    
    # 0. Apply Slippage and Lot Size
    # Valid trade types that incur slippage
    exec_types = ['Long Straddle', 'SL', 'EOD', 'Stop Loss', 'Trailing SL', 'Time Exit']
    
    if not trades_df.empty:
        # Subtract slippage from points for matching types
        mask = trades_df['Type'].isin(exec_types)
        trades_df.loc[mask, 'PnL'] = trades_df.loc[mask, 'PnL'] - slippage
        
        # Convert to Rupees
        if lot_size != 1:
            trades_df['PnL'] = trades_df['PnL'] * lot_size

    if daily_summaries:
        # Note: daily_summaries usually contain pre-calculated PnL points.
        # We need to reconstruct it if we want accurate Daily PnL in Rupees with slippage.
        # However, it's easier to just re-group from the modified trades_df if possible.
        pass

    # Calculate Periodical PnL
    # Monthly PnL Layout: Period (YYYY-MM), PnL
    m_df = trades_df.copy()
    m_df['Date'] = pd.to_datetime(m_df['Date'])
    monthly_pnl = m_df.set_index('Date').resample('ME')['PnL'].sum().reset_index()
    monthly_pnl['Period'] = monthly_pnl['Date'].dt.strftime('%Y-%m')
    monthly_pnl = monthly_pnl[['Period', 'PnL']]
    
    # Quarterly PnL Layout: Period (YYYYQX), PnL
    quarterly_pnl = m_df.set_index('Date').resample('QE')['PnL'].sum().reset_index()
    quarterly_pnl['Period'] = quarterly_pnl['Date'].dt.year.astype(str) + 'Q' + quarterly_pnl['Date'].dt.quarter.astype(str)
    quarterly_pnl = quarterly_pnl[['Period', 'PnL']]
    
    yearly_pnl = m_df.set_index('Date').resample('YE')['PnL'].sum().reset_index()

    # Daily PnL Layout: Date, Expiry Date, PnL (Rs), PnL (Pts), Total Trade
    # We need to calculate these from trades_df
    daily_stats = trades_df.groupby('Date').agg(
        PnL_Rs=('PnL', 'sum'),
        Total_Trade=('PnL', 'count')
    ).reset_index()
    daily_stats['PnL (Pts)'] = daily_stats['PnL_Rs'] / lot_size
    daily_stats['Expiry Date'] = daily_stats['Date'] # Default for 0DTE
    daily_stats.rename(columns={'PnL_Rs': 'PnL (Rs)', 'Total_Trade': 'total Trade', 'Date': 'Date'}, inplace=True)
    daily_stats = daily_stats[['Date', 'Expiry Date', 'PnL (Rs)', 'PnL (Pts)', 'total Trade']]

    # Equity and Drawdown Layout: Date (with time), Equity (INR), Drawdown (INR)
    # Granularity: Trade-level
    eq_df = trades_df.copy()
    
    # Filter out rows that are not valid trades (e.g. "No Entry" placeholders if they exist)
    exec_types = ['Long Straddle', 'SL', 'EOD', 'Stop Loss', 'Trailing SL', 'Time Exit']
    eq_df = eq_df[eq_df['Type'].isin(exec_types)].copy()

    if 'Exit Time' in eq_df.columns:
        # Handle None/NaN in Exit Time by replacing with a default or coercing
        # Convert everything to string first, but handle 'None' string specifically
        eq_df['Exit_Time_Clean'] = eq_df['Exit Time'].astype(str).replace(['None', 'nan', ''], '00:00:00')
        combined_str = eq_df['Date'].astype(str) + ' ' + eq_df['Exit_Time_Clean']
        eq_df['DateTime'] = pd.to_datetime(combined_str, errors='coerce')
        # Drop rows where DateTime conversion failed (if any)
        eq_df = eq_df.dropna(subset=['DateTime'])
    else:
        eq_df['DateTime'] = pd.to_datetime(eq_df['Date'])
    
    eq_df.sort_values('DateTime', inplace=True)
    eq_df['Equity (INR)'] = eq_df['PnL'].cumsum()
    eq_df['Peak'] = eq_df['Equity (INR)'].cummax()
    eq_df['Drawdown (INR)'] = eq_df['Equity (INR)'] - eq_df['Peak']
    equity_dd_data = eq_df[['DateTime', 'Equity (INR)', 'Drawdown (INR)']].rename(columns={'DateTime': 'Date'})

    # 2. Calculate Extensive Metrics
    # Note: Using a daily-aggregated PnL for standard metrics logic
    metrics_daily = trades_df.groupby('Date')['PnL'].sum().reset_index()
    metrics_daily['Peak'] = metrics_daily['PnL'].cumsum().cummax()
    metrics_daily['Drawdown'] = metrics_daily['PnL'].cumsum() - metrics_daily['Peak']
    metrics_records = calculate_extensive_metrics(trades_df, metrics_daily)
    metrics_df = pd.DataFrame(metrics_records)

    # 3. Write to Excel with XlsxWriter
    writer = pd.ExcelWriter(report_path, engine='xlsxwriter')
    workbook = writer.book
    
    # Styles
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#D9E1F2'})
    num_fmt = workbook.add_format({'num_format': '#,##0.00'})
    date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    datetime_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})

    # Sheets
    trades_df.to_excel(writer, sheet_name='detailed trade logs', index=False)
    
    param_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
    param_df.to_excel(writer, sheet_name='input parameters', index=False)
    
    metrics_df.to_excel(writer, sheet_name='metrics', index=False)
    daily_stats.to_excel(writer, sheet_name='daily pnl', index=False)
    monthly_pnl.to_excel(writer, sheet_name='monthly pnl', index=False)
    quarterly_pnl.to_excel(writer, sheet_name='quaterly pnl', index=False)
    yearly_pnl.to_excel(writer, sheet_name='yearly pnl', index=False)
    
    equity_dd_data.to_excel(writer, sheet_name='equity and drawdown', index=False)
    
    # CHARTS on 'equity and drawdown' sheet
    charts_sheet = writer.sheets['equity and drawdown']
    
    # Equity Chart
    equity_chart = workbook.add_chart({'type': 'line'})
    max_row = len(equity_dd_data) + 1
    equity_chart.add_series({
        'name': 'Equity (INR)',
        'categories': ['equity and drawdown', 1, 0, max_row-1, 0],
        'values':     ['equity and drawdown', 1, 1, max_row-1, 1],
        'line':       {'color': 'green'},
    })
    equity_chart.set_title({'name': 'Equity Curve'})
    equity_chart.set_x_axis({'name': 'Date'})
    equity_chart.set_y_axis({'name': 'INR'})
    equity_chart.set_legend({'position': 'right'})
    
    # Drawdown Chart
    dd_chart = workbook.add_chart({'type': 'area'})
    dd_chart.add_series({
        'name': 'Drawdown (INR)',
        'categories': ['equity and drawdown', 1, 0, max_row-1, 0],
        'values':     ['equity and drawdown', 1, 2, max_row-1, 2],
        'fill':       {'color': 'red', 'transparency': 50},
    })
    dd_chart.set_title({'name': 'Drawdown Curve'})
    dd_chart.set_x_axis({'name': 'Date'})
    dd_chart.set_y_axis({'name': 'INR'})
    dd_chart.set_legend({'position': 'right'})
    
    # Insert Charts
    charts_sheet.insert_chart('E2', equity_chart, {'x_scale': 1.5, 'y_scale': 1.5})
    charts_sheet.insert_chart('E25', dd_chart, {'x_scale': 1.5, 'y_scale': 1.5})
    
    # Column Formatting
    for sheet_name in writer.sheets:
        ws = writer.sheets[sheet_name]
        ws.set_column('A:Z', 15)
        # Apply header format manually if needed, but to_excel does its thing.
        # Let's at least fix the Date columns
        if sheet_name in ['daily pnl', 'detailed trade logs']:
            ws.set_column('A:A', 15, date_fmt)
        if sheet_name == 'equity and drawdown':
            ws.set_column('A:A', 20, datetime_fmt)
            ws.set_column('B:C', 15, num_fmt)

    writer.close()
    return metrics_records

def calculate_extensive_metrics(trades_df, daily_pnl):
    """
    Calculates 30+ detailed trading metrics.
    """
    # Filter out empty/invalid trades
    valid_trades = trades_df[trades_df['Type'].isin(['Long Straddle', 'SL', 'EOD', 'Stop Loss', 'Trailing SL', 'Time Exit'])]
    
    # 1. Trade Based Metrics
    total_trades = len(valid_trades)
    winning_trades = valid_trades[valid_trades['PnL'] > 0]
    losing_trades = valid_trades[valid_trades['PnL'] < 0]
    
    total_winning_trades = len(winning_trades)
    total_losing_trades = len(losing_trades)
    trade_win_rate = (total_winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = daily_pnl['PnL'].sum()
    gross_profit = winning_trades['PnL'].sum()
    gross_loss = abs(losing_trades['PnL'].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)
    
    # 2. Drawdown & Returns
    max_dd = daily_pnl['Drawdown'].min()
    return_on_max_dd = (total_pnl / abs(max_dd)) if max_dd != 0 else 0
    
    # 3. Stats (Standard deviation based)
    daily_returns = daily_pnl['PnL']
    mean_daily = daily_returns.mean()
    std_daily = daily_returns.std()
    
    sharpe = (mean_daily / std_daily * math.sqrt(252)) if std_daily > 0 else 0
    
    neg_returns = daily_returns[daily_returns < 0]
    std_neg = neg_returns.std()
    sortino = (mean_daily / std_neg * math.sqrt(252)) if std_neg > 0 else 0
    
    # Expectancy: (WinRate * AvgWin) - (LossRate * AvgLoss) -> or PnL / Trades
    avg_win_trade = winning_trades['PnL'].mean() if not winning_trades.empty else 0
    avg_loss_trade = abs(losing_trades['PnL'].mean()) if not losing_trades.empty else 0
    expectancy = (total_pnl / total_trades) if total_trades > 0 else 0
    
    # SQN = sqrt(N) * AveragePnL / StdDevPnL
    sqn = (math.sqrt(total_trades) * (total_pnl / total_trades) / valid_trades['PnL'].std()) if total_trades > 0 and valid_trades['PnL'].std() > 0 else 0
    
    # 4. Day Based Metrics
    total_trading_days = len(daily_pnl)
    win_days_df = daily_pnl[daily_pnl['PnL'] > 0]
    loss_days_df = daily_pnl[daily_pnl['PnL'] < 0]
    
    total_winning_days = len(win_days_df)
    total_losing_days = len(loss_days_df)
    day_win_rate = (total_winning_days / total_trading_days * 100) if total_trading_days > 0 else 0
    day_loss_rate = (total_losing_days / total_trading_days * 100) if total_trading_days > 0 else 0
    
    avg_profit_win_day = win_days_df['PnL'].mean() if not win_days_df.empty else 0
    avg_loss_loss_day = abs(loss_days_df['PnL'].mean()) if not loss_days_df.empty else 0
    mean_profit_per_day = total_pnl / total_trading_days if total_trading_days > 0 else 0
    
    max_profit_day = daily_pnl['PnL'].max()
    max_loss_day = daily_pnl['PnL'].min()
    
    win_loss_ratio = (avg_win_trade / avg_loss_trade) if avg_loss_trade > 0 else 0
    day_profit_ratio = (avg_profit_win_day / avg_loss_loss_day) if avg_loss_loss_day > 0 else 0
    
    # 5. Streaks & Recovery
    # Recovery Time (Max days in DD)
    recovery_time = 0
    if not daily_pnl.empty:
        dd_series = daily_pnl['Drawdown']
        current_dd_len = 0
        max_dd_len = 0
        for val in dd_series:
            if val < 0:
                current_dd_len += 1
            else:
                max_dd_len = max(max_dd_len, current_dd_len)
                current_dd_len = 0
        recovery_time = max(max_dd_len, current_dd_len)
        
    # Consecutive Wins/Losses
    max_cons_wins = 0
    max_cons_losses = 0
    if not daily_pnl.empty:
        results = (daily_pnl['PnL'] > 0).astype(int) - (daily_pnl['PnL'] < 0).astype(int)
        win_streak = 0
        loss_streak = 0
        for r in results:
            if r == 1:
                win_streak += 1
                max_cons_wins = max(max_cons_wins, win_streak)
                loss_streak = 0
            elif r == -1:
                loss_streak += 1
                max_cons_losses = max(max_cons_losses, loss_streak)
                win_streak = 0
                
    metrics = [
        {"Metric": "Total Trades", "Value": total_trades},
        {"Metric": "Total Winning Trades", "Value": total_winning_trades},
        {"Metric": "Total Losing Trades", "Value": total_losing_trades},
        {"Metric": "Win Rate", "Value": f"{trade_win_rate:.2f}%"},
        {"Metric": "Total PnL", "Value": round(total_pnl, 2)},
        {"Metric": "Profit Factor", "Value": round(profit_factor, 2)},
        {"Metric": "Max Drawdown", "Value": round(max_dd, 2)},
        {"Metric": "Return on Max DD", "Value": round(return_on_max_dd, 2)},
        {"Metric": "Sharpe Ratio", "Value": round(sharpe, 2)},
        {"Metric": "Sortino Ratio", "Value": round(sortino, 2)},
        {"Metric": "Expectancy", "Value": round(expectancy, 2)},
        {"Metric": "SQN", "Value": round(sqn, 2)},
        {"Metric": "Avg Profit Winning Trade", "Value": round(avg_win_trade, 2)},
        {"Metric": "Avg Loss Losing Trade", "Value": round(avg_loss_trade, 2)},
        {"Metric": "Mean Profit Per Trade", "Value": round(total_pnl / total_trades if total_trades > 0 else 0, 2)},
        {"Metric": "Total Trading Days", "Value": total_trading_days},
        {"Metric": "Total Winning Days", "Value": total_winning_days},
        {"Metric": "Total Losing Days", "Value": total_losing_days},
        {"Metric": "Day Wise Win Rate", "Value": f"{day_win_rate:.2f}%"},
        {"Metric": "Day Wise Loosing Rate", "Value": f"{day_loss_rate:.2f}%"},
        {"Metric": "Avg Profit Winning Day", "Value": round(avg_profit_win_day, 2)},
        {"Metric": "Avg Loss Losing Day", "Value": round(avg_loss_loss_day, 2)},
        {"Metric": "Mean Profit Per Day", "Value": round(mean_profit_per_day, 2)},
        {"Metric": "Max Profit Day", "Value": round(max_profit_day, 2)},
        {"Metric": "Max Loss Day", "Value": round(max_loss_day, 2)},
        {"Metric": "Win/Loss Ratio", "Value": round(win_loss_ratio, 2)},
        {"Metric": "Day Profit Ratio", "Value": round(day_profit_ratio, 2)},
        {"Metric": "Max DD Recovery Time", "Value": f"{recovery_time} Days"},
        {"Metric": "Max Cons Wins", "Value": max_cons_wins},
        {"Metric": "Max Cons Losses", "Value": max_cons_losses}
    ]
    return metrics
