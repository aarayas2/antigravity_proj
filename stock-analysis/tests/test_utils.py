import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import datetime

from utils import calculate_metrics, load_data

class TestLoadData(unittest.TestCase):
    @patch('utils.yf.download')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_load_data_fetches_and_caches(self, mock_exists, mock_makedirs, mock_download):
        from utils import StockDataCache, load_data
        import utils

        # Simulate cache miss by mocking os.path.exists
        mock_exists.return_value = False

        # Override the global _cache with a fresh instance so we can intercept yfinance
        with patch('utils._cache', StockDataCache(data_dir='test_data')):
            ticker = "AAPL"
            start_date = datetime.date(2023, 1, 1)
            end_date = datetime.date(2023, 1, 10)

            # Create dummy data from yfinance
            expected_df = pd.DataFrame({'Close': [150, 155]}, index=pd.date_range(start_date, periods=2))
            mock_download.return_value = expected_df

            # Mock DataFrame.to_json to avoid writing to disk during test
            with patch('pandas.DataFrame.to_json') as mock_to_json:
                result = load_data(ticker, start_date, end_date)

                # Verify that yfinance was called correctly
                mock_download.assert_called_once_with(ticker, start=start_date, end=end_date + datetime.timedelta(days=1))

                # Verify that to_json was called to save the cache
                mock_to_json.assert_called_once()

                # Verify the result is the expected dataframe
                pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    @patch('utils.yf.download')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_load_data_returns_none_on_empty(self, mock_exists, mock_makedirs, mock_download):
        from utils import StockDataCache, load_data

        # Simulate cache miss
        mock_exists.return_value = False

        with patch('utils._cache', StockDataCache(data_dir='test_data')):
            ticker = "INVALID"
            start_date = datetime.date(2023, 1, 1)
            end_date = datetime.date(2023, 1, 10)

            # Simulate empty dataframe from yfinance
            mock_download.return_value = pd.DataFrame()

            result = load_data(ticker, start_date, end_date)

            mock_download.assert_called_once()
            self.assertIsNone(result)


