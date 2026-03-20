"""
Utility functions for data loading, caching, and backtesting.
"""

import datetime
import os
import re

import pandas as pd  # pylint: disable=import-error
import yfinance as yf  # pylint: disable=import-error

from persistence import StatsManager, JsonStatsStorage  # pylint: disable=import-error
from strategy import STRATEGIES  # pylint: disable=import-error


class StockDataCache:  # pylint: disable=too-few-public-methods
    """Cache implementation for Yahoo Finance stock data."""
    def __init__(self, data_dir="data"):
        # Make the data_dir relative to the location of utils.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(base_dir, data_dir)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _get_file_path(self, ticker: str) -> str:
        # Sanitize ticker to prevent path traversal vulnerabilities
        # Ensure cross-platform path handling for os.path.basename by normalizing backslashes
        normalized_ticker = str(ticker).replace("\\", "/")
        # Prevent traversal combinations (e.g. '..' or '../')
        sanitized_ticker = os.path.basename(normalized_ticker)
        # Keep alphanumeric and specific symbols (., -, =, ^)
        sanitized_ticker = re.sub(r"[^a-zA-Z0-9.\-=^]", "", sanitized_ticker)

        final_path = os.path.abspath(
            os.path.join(self.data_dir, f"{sanitized_ticker}.json")
        )

        # Ensure the final path is strictly within the data_dir
        if not final_path.startswith(os.path.abspath(self.data_dir) + os.sep):
            raise ValueError(
                f"Invalid ticker format: Potential path traversal detected for '{ticker}'."
            )

        return final_path

    def _handle_cache_miss(
        self,
        ticker: str,
        start_date: datetime.date,
        end_date: datetime.date,
        file_path: str,
    ) -> pd.DataFrame:
        print(
            f"Cache miss for {ticker}. Downloading full data from {start_date} to {end_date}."
        )
        return self._download_and_save_full(ticker, start_date, end_date, file_path)

    def _handle_cache_hit(self, ticker: str, cached_df: pd.DataFrame) -> pd.DataFrame:
        print(f"Cache hit for {ticker}. All requested data available locally.")
        return cached_df

    def _handle_partial_hit(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        ticker: str,
        start_date: datetime.date,
        end_date: datetime.date,
        cached_df: pd.DataFrame,
        file_path: str,
    ) -> pd.DataFrame:
        first_cached_date = cached_df.index.min().date()
        last_cached_date = cached_df.index.max().date()

        needs_save = False
        dfs_to_concat = [cached_df]

        # 1. Check if we need older data
        if start_date <= first_cached_date - datetime.timedelta(days=1):
            fetch_end_old = first_cached_date - datetime.timedelta(days=1)
            print(
                f"Partial hit for {ticker}. "
                f"Fetching older data from {start_date} to {fetch_end_old}."
            )
            older_data = self._download_from_yf(
                ticker, start_date, fetch_end_old + datetime.timedelta(days=1)
            )
            if older_data is not None and not older_data.empty:
                dfs_to_concat.append(older_data)
                needs_save = True

        # 2. Check if we need newer data
        if end_date >= last_cached_date + datetime.timedelta(days=1):
            fetch_start_new = last_cached_date + datetime.timedelta(days=1)
            print(
                f"Partial hit for {ticker}. "
                f"Fetching newer data from {fetch_start_new} to {end_date}."
            )
            newer_data = self._download_from_yf(
                ticker, fetch_start_new, end_date + datetime.timedelta(days=1)
            )
            if newer_data is not None and not newer_data.empty:
                dfs_to_concat.append(newer_data)
                needs_save = True

        if needs_save:
            # Combine all data
            cached_df = pd.concat(dfs_to_concat)
            # Remove duplicates just in case
            cached_df = cached_df[~cached_df.index.duplicated(keep="last")]
            # Sort index
            cached_df.sort_index(inplace=True)

            # Overwrite cache with combined data
            cached_df.to_json(file_path, orient="table")
            print(f"Cache updated for {ticker}.")

        return cached_df

    def get_data(
        self, ticker: str, start_date: datetime.date, end_date: datetime.date
    ) -> pd.DataFrame:
        """Retrieves data from cache or downloads it if not available."""
        file_path = self._get_file_path(ticker)

        cached_df = None
        if os.path.exists(file_path):
            try:
                cached_df = pd.read_json(file_path, orient="table")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"Error reading cache for {ticker}: {e}. Redownloading.")
                cached_df = None

        if cached_df is None or cached_df.empty:
            cached_df = self._handle_cache_miss(ticker, start_date, end_date, file_path)
        else:
            first_cached_date = cached_df.index.min().date()
            last_cached_date = cached_df.index.max().date() - datetime.timedelta(days=1)

            if start_date >= first_cached_date and end_date <= last_cached_date:
                cached_df = self._handle_cache_hit(ticker, cached_df)
            else:
                cached_df = self._handle_partial_hit(
                    ticker, start_date, end_date, cached_df, file_path
                )

        if cached_df is not None and not cached_df.empty:
            # Return only the requested date range
            mask = (cached_df.index.date >= start_date) & (
                cached_df.index.date <= end_date
            )
            return cached_df.loc[mask].copy()

        return None

    def _download_and_save_full(
        self,
        ticker: str,
        start_date: datetime.date,
        end_date: datetime.date,
        file_path: str,
    ) -> pd.DataFrame:
        df = self._download_from_yf(
            ticker, start_date, end_date + datetime.timedelta(days=1)
        )
        if df is not None and not df.empty:
            df.to_json(file_path, orient="table")
        return df

    def _download_from_yf(
        self, ticker: str, start_date: datetime.date, end_date: datetime.date
    ) -> pd.DataFrame:
        try:
            df = yf.download(ticker, start=start_date, end=end_date)
            if df.empty:
                return None
            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error downloading data for {ticker}: {e}")
            return None


