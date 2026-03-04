import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import pandas as pd
from datetime import datetime

from utils import calculate_metrics

class TestCalculateMetrics(unittest.TestCase):
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

if __name__ == '__main__':
    unittest.main()