class TestCalculateMetrics(unittest.TestCase):
    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = calculate_metrics(df, "dummy_strategy")
        self.assertEqual(result['Total Return'], '0.00%')
        self.assertEqual(result['Number of Trades'], 0)

    def test_backtesting_loop_trades(self):
        dates = pd.date_range('2023-01-01', periods=5)
        # capital starts at 10000.0
        # Buy on day 1 (price 100): buy 100 shares. Capital: 0.
        # Sell on day 3 (price 150): sell 100 shares. Capital: 15000.
        # Buy on day 4 (price 100): buy 150 shares. Capital: 0.
        # Sell on day 5 (price 200): sell 150 shares. Capital: 30000.
        df = pd.DataFrame({
            'Close': [100, 120, 150, 100, 200],
            'Position': [1.0, 0.0, -1.0, 1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 2)
        # Total return should be (30000 - 10000) / 10000 * 100 = 200%
        self.assertEqual(result['Total Return'], '200.00%')
        self.assertEqual(result['Win Rate'], '100.00%')

        # trade 1 profit pct: (150-100)/100 = 50%
        # trade 2 profit pct: (200-100)/100 = 100%
        # avg = 75%
        self.assertEqual(result['Average Return'], '75.00%')

        trades = result['Trades History']
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0]['entry_price'], 100)
        self.assertEqual(trades[0]['exit_price'], 150)
        self.assertEqual(trades[1]['entry_price'], 100)
        self.assertEqual(trades[1]['exit_price'], 200)

    def test_sell_without_position(self):
        dates = pd.date_range('2023-01-01', periods=2)
        df = pd.DataFrame({
            'Close': [100, 150],
            'Position': [-1.0, 0.0]  # Try to sell without buying
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], '0.00%')
        self.assertEqual(result['Trades History'], [])

    def test_missing_position_column(self):
        df = pd.DataFrame({'Close': [100, 105, 110]})
        result = calculate_metrics(df, "dummy_strategy")
        self.assertEqual(result['Total Return'], '0.00%')
        self.assertEqual(result['Number of Trades'], 0)

    def test_no_trades(self):
        df = pd.DataFrame({'Close': [100, 105, 110], 'Position': [0, 0, 0]})
        result = calculate_metrics(df, "dummy_strategy")
        self.assertEqual(result['Total Return'], '0.00%')
        self.assertEqual(result['Number of Trades'], 0)

    def test_single_winning_trade(self):
        dates = pd.date_range('2023-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100, 110, 105],
            'Position': [1.0, -1.0, 0.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], '10.00%')
        self.assertEqual(result['Win Rate'], '100.00%')
        self.assertEqual(result['Average Return'], '10.00%')

    def test_single_losing_trade(self):
        dates = pd.date_range('2023-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100, 90, 95],
            'Position': [1.0, -1.0, 0.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], '-10.00%')
        self.assertEqual(result['Win Rate'], '0.00%')
        self.assertEqual(result['Average Return'], '-10.00%')

    def test_multiple_trades(self):
        dates = pd.date_range('2023-01-01', periods=4)
        df = pd.DataFrame({
            'Close': [100, 120, 150, 135],
            'Position': [1.0, -1.0, 1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 2)
        self.assertEqual(result['Total Return'], '8.00%')
        self.assertEqual(result['Win Rate'], '50.00%')
        self.assertEqual(result['Average Return'], '5.00%')

    def test_open_position_at_end(self):
        dates = pd.date_range('2023-01-01', periods=2)
        df = pd.DataFrame({
            'Close': [100, 150],
            'Position': [1.0, 0.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], '50.00%')
        self.assertEqual(result['Win Rate'], '100.00%')
        self.assertEqual(result['Average Return'], '50.00%')

    def test_insufficient_capital(self):
        dates = pd.date_range('2023-01-01', periods=2)
        df = pd.DataFrame({
            'Close': [20000, 25000],
            'Position': [1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], '0.00%')
        self.assertEqual(result['Win Rate'], '0.00%')
        self.assertEqual(result['Average Return'], '0.00%')

    def test_zero_buy_price(self):
        dates = pd.date_range('2023-01-01', periods=2)
        df = pd.DataFrame({
            'Close': [0.0, 150.0],
            'Position': [1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], '0.00%')
        self.assertEqual(result['Win Rate'], '0.00%')
        self.assertEqual(result['Average Return'], '0.00%')

    def test_zero_exit_price_and_buy_price(self):
        dates = pd.date_range('2023-01-01', periods=2)
        # Force a case where buy_price could be 0, but since price > 0 is required,
        # it shouldn't buy. Let's test a valid buy, but sell price is 0.
        df = pd.DataFrame({
            'Close': [100.0, 0.0],
            'Position': [1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], '-100.00%')
        self.assertEqual(result['Win Rate'], '0.00%')
        self.assertEqual(result['Average Return'], '-100.00%')

    def test_calculate_metrics_happy_path(self):
        """
        Happy path test: Buying at a normal price, and selling at a higher price
        to verify standard behavior.
        """
        dates = pd.date_range('2024-01-01', periods=3)
        # Day 1: Price 100, Buy 100 shares (10000 capital)
        # Day 2: Price 120, Hold
        # Day 3: Price 150, Sell 100 shares -> 15000 capital
        df = pd.DataFrame({
            'Close': [100.0, 120.0, 150.0],
            'Position': [1.0, 0.0, -1.0]
        }, index=dates)

        result = calculate_metrics(df, "happy_path_strategy")

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], '50.00%')
        self.assertEqual(result['Win Rate'], '100.00%')
        self.assertEqual(result['Average Return'], '50.00%')

        trades = result['Trades History']
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['entry_price'], 100.0)
        self.assertEqual(trades[0]['exit_price'], 150.0)
        self.assertEqual(trades[0]['profit'], 50.0)
        self.assertEqual(trades[0]['profit_pct'], 50.0)

    def test_consecutive_buys_and_sells(self):
        """
        Tests behavior when multiple buy signals arrive sequentially without sell signals,
        and multiple sell signals arrive sequentially without buy signals.
        """
        dates = pd.date_range('2024-01-01', periods=6)
        # Capital: 10000
        # Day 1: Buy @ 100 -> 100 shares, capital 0
        # Day 2: Buy @ 50 -> Ignored because capital 0
        # Day 3: Sell @ 150 -> 100 shares sold, capital 15000
        # Day 4: Sell @ 160 -> Ignored because position_size 0
        # Day 5: Buy @ 100 -> 150 shares, capital 0
        # Day 6: Hold (Open position at end)
        df = pd.DataFrame({
            'Close': [100.0, 50.0, 150.0, 160.0, 100.0, 200.0],
            'Position': [1.0, 1.0, -1.0, -1.0, 1.0, 0.0]
        }, index=dates)

        result = calculate_metrics(df, "consecutive_signals")

        self.assertEqual(result['Number of Trades'], 2)
        # Trade 1: Entry 100, Exit 150. Profit = 50. Profit Pct = 50.0%
        # Trade 2 (End): Entry 100, Exit 200. Profit = 100. Profit Pct = 100.0%
        # Wait, the second buy @ 100 happens when capital is 15000, so 150 shares bought.
        # But wait, looking at `calculate_metrics`, it filters out rows where Position is 0!
        # `df[df['Position'] != 0.0]`
        # So row 6 (Hold) is filtered out!
        # The exit info is extracted from the UNFILTERED df at the beginning:
        # exit_price = df['Close'].iat[-1] -> 200.0
        # exit_date = df.index[-1] -> Day 6
        # So it correctly closes the open position of 150 shares at 200.0.
        # So Final capital = 15000 (from previous sell) - 15000 (bought 150 * 100) + 150 * 200 = 30000
        # Total Return = (30000 - 10000) / 10000 * 100 = 200.00%
        self.assertEqual(result['Total Return'], '200.00%')
        self.assertEqual(result['Win Rate'], '100.00%')
        self.assertEqual(result['Average Return'], '75.00%')

    def test_fractional_capital_remainder(self):
        """
        Tests backtesting loop logic when capital doesn't perfectly divide by price,
        leaving a remainder of uninvested capital.
        """
        dates = pd.date_range('2024-01-01', periods=3)
        # Capital: 10000
        # Day 1: Buy @ 300 -> 33 shares (9900 used), 100 remaining
        # Day 2: Hold
        # Day 3: Sell @ 400 -> 33 * 400 = 13200 + 100 = 13300 final capital
        df = pd.DataFrame({
            'Close': [300.0, 350.0, 400.0],
            'Position': [1.0, 0.0, -1.0]
        }, index=dates)

        result = calculate_metrics(df, "fractional_capital")

        self.assertEqual(result['Number of Trades'], 1)
        # Total Return = (13300 - 10000) / 10000 * 100 = 33.00%
        self.assertEqual(result['Total Return'], '33.00%')
        self.assertEqual(result['Win Rate'], '100.00%')

        trades = result['Trades History']
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['entry_price'], 300.0)
        self.assertEqual(trades[0]['exit_price'], 400.0)
        self.assertEqual(trades[0]['profit'], 100.0)
        self.assertAlmostEqual(trades[0]['profit_pct'], 33.33333333333333)

    def test_negative_prices_handling(self):
        """
        Tests handling of negative or zero prices according to `price > 0` condition.
        """
        dates = pd.date_range('2024-01-01', periods=3)
        # Day 1: Buy @ -50 -> Should be ignored
        # Day 2: Buy @ 0 -> Should be ignored
        # Day 3: Buy @ 100 -> Should be executed
        df = pd.DataFrame({
            'Close': [-50.0, 0.0, 100.0],
            'Position': [1.0, 1.0, 1.0]
        }, index=dates)

        # Force exit price manually by checking the last row behavior
        # In actual calculate_metrics, it uses exit_price = df['Close'].iat[-1]
        # In this case exit_price is 100.0. The open position (bought at 100.0) will be closed at 100.0.
        result = calculate_metrics(df, "negative_prices")

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], '0.00%')
        trades = result['Trades History']
        self.assertEqual(trades[0]['entry_price'], 100.0)
        self.assertEqual(trades[0]['exit_price'], 100.0)
        self.assertEqual(trades[0]['profit'], 0.0)
        