# Global cache instance
_cache = StockDataCache()


def load_data(
    ticker: str, start_date: datetime.date, end_date: datetime.date
) -> pd.DataFrame:
    """Fetches historical stock data from Yahoo Finance, utilizing a local cache."""
    return _cache.get_data(ticker, start_date, end_date)


def apply_strategy(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Applies the selected trading strategy and calculates indicators."""
    if strategy in STRATEGIES:
        return STRATEGIES[strategy]["apply_strategy"](df)
    return df


def _create_trade_record(entry_date, exit_date, entry_price, exit_price):
    """Creates a dictionary representing a completed or open trade."""
    return {
        "entry_date": entry_date,
        "exit_date": exit_date,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "profit": exit_price - entry_price,
        "profit_pct": (
            (exit_price - entry_price) / entry_price * 100 if entry_price > 0 else 0
        ),
    }


class _TradeEvaluator:
    def __init__(self, initial_capital):
        self.capital = initial_capital
        self.position_size = 0
        self.buy_price = 0
        self.buy_date = None
        self.trades_history = []

    def process_buy(self, date, price):
        """Processes a buy signal."""
        if self.capital > price > 0:
            shares_to_buy = self.capital // price
            self.position_size += shares_to_buy
            self.capital -= shares_to_buy * price
            self.buy_price = price
            self.buy_date = date

    def process_sell(self, date, price):
        """Processes a sell signal."""
        if self.position_size > 0:
            self.capital += self.position_size * price
            self.trades_history.append(
                _create_trade_record(self.buy_date, date, self.buy_price, price)
            )
            self.position_size = 0
            self.buy_price = 0
            self.buy_date = None

    def close_open_position(self, exit_date, exit_price):
        """Closes any open position at the end of the testing period."""
        if self.position_size > 0:
            self.capital += self.position_size * exit_price
            self.trades_history.append(
                _create_trade_record(
                    self.buy_date, exit_date, self.buy_price, exit_price
                )
            )


def _evaluate_trade_sequence(df, initial_capital, exit_date, exit_price):
    evaluator = _TradeEvaluator(initial_capital)

    # PERFORMANCE OPTIMIZATION: A true paradigm shift to vectorized operations is not completely
    # possible due to the stateful nature of integer fractional share capital calculation
    # (`shares_to_buy = capital // price`). However, we can use a significantly faster array
    # iteration over pandas core properties.
    dates = df.index
    closes = df["Close"].values
    positions = df["Position"].values

    for date_val, close_val, pos_val in zip(dates, closes, positions):
        if pos_val == 1.0:
            evaluator.process_buy(date_val, close_val)
        elif pos_val == -1.0:
            evaluator.process_sell(date_val, close_val)

    evaluator.close_open_position(exit_date, exit_price)

    return evaluator.capital, evaluator.trades_history


def _compile_performance_metrics(initial_capital, final_capital, trades_history):
    trades = len(trades_history)
    winning_trades = 0
    total_profit_pct = 0.0

    # PERFORMANCE OPTIMIZATION: A single loop to compute the count of winning
    # trades and average return avoids multiple duplicate passes over the trades list
    # (previously O(2N) using sum() comprehension logic, now O(N)).
    for t in trades_history:
        if t["profit"] > 0:
            winning_trades += 1
        total_profit_pct += t["profit_pct"]

    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    win_rate = (winning_trades / trades * 100) if trades > 0 else 0
    avg_return = (total_profit_pct / trades) if trades > 0 else 0

    return {
        "Total Return": round(total_return / 100, 4),
        "Average Return": round(avg_return / 100, 4),
        "Number of Trades": trades,
        "Win Rate": round(win_rate / 100, 4),
        "Trades History": trades_history,
    }


def _has_valid_signals(df: pd.DataFrame) -> bool:
    """Checks if the dataframe contains valid signals for backtesting."""
    if df.empty:
        return False
    if "Position" not in df.columns or "Close" not in df.columns:
        return False
    # Optimized check to avoid full column summation
    if not (df["Position"] != 0).any():
        return False
    return True


def calculate_metrics(df: pd.DataFrame, strategy: str) -> dict:  # pylint: disable=unused-argument
    """Calculates basic performance metrics from the generated signals."""
    if not _has_valid_signals(df):
        return {
            "Total Return": 0.0,
            "Average Return": 0.0,
            "Number of Trades": 0,
            "Win Rate": 0.0,
            "Trades History": [],
        }

    initial_capital = 10000.0

    # Store exit info before filtering
    exit_price = df["Close"].iat[-1]
    exit_date = df.index[-1]

    # Filter out rows with no position changes to avoid iterating through them
    active_df = df[df["Position"] != 0.0]

    # Extremely simplified backtest loop just for display metrics
    final_capital, trades_history = _evaluate_trade_sequence(
        active_df, initial_capital, exit_date, exit_price
    )

    return _compile_performance_metrics(initial_capital, final_capital, trades_history)


# Initialize Persistence Layer
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
stats_manager = StatsManager(JsonStatsStorage(STATS_FILE))


# Date helpers
def get_date_ranges():
    """Returns a dictionary with common date ranges and configurations."""
    max_date = datetime.date.today()
    min_date = max_date - datetime.timedelta(days=365 * 5)
    default_start = max_date - datetime.timedelta(days=365)

    return {
        "max_date": max_date,
        "min_date": min_date,
        "default_start": default_start,
        "min_date_ord": min_date.toordinal(),
        "max_date_ord": max_date.toordinal(),
        "default_start_ord": default_start.toordinal(),
        "step_ord": 180,  # ~6 months interval
    }
