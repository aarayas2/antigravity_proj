import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
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

if __name__ == '__main__':
    unittest.main()
