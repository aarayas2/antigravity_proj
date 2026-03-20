import sys
import os
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import calculate_metrics

class TestCalculateMetricsBacktestingLoop(unittest.TestCase):
    def test_calculate_metrics_no_position_column(self):
        df = pd.DataFrame({'Close': [100.0, 105.0]})
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Total Return'], 0.0)
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Trades History'], [])

    def test_calculate_metrics_no_close_column(self):
        df = pd.DataFrame({'Position': [1.0, 1.0]})
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Total Return'], 0.0)
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Trades History'], [])

    def test_calculate_metrics_empty_dataframe(self):
        df = pd.DataFrame()
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Total Return'], 0.0)
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Trades History'], [])

    def test_calculate_metrics_no_trades_taken(self):
        dates = pd.date_range('2023-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100.0, 105.0, 110.0],
            'Position': [0.0, 0.0, 0.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Total Return'], 0.0)
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Trades History'], [])

    def test_calculate_metrics_single_winning_trade(self):
        dates = pd.date_range('2023-01-01', periods=3)
        # Day 1: Buy @ 100 -> 100 shares bought (capital drops from 10000 to 0)
        # Day 2: Hold @ 110
        # Day 3: Sell @ 150 -> 100 shares sold (capital becomes 15000)
        df = pd.DataFrame({
            'Close': [100.0, 110.0, 150.0],
            'Position': [1.0, 0.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], 0.5)
        self.assertEqual(result['Win Rate'], 1.0)
        self.assertEqual(result['Average Return'], 0.5)
        self.assertEqual(len(result['Trades History']), 1)
        self.assertEqual(result['Trades History'][0]['entry_price'], 100.0)
        self.assertEqual(result['Trades History'][0]['exit_price'], 150.0)

    def test_calculate_metrics_single_losing_trade(self):
        dates = pd.date_range('2023-01-01', periods=3)
        # Day 1: Buy @ 100 -> 100 shares
        # Day 2: Hold @ 90
        # Day 3: Sell @ 50 -> 100 shares sold (capital becomes 5000)
        df = pd.DataFrame({
            'Close': [100.0, 90.0, 50.0],
            'Position': [1.0, 0.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], -0.5)
        self.assertEqual(result['Win Rate'], 0.0)
        self.assertEqual(result['Average Return'], -0.5)
        self.assertEqual(result['Trades History'][0]['profit'], -50.0)

    def test_calculate_metrics_multiple_trades(self):
        dates = pd.date_range('2023-01-01', periods=5)
        # Day 1: Buy @ 100 -> 100 shares (Capital: 0)
        # Day 2: Sell @ 150 -> 100 shares (Capital: 15000)
        # Day 3: Hold @ 100 -> Position: 0
        # Day 4: Buy @ 150 -> 100 shares (Capital: 0)
        # Day 5: Sell @ 180 -> 100 shares (Capital: 18000)
        df = pd.DataFrame({
            'Close': [100.0, 150.0, 100.0, 150.0, 180.0],
            'Position': [1.0, -1.0, 0.0, 1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')

        self.assertEqual(result['Number of Trades'], 2)
        # Profit trade 1: (150-100)/100 = 50%
        # Profit trade 2: (180-150)/150 = 20%
        # Total Return: (18000-10000)/10000 = 80%
        # Avg Return: (50 + 20) / 2 = 35%
        self.assertEqual(result['Total Return'], 0.8)
        self.assertEqual(result['Win Rate'], 1.0)
        self.assertEqual(result['Average Return'], 0.35)

    def test_calculate_metrics_open_trade_at_end(self):
        dates = pd.date_range('2023-01-01', periods=2)
        # Day 1: Buy @ 100 -> 100 shares (Capital: 0)
        # Day 2: Hold @ 200 -> Position: 0 (Ends as open position)
        df = pd.DataFrame({
            'Close': [100.0, 200.0],
            'Position': [1.0, 0.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], 1.0)
        self.assertEqual(result['Win Rate'], 1.0)
        self.assertEqual(result['Average Return'], 1.0)

    def test_calculate_metrics_sell_without_buy(self):
        dates = pd.date_range('2023-01-01', periods=2)
        # Selling before buying should be ignored
        df = pd.DataFrame({
            'Close': [100.0, 200.0],
            'Position': [-1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')

        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], 0.0)

    def test_calculate_metrics_zero_or_negative_price(self):
        dates = pd.date_range('2023-01-01', periods=3)
        # Buying at price 0 or negative should be ignored due to price > 0 check
        df = pd.DataFrame({
            'Close': [0.0, -50.0, 100.0],
            'Position': [1.0, 1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')

        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], 0.0)

    def test_calculate_metrics_fractional_capital(self):
        dates = pd.date_range('2023-01-01', periods=3)
        # Capital 10000
        # Buy @ 300 -> 33 shares (9900 cost), 100 capital remaining
        # Sell @ 400 -> 33 * 400 = 13200 + 100 = 13300 total capital
        df = pd.DataFrame({
            'Close': [300.0, 350.0, 400.0],
            'Position': [1.0, 0.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')

        self.assertEqual(result['Number of Trades'], 1)
        # Total Return: (13300 - 10000) / 10000 = 33%
        self.assertEqual(result['Total Return'], 0.33)


    def test_calculate_metrics_buy_without_sell_then_close(self):
        dates = pd.date_range('2023-01-01', periods=3)
        # Buy @ 100, then hold, but no explicit sell. Closed out at exit_price.
        df = pd.DataFrame({
            'Close': [100.0, 110.0, 120.0],
            'Position': [1.0, 0.0, 0.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Number of Trades'], 1)
        # Entry 100, Exit 120 => 20% return.

    def test_calculate_metrics_fractional_shares_large_price(self):
        dates = pd.date_range('2023-01-01', periods=3)
        # Price is higher than capital, so shares_to_buy = 0
        df = pd.DataFrame({
            'Close': [20000.0, 21000.0, 22000.0],
            'Position': [1.0, 0.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], 0.0)

    def test_calculate_metrics_multiple_trades_same_position(self):
        dates = pd.date_range('2023-01-01', periods=4)
        # Sequence of duplicate position signals
        df = pd.DataFrame({
            'Close': [100.0, 110.0, 120.0, 150.0],
            'Position': [1.0, 1.0, -1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Number of Trades'], 1)
        # Entry 100, Exit 120 => 20% return. The second 1.0 is ignored since capital < price
        # The second -1.0 is ignored since position_size = 0
        self.assertEqual(result['Total Return'], 0.2)

    def test_calculate_metrics_buy_hold_scenario(self):
        """
        Tests backtesting loop logic for a simple buy and hold scenario,
        to ensure Total Return and Number of Trades are calculated correctly
        even when the trade is open at the end.
        """
        dates = pd.date_range('2024-01-01', periods=4)
        # Day 1: Buy @ 100 -> 100 shares, capital drops from 10000 to 0
        # Day 2: Hold @ 120
        # Day 3: Hold @ 130
        # Day 4: Hold @ 150 -> position open, exit_price = 150
        df = pd.DataFrame({
            'Close': [100.0, 120.0, 130.0, 150.0],
            'Position': [1.0, 0.0, 0.0, 0.0]
        }, index=dates)

        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], 0.5)
        self.assertEqual(result['Win Rate'], 1.0)
        self.assertEqual(result['Average Return'], 0.5)

    def test_calculate_metrics_all_zero_positions(self):
        """
        Tests backtesting loop when there are only zeros in the Position column.
        The function should return the default zero-filled dictionary without doing full loop.
        """
        dates = pd.date_range('2024-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100.0, 105.0, 110.0],
            'Position': [0.0, 0.0, 0.0]
        }, index=dates)

        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Total Return'], 0.0)
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Trades History'], [])

    def test_calculate_metrics_invalid_position_value(self):
        """
        Tests backtesting loop when there are unknown non-zero positions like 0.5.
        The function should simply ignore these invalid signals and not crash.
        """
        dates = pd.date_range('2024-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100.0, 105.0, 110.0],
            'Position': [0.5, -0.5, 2.0]
        }, index=dates)

        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Total Return'], 0.0)
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Trades History'], [])

class TestCalculateMetricsBacktestingLoopExtended(unittest.TestCase):
    def test_calculate_metrics_with_nan_values(self):
        """Test how backtesting handles NaN in Close or Position."""
        dates = pd.date_range('2024-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100.0, np.nan, 150.0],
            'Position': [1.0, 0.0, -1.0]
        }, index=dates)

        # Position is 1.0, so buy at 100.0 -> 100 shares.
        # Position is 0.0 at NaN, so it does nothing.
        # Position is -1.0, so sell at 150.0 -> 100 shares sold.
        result = calculate_metrics(df, "dummy")

        self.assertEqual(result['Number of Trades'], 1)
        self.assertEqual(result['Total Return'], 0.5)

    def test_compile_performance_metrics_empty_trades(self):
        """Passing an empty list [] to _compile_performance_metrics is a trivial 5-line test."""
        from utils import _compile_performance_metrics
        result = _compile_performance_metrics(10000.0, 10000.0, [])
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], 0.0)

    def test_calculate_metrics_empty_active_df_but_valid(self):
        """Test when the DataFrame is valid but has no active positions, ensuring it doesn't crash."""
        dates = pd.date_range('2024-01-01', periods=2)
        df = pd.DataFrame({
            'Close': [100.0, 100.0],
            'Position': [0.0, 0.0]
        }, index=dates)
        result = calculate_metrics(df, "dummy")
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], 0.0)

    def test_calculate_metrics_string_strategy_is_ignored(self):
        """Ensure the strategy string parameter doesn't alter the simple metric calculation."""
        dates = pd.date_range('2024-01-01', periods=2)
        df = pd.DataFrame({
            'Close': [100.0, 200.0],
            'Position': [1.0, -1.0]
        }, index=dates)
        result1 = calculate_metrics(df, "StrategyA")
        result2 = calculate_metrics(df, "StrategyB")
        self.assertEqual(result1, result2)
        self.assertEqual(result1['Total Return'], 1.0)

if __name__ == '__main__':
    unittest.main()
