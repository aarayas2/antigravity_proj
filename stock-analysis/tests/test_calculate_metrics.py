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
        self.assertEqual(result['Total Return'], '0.00%')
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Trades History'], [])

    def test_calculate_metrics_empty_dataframe(self):
        df = pd.DataFrame()
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Total Return'], '0.00%')
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Trades History'], [])

    def test_calculate_metrics_no_trades_taken(self):
        dates = pd.date_range('2023-01-01', periods=3)
        df = pd.DataFrame({
            'Close': [100.0, 105.0, 110.0],
            'Position': [0.0, 0.0, 0.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Total Return'], '0.00%')
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
        self.assertEqual(result['Total Return'], '50.00%')
        self.assertEqual(result['Win Rate'], '100.00%')
        self.assertEqual(result['Average Return'], '50.00%')
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
        self.assertEqual(result['Total Return'], '-50.00%')
        self.assertEqual(result['Win Rate'], '0.00%')
        self.assertEqual(result['Average Return'], '-50.00%')
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
        self.assertEqual(result['Total Return'], '80.00%')
        self.assertEqual(result['Win Rate'], '100.00%')
        self.assertEqual(result['Average Return'], '35.00%')

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
        self.assertEqual(result['Total Return'], '100.00%')
        self.assertEqual(result['Win Rate'], '100.00%')
        self.assertEqual(result['Average Return'], '100.00%')

    def test_calculate_metrics_sell_without_buy(self):
        dates = pd.date_range('2023-01-01', periods=2)
        # Selling before buying should be ignored
        df = pd.DataFrame({
            'Close': [100.0, 200.0],
            'Position': [-1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], '0.00%')

    def test_calculate_metrics_zero_or_negative_price(self):
        dates = pd.date_range('2023-01-01', periods=3)
        # Buying at price 0 or negative should be ignored due to price > 0 check
        df = pd.DataFrame({
            'Close': [0.0, -50.0, 100.0],
            'Position': [1.0, 1.0, -1.0]
        }, index=dates)
        result = calculate_metrics(df, 'dummy')
        self.assertEqual(result['Number of Trades'], 0)
        self.assertEqual(result['Total Return'], '0.00%')

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
        self.assertEqual(result['Total Return'], '33.00%')

if __name__ == '__main__':
    unittest.main()
