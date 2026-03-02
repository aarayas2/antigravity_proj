import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import datetime

def load_data(ticker: str, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Fetches historical stock data from Yahoo Finance."""
    try:
        df = yf.download(ticker, start=start_date, end=end_date)
        if df.empty:
            return None
        # Flatten multi-index columns if present (yfinance returns multi-index for some tickers)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"Error downloading data for {ticker}: {e}")
        return None

from strategy import STRATEGIES

def apply_strategy(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Applies the selected trading strategy and calculates indicators."""
    if strategy in STRATEGIES:
        return STRATEGIES[strategy]["apply_strategy"](df)
    return df

def calculate_metrics(df: pd.DataFrame, strategy: str) -> dict:
    """Calculates basic performance metrics from the generated signals."""
    if 'Position' not in df.columns or df['Position'].abs().sum() == 0:
        return {"Total Return": "0.00%", "Number of Trades": 0, "Win Rate": "0.00%", "Trades History": []}

    initial_capital = 10000.0
    capital = initial_capital
    position_size = 0 # Number of shares held
    
    trades = 0
    winning_trades = 0
    
    buy_price = 0
    buy_date = None
    
    trades_history = []

    # Extremely simplified backtest loop just for display metrics
    for i in range(len(df)):
        price = df['Close'].iloc[i]
        pos = df['Position'].iloc[i]
        
        date = df.index[i]
        
        if pos == 1.0 and capital > price: # Buy
            shares_to_buy = capital // price
            position_size += shares_to_buy
            capital -= shares_to_buy * price
            buy_price = price
            buy_date = date
        elif pos == -1.0 and position_size > 0: # Sell
            capital += position_size * price
            
            trades += 1
            if price > buy_price:
                 winning_trades += 1
                 
            trades_history.append({
                'entry_date': buy_date,
                'exit_date': date,
                'entry_price': buy_price,
                'exit_price': price,
                'profit': price - buy_price
            })
            
            position_size = 0
            buy_price = 0
            buy_date = None

    # Close out open position at the end
    if position_size > 0:
         exit_price = df['Close'].iloc[-1]
         capital += position_size * exit_price
         trades += 1
         if exit_price > buy_price:
             winning_trades += 1
         trades_history.append({
             'entry_date': buy_date,
             'exit_date': df.index[-1],
             'entry_price': buy_price,
             'exit_price': exit_price,
             'profit': exit_price - buy_price
         })

    total_return = ((capital - initial_capital) / initial_capital) * 100
    win_rate = (winning_trades / trades * 100) if trades > 0 else 0
    
    return {
        "Total Return": f"{total_return:.2f}%",
        "Number of Trades": trades,
        "Win Rate": f"{win_rate:.2f}%",
        "Trades History": trades_history
    }