class TestApplyStrategy(unittest.TestCase):
    @patch('utils.STRATEGIES')
    def test_apply_strategy_found(self, mock_strategies):
        # Arrange
        strategy_name = "test_strategy"
        df_input = pd.DataFrame({'Close': [100, 105]})
        df_output = pd.DataFrame({'Close': [100, 105], 'Signal': [1, -1]})

        mock_strategy_func = MagicMock(return_value=df_output)
        mock_strategies.__contains__.side_effect = lambda k: k == strategy_name
        mock_strategies.__getitem__.side_effect = lambda k: {"apply_strategy": mock_strategy_func}

        # Act
        from utils import apply_strategy
        result = apply_strategy(df_input, strategy_name)

        # Assert
        mock_strategy_func.assert_called_once_with(df_input)
        pd.testing.assert_frame_equal(result, df_output)

    @patch('utils.STRATEGIES')
    def test_apply_strategy_not_found(self, mock_strategies):
        # Arrange
        strategy_name = "unknown_strategy"
        df_input = pd.DataFrame({'Close': [100, 105]})

        mock_strategies.__contains__.side_effect = lambda k: False

        # Act
        from utils import apply_strategy
        result = apply_strategy(df_input, strategy_name)

        # Assert
        pd.testing.assert_frame_equal(result, df_input)

