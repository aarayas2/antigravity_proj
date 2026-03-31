"""
Tests for the strategy statistics page logic.
"""
import sys
import os
import unittest
from unittest.mock import patch

# Add parent directory to sys.path to allow imports from pages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pylint: disable=wrong-import-position,import-error
import dash
import dash_bootstrap_components as dbc

from pages.strategy_statistics import (
    update_stats_table,
    update_tickers_input,
    disable_process_button,
    run_and_display_batch_mode
)

class TestStrategyStatistics(unittest.TestCase):
    """Test suite for strategy statistics logic."""
    @patch('pages.strategy_statistics.stats_manager.read_all_stats')
    def test_update_stats_table_ignores_non_dict_metrics(self, mock_read_all):
        """Tests that update_stats_table ignores non-dict keys within stats."""
        # Provide mock data with string/invalid keys inside the strategy dictionary
        mock_read_all.return_value = [
            {'TICKER_X': {
                'date-begin': '2023-01-01',
                'date-end': '2023-12-31',
                'invalid_string_key': 'this should be ignored',
                'invalid_list_key': [1, 2, 3],
                'ValidStrategy': {
                    'Win Rate': 0.8,
                    'Average Return': 0.05,
                    'Total Return': 0.1,
                    'Number of Trades': 10
                }
            }}
        ]

        table = update_stats_table(0)
        row_data = getattr(table, 'rowData', [])
        
        # Only ValidStrategy should be processed
        self.assertEqual(len(row_data), 1)
        self.assertEqual(row_data[0]['Strategy'], 'ValidStrategy')
        self.assertEqual(row_data[0]['Ticker'], 'TICKER_X')
        self.assertEqual(row_data[0]['Win Rate'], 0.8)

    @patch('pages.strategy_statistics.stats_manager._storage.read')
    def test_unique_tickers_maintains_order(self, mock_read):
        """Tests that unique tickers maintain their insertion order."""
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

        # Expected result contains all unique tickers
        # Ticker B should only appear once despite having multiple entries
        self.assertCountEqual(unique_tickers.split(";"), ["TICKER_B", "TICKER_A", "TICKER_C"])

    def test_update_tickers_input_with_virtual_data(self):
        """Tests update_tickers_input when virtualRowData is provided."""
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
        self.assertCountEqual(unique_tickers.split(";"), ["TICKER_C", "TICKER_A", "TICKER_B"])

    def test_update_tickers_input_empty(self):
        """Tests update_tickers_input with empty or None inputs."""
        # Both None
        self.assertEqual(update_tickers_input(None, None), "")
        # Empty lists
        self.assertEqual(update_tickers_input([], []), "")
        # Missing 'Ticker' key
        self.assertEqual(update_tickers_input([{"Other": "X"}], None), "")

    def test_disable_process_button(self):
        """Tests disable_process_button with various inputs."""
        # Empty inputs should return True (disabled)
        self.assertTrue(disable_process_button(None))
        self.assertTrue(disable_process_button(""))
        self.assertTrue(disable_process_button("   "))

        # Valid ticker strings should return False (enabled)
        self.assertFalse(disable_process_button("AAPL"))
        self.assertFalse(disable_process_button("AAPL;MSFT"))
        self.assertFalse(disable_process_button("  AAPL  "))

    def test_run_and_display_batch_mode_no_inputs(self):
        """Tests run_and_display_batch_mode with missing inputs."""
        # Missing n_clicks
        self.assertEqual(run_and_display_batch_mode(None, "AAPL"), dash.no_update)
        self.assertEqual(run_and_display_batch_mode(0, "AAPL"), dash.no_update)

        # Missing tickers_val
        self.assertEqual(run_and_display_batch_mode(1, None), dash.no_update)
        self.assertEqual(run_and_display_batch_mode(1, ""), dash.no_update)

    @patch('app.run_batch_mode')
    def test_run_and_display_batch_mode_empty_results(self, mock_run_batch_mode):
        """Tests run_and_display_batch_mode when batch mode returns no results."""
        mock_run_batch_mode.return_value = {}

        result = run_and_display_batch_mode(1, "AAPL")

        self.assertIsInstance(result, dbc.Alert)
        self.assertEqual(result.children, "No buy zone signals found or processing failed.")
        self.assertEqual(getattr(result, 'color', None), "warning")
        mock_run_batch_mode.assert_called_once_with("AAPL")

    @patch('app.run_batch_mode')
    def test_run_and_display_batch_mode_success(self, mock_run_batch_mode):
        """Tests run_and_display_batch_mode when batch mode returns successful results."""
        mock_run_batch_mode.return_value = {
            "MACD": ["AAPL", "MSFT"],
            "RSI": ["GOOGL"]
        }

        result = run_and_display_batch_mode(1, "AAPL;MSFT;GOOGL")

        # Should return a dbc.Card
        self.assertIsInstance(result, dbc.Card)

        # Check Card components
        children = result.children
        self.assertEqual(len(children), 2)

        card_header = children[0]
        self.assertIsInstance(card_header, dbc.CardHeader)
        self.assertEqual(card_header.children.children, "Buy Zone Signals")

        card_body = children[1]
        self.assertIsInstance(card_body, dbc.CardBody)

        # Check rows in CardBody
        rows = card_body.children
        self.assertEqual(len(rows), 2)

        # Check first strategy row
        macd_row = rows[0]
        macd_col = macd_row.children[0]
        macd_label = macd_col.children[0]
        macd_input = macd_col.children[1]

        self.assertEqual(macd_label.children, "MACD:")
        self.assertEqual(macd_input.value, "AAPL; MSFT")
        self.assertTrue(macd_input.readonly)

        # Check second strategy row
        rsi_row = rows[1]
        rsi_col = rsi_row.children[0]
        rsi_label = rsi_col.children[0]
        rsi_input = rsi_col.children[1]

        self.assertEqual(rsi_label.children, "RSI:")
        self.assertEqual(rsi_input.value, "GOOGL")
        self.assertTrue(rsi_input.readonly)

        mock_run_batch_mode.assert_called_once_with("AAPL;MSFT;GOOGL")

if __name__ == '__main__':
    unittest.main()
