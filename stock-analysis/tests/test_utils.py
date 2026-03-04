import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import datetime

from utils import calculate_metrics, load_data

class TestLoadData(unittest.TestCase):
    @patch('utils._cache')
    def test_load_data_returns_dataframe(self, mock_cache):
        # Arrange
        ticker = "AAPL"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        expected_df = pd.DataFrame({'Close': [150, 155]}, index=pd.date_range(start_date, periods=2))
        mock_cache.get_data.return_value = expected_df

        # Act
        result = load_data(ticker, start_date, end_date)

        # Assert
        mock_cache.get_data.assert_called_once_with(ticker, start_date, end_date)
        pd.testing.assert_frame_equal(result, expected_df)

    @patch('utils._cache')
    def test_load_data_returns_none(self, mock_cache):
        # Arrange
        ticker = "INVALID"
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)

        mock_cache.get_data.return_value = None

        # Act
        result = load_data(ticker, start_date, end_date)

        # Assert
        mock_cache.get_data.assert_called_once_with(ticker, start_date, end_date)
        self.assertIsNone(result)


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