class TestStockDataCache(unittest.TestCase):
    @patch('utils.yf.download')
    def test_download_from_yf_success(self, mock_download):
        from utils import _cache
        import datetime
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        expected_df = pd.DataFrame({'Close': [150, 155]})
        mock_download.return_value = expected_df

        result = _cache._download_from_yf(ticker, start_date, end_date)

        mock_download.assert_called_once_with(ticker, start=start_date, end=end_date)
        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    @patch('utils.yf.download')
    def test_download_from_yf_empty(self, mock_download):
        from utils import _cache
        import datetime
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        expected_df = pd.DataFrame()
        mock_download.return_value = expected_df

        result = _cache._download_from_yf(ticker, start_date, end_date)

        mock_download.assert_called_once_with(ticker, start=start_date, end=end_date)
        self.assertIsNone(result)

    @patch('utils.yf.download')
    def test_download_from_yf_multiindex(self, mock_download):
        from utils import _cache
        import datetime
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        # Create a DataFrame with a MultiIndex column
        arrays = [['Close', 'Close'], ['AAPL', 'MSFT']]
        tuples = list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples, names=['Price', 'Ticker'])
        expected_df = pd.DataFrame([[150, 200]], columns=index)

        mock_download.return_value = expected_df

        result = _cache._download_from_yf(ticker, start_date, end_date)

        mock_download.assert_called_once_with(ticker, start=start_date, end=end_date)
        # Expected column index is a simple Index of the top level
        expected_columns = pd.Index(['Close', 'Close'], name='Price')
        pd.testing.assert_index_equal(result.columns, expected_columns)

    @patch('utils.yf.download')
    def test_download_from_yf_exception(self, mock_download):
        from utils import _cache
        import datetime
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        mock_download.side_effect = Exception("Download failed")

        result = _cache._download_from_yf(ticker, start_date, end_date)

        mock_download.assert_called_once_with(ticker, start=start_date, end=end_date)
        self.assertIsNone(result)


    @patch('utils.pd.read_json')
    @patch('utils.os.path.exists')
    @patch('utils.pd.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_miss_downloads_full(self, mock_download, mock_to_json, mock_exists, mock_read_json):
        from utils import StockDataCache
        import datetime

        cache = StockDataCache(data_dir='test_data')
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        # Simulate cache miss
        mock_exists.return_value = False

        expected_df = pd.DataFrame({'Close': [150, 155]}, index=pd.date_range(start_date, periods=2))
        mock_download.return_value = expected_df

        result = cache.get_data(ticker, start_date, end_date)

        mock_download.assert_called_once()
        mock_to_json.assert_called_once()
        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    @patch('utils.pd.read_json')
    @patch('utils.os.path.exists')
    @patch('utils.pd.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_hit_all_data_local(self, mock_download, mock_to_json, mock_exists, mock_read_json):
        from utils import StockDataCache
        import datetime

        cache = StockDataCache(data_dir='test_data')
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 2)
        end_date = datetime.date(2023, 1, 9)

        mock_exists.return_value = True

        # Cache contains data from 1-1 to 1-10
        cache_dates = pd.date_range(datetime.date(2023, 1, 1), datetime.date(2023, 1, 10))
        cached_df = pd.DataFrame({'Close': range(10)}, index=cache_dates)
        mock_read_json.return_value = cached_df

        result = cache.get_data(ticker, start_date, end_date)

        # Should not download or save
        mock_download.assert_not_called()
        mock_to_json.assert_not_called()

        # Result should be subset of cached_df
        expected_dates = pd.date_range(start_date, end_date)
        expected_df = pd.DataFrame({'Close': range(1, 9)}, index=expected_dates)
        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    @patch('utils.pd.read_json')
    @patch('utils.os.path.exists')
    @patch('utils.pd.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_hit_needs_older_data(self, mock_download, mock_to_json, mock_exists, mock_read_json):
        from utils import StockDataCache
        import datetime

        cache = StockDataCache(data_dir='test_data')
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        mock_exists.return_value = True

        # Cache contains data from 1-5 to 1-10
        cache_dates = pd.date_range(datetime.date(2023, 1, 5), datetime.date(2023, 1, 10))
        cached_df = pd.DataFrame({'Close': range(5, 11)}, index=cache_dates)
        mock_read_json.return_value = cached_df

        # Download returns older data
        older_dates = pd.date_range(datetime.date(2023, 1, 1), datetime.date(2023, 1, 4))
        older_df = pd.DataFrame({'Close': range(1, 5)}, index=older_dates)
        mock_download.return_value = older_df

        result = cache.get_data(ticker, start_date, end_date)

        # Should download older data and save
        mock_download.assert_called_once()
        mock_to_json.assert_called_once()

        expected_dates = pd.date_range(start_date, end_date)
        expected_df = pd.DataFrame({'Close': range(1, 11)}, index=expected_dates)
        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    @patch('utils.pd.read_json')
    @patch('utils.os.path.exists')
    @patch('utils.pd.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_hit_needs_newer_data(self, mock_download, mock_to_json, mock_exists, mock_read_json):
        from utils import StockDataCache
        import datetime

        cache = StockDataCache(data_dir='test_data')
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        mock_exists.return_value = True

        # Cache contains data from 1-1 to 1-5
        cache_dates = pd.date_range(datetime.date(2023, 1, 1), datetime.date(2023, 1, 5))
        cached_df = pd.DataFrame({'Close': range(1, 6)}, index=cache_dates)
        mock_read_json.return_value = cached_df

        # Download returns newer data
        newer_dates = pd.date_range(datetime.date(2023, 1, 6), datetime.date(2023, 1, 10))
        newer_df = pd.DataFrame({'Close': range(6, 11)}, index=newer_dates)
        mock_download.return_value = newer_df

        result = cache.get_data(ticker, start_date, end_date)

        # Should download newer data and save
        mock_download.assert_called_once()
        mock_to_json.assert_called_once()

        expected_dates = pd.date_range(start_date, end_date)
        expected_df = pd.DataFrame({'Close': range(1, 11)}, index=expected_dates)
        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    @patch('utils.pd.read_json')
    @patch('utils.os.path.exists')
    @patch('utils.pd.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_hit_needs_older_and_newer_data(self, mock_download, mock_to_json, mock_exists, mock_read_json):
        from utils import StockDataCache
        import datetime

        cache = StockDataCache(data_dir='test_data')
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        mock_exists.return_value = True

        # Cache contains data from 1-4 to 1-7
        cache_dates = pd.date_range(datetime.date(2023, 1, 4), datetime.date(2023, 1, 7))
        cached_df = pd.DataFrame({'Close': range(4, 8)}, index=cache_dates)
        mock_read_json.return_value = cached_df

        # Download returns older and newer data
        older_dates = pd.date_range(datetime.date(2023, 1, 1), datetime.date(2023, 1, 3))
        older_df = pd.DataFrame({'Close': range(1, 4)}, index=older_dates)
        newer_dates = pd.date_range(datetime.date(2023, 1, 8), datetime.date(2023, 1, 10))
        newer_df = pd.DataFrame({'Close': range(8, 11)}, index=newer_dates)

        mock_download.side_effect = [older_df, newer_df]

        result = cache.get_data(ticker, start_date, end_date)

        # Should download twice and save
        self.assertEqual(mock_download.call_count, 2)
        mock_to_json.assert_called_once()

        expected_dates = pd.date_range(start_date, end_date)
        expected_df = pd.DataFrame({'Close': range(1, 11)}, index=expected_dates)
        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    @patch('utils.pd.read_json')
    @patch('utils.os.path.exists')
    @patch('utils.pd.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_hit_empty_file(self, mock_download, mock_to_json, mock_exists, mock_read_json):
        from utils import StockDataCache
        import datetime

        cache = StockDataCache(data_dir='test_data')
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        mock_exists.return_value = True

        # Cache file empty
        mock_read_json.return_value = pd.DataFrame()

        expected_df = pd.DataFrame({'Close': [150, 155]}, index=pd.date_range(start_date, periods=2))
        mock_download.return_value = expected_df

        result = cache.get_data(ticker, start_date, end_date)

        mock_download.assert_called_once()
        mock_to_json.assert_called_once()
        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    @patch('utils.pd.read_json')
    @patch('utils.os.path.exists')
    @patch('utils.pd.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_read_exception(self, mock_download, mock_to_json, mock_exists, mock_read_json):
        from utils import StockDataCache
        import datetime

        cache = StockDataCache(data_dir='test_data')
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        mock_exists.return_value = True

        # Raise exception during read
        mock_read_json.side_effect = Exception("Corrupt file")

        expected_df = pd.DataFrame({'Close': [150, 155]}, index=pd.date_range(start_date, periods=2))
        mock_download.return_value = expected_df

        result = cache.get_data(ticker, start_date, end_date)

        mock_download.assert_called_once()
        mock_to_json.assert_called_once()
        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

    def test_get_file_path_invalid_ticker(self):
        from utils import StockDataCache
        cache = StockDataCache(data_dir='test_data')
        # The path traversal check should just sanitize the ticker, not raise ValueError
            # Pass a path traversal string
        path = cache._get_file_path("../../../etc/passwd")
        self.assertTrue(path.endswith("......etcpasswd.json"))


    @patch('utils.os.path.abspath')
    def test_get_file_path_invalid_ticker_abspath_mock(self, mock_abspath):
        from utils import StockDataCache
        import os
        cache = StockDataCache(data_dir='test_data')

        # We need to mock abspath carefully to trigger the ValueError
        # but the first call to abspath happens in __init__ (wait, we already initialized)
        # Actually, let's just make the final_path check fail
        def side_effect(path):
            if path.endswith('.json'):
                return '/tmp/malicious/path.json'
            return '/tmp/legit/data_dir'

        mock_abspath.side_effect = side_effect

        with self.assertRaises(ValueError):
            cache._get_file_path("some_ticker")

    @patch('utils.os.path.abspath')
    def test_get_file_path_invalid_ticker_abspath_mock2(self, mock_abspath):
        from utils import StockDataCache

        # We need to test the ValueError branch in _get_file_path
        # final_path = os.path.abspath(os.path.join(self.data_dir, f"{sanitized_ticker}.json"))
        # if not final_path.startswith(os.path.abspath(self.data_dir)): raise ValueError(...)

        # When _get_file_path calls abspath, we want it to return different values
        def abspath_side_effect(path):
            if path.endswith('.json'):
                return '/tmp/malicious/file.json'
            return '/tmp/legit/dir'

        mock_abspath.side_effect = abspath_side_effect

        cache = StockDataCache(data_dir='test_data')
        with self.assertRaises(ValueError):
            cache._get_file_path("test")
if __name__ == '__main__':
    unittest.main()
