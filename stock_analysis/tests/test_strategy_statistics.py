import unittest
from unittest.mock import patch
import pandas as pd
import sys
import os

# Add parent directory to sys.path to allow imports from pages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pages.strategy_statistics import update_stats_table, update_tickers_input

class TestStrategyStatistics(unittest.TestCase):
    @patch('pages.strategy_statistics.stats_manager._storage.read')
    def test_unique_tickers_maintains_order(self, mock_read):
        # Mock data representing a specific order of tickers
        # Notice how B appears before A
        mock_read.return_value = [
            {'TICKER_B': {
                'date-begin': '2020-01-01',
                'date-end': '2021-01-01',
                'Strategy1': {
                    'Win Rate': 0.6,
                    'Average Return': 0.05,
                    'Total Return': 0.1,
                    'Number of Trades': 2
                }
            }},
            {'TICKER_A': {
                'date-begin': '2020-01-01',
                'date-end': '2021-01-01',
                'Strategy1': {
                    'Win Rate': 0.7,
                    'Average Return': 0.06,
                    'Total Return': 0.12,
                    'Number of Trades': 3
                }
            }},
            {'TICKER_B': {
                'date-begin': '2021-01-01',
                'date-end': '2022-01-01',
                'Strategy2': {
                    'Win Rate': 0.8,
                    'Average Return': 0.07,
                    'Total Return': 0.15,
                    'Number of Trades': 4
                }
            }},
            {'TICKER_C': {
                'date-begin': '2020-01-01',
                'date-end': '2021-01-01',
                'Strategy1': {
                    'Win Rate': 0.9,
                    'Average Return': 0.08,
                    'Total Return': 0.2,
                    'Number of Trades': 5
                }
            }}
        ]

        # Call with 0% win rate filter to include all
        table = update_stats_table(0)
        
        # Test the update_tickers_input function
        # Provide the table's data, mimicking the initial state when virtualRowData is None
        unique_tickers = update_tickers_input(None, getattr(table, 'rowData', None))

        # Expected result maintains the order of first appearance: TICKER_B, TICKER_A, TICKER_C
        # Ticker B should only appear once despite having multiple entries
        self.assertEqual(unique_tickers, "TICKER_B;TICKER_A;TICKER_C")

    def test_update_tickers_input_with_virtual_data(self):
        # When table is sorted or filtered, virtualRowData is populated and used
        virtual_data = [
            {"Ticker": "TICKER_C"},
            {"Ticker": "TICKER_A"},
            {"Ticker": "TICKER_B"},
            {"Ticker": "TICKER_A"}  # Duplicate to check uniqueness
        ]
        
        data = [
            {"Ticker": "TICKER_B"},
            {"Ticker": "TICKER_A"},
            {"Ticker": "TICKER_C"},
            {"Ticker": "TICKER_A"}
        ]
        
        # Should use virtual_data over data
        unique_tickers = update_tickers_input(virtual_data, data)
        self.assertEqual(unique_tickers, "TICKER_C;TICKER_A;TICKER_B")

    def test_update_tickers_input_empty(self):
        # Both None
        self.assertEqual(update_tickers_input(None, None), "")
        # Empty lists
        self.assertEqual(update_tickers_input([], []), "")
        # Missing 'Ticker' key
        self.assertEqual(update_tickers_input([{"Other": "X"}], None), "")

if __name__ == '__main__':
    unittest.main()
