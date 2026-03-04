import os
import yfinance as yf
import pandas as pd
import datetime
import re

class StockDataCache:
    def __init__(self, data_dir="data"):
        # Make the data_dir relative to the location of utils.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(base_dir, data_dir)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _get_file_path(self, ticker: str) -> str:
        # Sanitize ticker to prevent path traversal vulnerabilities
        # Keep alphanumeric and specific symbols (., -, =, ^)
        sanitized_ticker = re.sub(r'[^a-zA-Z0-9.\-=^]', '', str(ticker))
        # Prevent traversal combinations (e.g. '..' or '../')
        sanitized_ticker = os.path.basename(sanitized_ticker)

        return os.path.join(self.data_dir, f"{sanitized_ticker}.json")

    def get_data(self, ticker: str, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
        file_path = self._get_file_path(ticker)
        
        if os.path.exists(file_path):
            try:
                # Load existing cache
                cached_df = pd.read_json(file_path, orient="table")
                
                # Check if we need to fetch missing data (either older or newer)
                if not cached_df.empty:
                    first_cached_date = cached_df.index.min().date()
                    last_cached_date = cached_df.index.max().date()
                    
                    needs_save = False
                    dfs_to_concat = [cached_df]
                    
                    # 1. Check if we need older data
                    if start_date < first_cached_date:
                        fetch_end_old = first_cached_date - datetime.timedelta(days=1)
                        if start_date <= fetch_end_old:
                            print(f"Cache hit for {ticker}. Fetching older data from {start_date} to {fetch_end_old}.")
                            older_data = self._download_from_yf(ticker, start_date, fetch_end_old + datetime.timedelta(days=1))
                            if older_data is not None and not older_data.empty:
                                dfs_to_concat.append(older_data)
                                needs_save = True

                    # 2. Check if we need newer data
                    if end_date > last_cached_date:
                        fetch_start_new = last_cached_date + datetime.timedelta(days=1)
                        if fetch_start_new <= end_date:
                            print(f"Cache hit for {ticker}. Fetching newer data from {fetch_start_new} to {end_date}.")
                            newer_data = self._download_from_yf(ticker, fetch_start_new, end_date + datetime.timedelta(days=1))
                            if newer_data is not None and not newer_data.empty:
                                dfs_to_concat.append(newer_data)
                                needs_save = True
                    
                    if needs_save:
                        # Combine all data
                        cached_df = pd.concat(dfs_to_concat)
                        # Remove duplicates just in case
                        cached_df = cached_df[~cached_df.index.duplicated(keep='last')]
                        # Sort index
                        cached_df.sort_index(inplace=True)
                        
                        # Overwrite cache with combined data
                        cached_df.to_json(file_path, orient="table")
                        print(f"Cache updated for {ticker}.")
                    elif start_date >= first_cached_date and end_date <= last_cached_date:
                        print(f"Cache hit for {ticker}. All requested data available locally.")

                else:
                    # File exists but is empty, redownload full
                    print(f"Cache for {ticker} is empty. Downloading full range.")
                    cached_df = self._download_and_save_full(ticker, start_date, end_date, file_path)
            except Exception as e:
                print(f"Error reading cache for {ticker}: {e}. Redownloading.")
                cached_df = self._download_and_save_full(ticker, start_date, end_date, file_path)
        else:
            # Cache miss
            print(f"Cache miss for {ticker}. Downloading full data from {start_date} to {end_date}.")
            cached_df = self._download_and_save_full(ticker, start_date, end_date, file_path)

        if cached_df is not None and not cached_df.empty:
            # Return only the requested date range
            mask = (cached_df.index.date >= start_date) & (cached_df.index.date <= end_date)
            return cached_df.loc[mask].copy()
        
        return None

    def _download_and_save_full(self, ticker: str, start_date: datetime.date, end_date: datetime.date, file_path: str) -> pd.DataFrame:
        df = self._download_from_yf(ticker, start_date, end_date + datetime.timedelta(days=1))
        if df is not None and not df.empty:
            df.to_json(file_path, orient="table")
        return df

    def _download_from_yf(self, ticker: str, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
        try:
            df = yf.download(ticker, start=start_date, end=end_date)
            if df.empty:
                return None
            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception as e:
            print(f"Error downloading data for {ticker}: {e}")
            return None

# Global cache instance
_cache = StockDataCache()

def load_data(ticker: str, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Fetches historical stock data from Yahoo Finance, utilizing a local cache."""
    return _cache.get_data(ticker, start_date, end_date)

from strategy import STRATEGIES  # noqa: E402

def apply_strategy(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Applies the selected trading strategy and calculates indicators."""
    if strategy in STRATEGIES:
        return STRATEGIES[strategy]["apply_strategy"](df)
    return df

def calculate_metrics(df: pd.DataFrame, strategy: str) -> dict:
    """Calculates basic performance metrics from the generated signals."""
    if df.empty or 'Position' not in df.columns or df['Position'].abs().sum() == 0:
        return {"Total Return": "0.00%", "Average Return": "0.00%", "Number of Trades": 0, "Win Rate": "0.00%", "Trades History": []}

    initial_capital = 10000.0
    capital = initial_capital
    position_size = 0 # Number of shares held
    
    trades = 0
    winning_trades = 0
    
    buy_price = 0
    buy_date = None
    
    trades_history = []

    # Store exit info before filtering
    exit_price = df['Close'].iloc[-1]
    exit_date = df.index[-1]

    # Filter out rows with no position changes to avoid iterating through them
    active_df = df[df['Position'] != 0.0]

    # Extremely simplified backtest loop just for display metrics
    dates = active_df.index
    prices = active_df['Close'].to_numpy()
    positions = active_df['Position'].to_numpy()

    for date, price, pos in zip(dates, prices, positions):
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
                'profit': price - buy_price,
                'profit_pct': (price - buy_price) / buy_price * 100 if buy_price > 0 else 0
            })
            
            position_size = 0
            buy_price = 0
            buy_date = None

    # Close out open position at the end
    if position_size > 0:
         capital += position_size * exit_price
         trades += 1
         if exit_price > buy_price:
             winning_trades += 1
         trades_history.append({
             'entry_date': buy_date,
             'exit_date': exit_date,
             'entry_price': buy_price,
             'exit_price': exit_price,
             'profit': exit_price - buy_price,
             'profit_pct': (exit_price - buy_price) / buy_price * 100 if buy_price > 0 else 0
         })

    total_return = ((capital - initial_capital) / initial_capital) * 100
    win_rate = (winning_trades / trades * 100) if trades > 0 else 0
    avg_return = sum([t['profit_pct'] for t in trades_history]) / len(trades_history) if trades_history else 0
    
    return {
        "Total Return": f"{total_return:.2f}%",
        "Average Return": f"{avg_return:.2f}%",
        "Number of Trades": trades,
        "Win Rate": f"{win_rate:.2f}%",
        "Trades History": trades_history
    }
