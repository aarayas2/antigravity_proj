import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import pandas as pd
from utils import calculate_metrics

class TestCalculateMetricsBacktestingLoop(unittest.TestCase):
    """
    Specifically tests the backtesting loop within `calculate_metrics`
    to fulfill the testing gap. The function takes a simple DataFrame
    and a strategy string, and returns a dictionary of metrics.
    """

    def test_calculate_metrics_backtesting_loop(self):
        # The logic can be easily tested by passing a mock DataFrame with known positions.
        dates = pd.date_range('2023-01-01', periods=5)
        # Mock DataFrame with known positions
        df = pd.DataFrame({
            'Close': [100.0, 110.0, 120.0, 105.0, 130.0],
            'Position': [1.0, 0.0, -1.0, 1.0, -1.0]
        }, index=dates)

        # Initial capital: 10000.0
        # Trade 1:
        # Buy at 100.0 -> Shares: 100, Capital: 0.0
        # Sell at 120.0 -> Shares: 0, Capital: 12000.0 (Profit: 2000, 20%)
        # Trade 2:
        # Buy at 105.0 -> Shares: 114 (12000 // 105), Capital: 12000 - (114 * 105) = 12000 - 11970 = 30.0
        # Sell at 130.0 -> Shares: 0, Capital: 30.0 + (114 * 130) = 30.0 + 14820 = 14850.0
        # Total profit: 4850.0 -> 48.5% total return

        metrics = calculate_metrics(df, "mock_strategy")

        self.assertEqual(metrics['Number of Trades'], 2)
        self.assertEqual(metrics['Total Return'], '48.50%')
        self.assertEqual(metrics['Win Rate'], '100.00%')
        # Average Return: Trade 1 profit% = 20%, Trade 2 profit% = (130-105)/105 * 100 = 23.8095%
        # Average = 43.8095 / 2 = 21.90%
        self.assertEqual(metrics['Average Return'], '21.90%')

    def test_calculate_metrics_empty_dataframe(self):
        # Edge Case: Empty DataFrame
        df = pd.DataFrame()
        metrics = calculate_metrics(df, "mock_strategy")
        self.assertEqual(metrics['Total Return'], "0.00%")
        self.assertEqual(metrics['Number of Trades'], 0)
        self.assertEqual(len(metrics['Trades History']), 0)

    def test_calculate_metrics_no_positions(self):
        # Edge Case: DataFrame with no trades taken
        dates = pd.date_range('2023-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100.0, 110.0, 120.0],
            'Position': [0.0, 0.0, 0.0]
        }, index=dates)
        metrics = calculate_metrics(df, "mock_strategy")
        self.assertEqual(metrics['Total Return'], "0.00%")
        self.assertEqual(metrics['Number of Trades'], 0)

    def test_calculate_metrics_open_position_at_end(self):
        # Edge Case: Trade remains open at the end of the DataFrame
        dates = pd.date_range('2023-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100.0, 110.0, 150.0],
            'Position': [1.0, 0.0, 0.0]
        }, index=dates)
        # Should simulate closing the open position at the final close price (150.0)
        # Buy at 100 -> 100 shares. Capital: 0
        # Final price 150 -> 15000 total capital. Return 50%
        metrics = calculate_metrics(df, "mock_strategy")
        self.assertEqual(metrics['Number of Trades'], 1)
        self.assertEqual(metrics['Total Return'], "50.00%")

    def test_calculate_metrics_insufficient_capital(self):
        # Edge Case: Stock price is too high to buy even 1 share with 10000 initial capital
        dates = pd.date_range('2023-01-01', periods=2)
        df = pd.DataFrame({
            'Close': [10001.0, 15000.0],
            'Position': [1.0, -1.0]
        }, index=dates)
        metrics = calculate_metrics(df, "mock_strategy")
        self.assertEqual(metrics['Number of Trades'], 0)
        self.assertEqual(metrics['Total Return'], "0.00%")

    def test_calculate_metrics_negative_prices(self):
        # Edge Case: Negative or zero prices
        dates = pd.date_range('2023-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [-10.0, 0.0, 100.0],
            'Position': [1.0, 1.0, 0.0]
        }, index=dates)
        metrics = calculate_metrics(df, "mock_strategy")
        # Ensure no divisions by zero and no invalid trades are executed
        self.assertEqual(metrics['Number of Trades'], 0)
        self.assertEqual(metrics['Total Return'], "0.00%")

if __name__ == '__main__':
    unittest.main()
