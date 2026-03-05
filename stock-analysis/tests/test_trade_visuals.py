import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import Mock
import pandas as pd
from datetime import datetime

from trade_visuals import TradeTooltipFactory

class TestTradeTooltipFactory(unittest.TestCase):
    def setUp(self):
        self.factory = TradeTooltipFactory(y_min=0.0, y_max=100.0)
        self.dt_entry = datetime(2023, 1, 1)
        self.dt_exit = datetime(2023, 1, 10)

    def test_valid_trade(self):
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertEqual(trace.fillcolor, "rgba(0, 128, 0, 0.2)") # profit > 0

    def test_missing_entry_date(self):
        trade = {
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNone(trace)

    def test_missing_exit_date_open_trade(self):
        trade = {
            'entry_date': self.dt_entry,
            'entry_price': 100.0,
            'profit': 0.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNone(trace) # As per logic, without fallback, it returns None for open trades

    def test_zero_entry_price(self):
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'entry_price': 0.0,
            'exit_price': 110.0,
            'profit': 110.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("N/A (Entry=0)", trace.text)

    def test_missing_prices(self):
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'profit': 0.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("Entry Price: N/A", trace.text)
        self.assertIn("Exit Price: N/A", trace.text)

    def test_negative_profit(self):
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 90.0,
            'profit': -10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertEqual(trace.fillcolor, "rgba(255, 0, 0, 0.2)")

    def test_exception_handling_malformed_trade(self):
        trade = ["not", "a", "dict"] # Will cause AttributeError when get() is called
        trace = self.factory.create_trace(trade)
        self.assertIsNone(trace)

    def test_entry_date_exception(self):
        mock_date = Mock()
        mock_date.strftime.side_effect = Exception("Date formatting error")

        trade = {
            'entry_date': mock_date,
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("Start: Unknown", trace.text)

    def test_exit_date_exception(self):
        mock_date = Mock()
        mock_date.strftime.side_effect = Exception("Date formatting error")

        trade = {
            'entry_date': self.dt_entry,
            'exit_date': mock_date,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("End: Unknown", trace.text)

    def test_open_trade_with_fallback_date(self):
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': None,
            'fallback_exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertEqual(trace.fillcolor, "rgba(128, 128, 128, 0.2)") # open trade color
        self.assertIn("End: Open", trace.text)
        self.assertEqual(trace.hoverlabel.bgcolor, "gray")

    def test_empty_trade_dict(self):
        """Test with an empty dictionary, which lacks 'entry_date' and should return None."""
        trace = self.factory.create_trace({})
        self.assertIsNone(trace)

    def test_none_trade(self):
        """Test with None, which should raise an exception caught internally, returning None."""
        trace = self.factory.create_trace(None)
        self.assertIsNone(trace)

    def test_open_trade_pd_isna_exit_date_valid_fallback(self):
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': pd.NaT,
            'fallback_exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("End: Open", trace.text)

    def test_open_trade_pd_isna_exit_date_invalid_fallback(self):
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': pd.NaT,
            'fallback_exit_date': pd.NaT,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNone(trace)

    def test_pd_isna_prices(self):
        import numpy as np
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'entry_price': np.nan,
            'exit_price': np.nan,
            'profit': 0.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("Entry Price: N/A", trace.text)
        self.assertIn("Exit Price: N/A", trace.text)

    def test_string_dates_no_strftime(self):
        trade = {
            'entry_date': '2023-01-01',
            'exit_date': '2023-01-10',
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("Start: 2023-01-01", trace.text)
        self.assertIn("End: 2023-01-10", trace.text)

    def test_missing_profit_key(self):
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        # Defaults to profit 0, which corresponds to red (profit <= 0)
        self.assertEqual(trace.fillcolor, "rgba(255, 0, 0, 0.2)")
        self.assertEqual(trace.hoverlabel.bgcolor, "red")

    def test_pd_nat_entry_date(self):
        trade = {
            'entry_date': pd.NaT,
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNone(trace)

    def test_missing_keys_edge_cases(self):
        # Trade missing both entry_date and exit_date
        trace1 = self.factory.create_trace({'profit': 10.0})
        self.assertIsNone(trace1)

        # Trade with None exit_date but missing fallback_exit_date
        trace2 = self.factory.create_trace({'entry_date': self.dt_entry, 'exit_date': None})
        self.assertIsNone(trace2)

    def test_missing_random_keys(self):
        """Test with a dictionary that has completely unrelated keys but misses the required ones."""
        trace = self.factory.create_trace({'random_key': 'value', 'another_key': 123})
        self.assertIsNone(trace)

    def test_missing_entry_price_with_exit_price(self):
        """Test when entry_price is explicitly missing but exit_price is present."""
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'exit_price': 110.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("Entry Price: N/A", trace.text)
        self.assertIn("Exit Price: $110.00", trace.text)

    def test_missing_exit_price_with_entry_price(self):
        """Test when exit_price is explicitly missing but entry_price is present."""
        trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'profit': 10.0
        }
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("Entry Price: $100.00", trace.text)
        self.assertIn("Exit Price: N/A", trace.text)

if __name__ == '__main__':
    unittest.main()
