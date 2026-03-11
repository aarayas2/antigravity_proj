import sys
import os
import unittest
sys.path.insert(0, os.path.abspath('stock-analysis'))
from trade_visuals import TradeTooltipFactory
import plotly.graph_objects as go
import pandas as pd

class TestTradeTooltipFactoryAdditionalEdgeCases(unittest.TestCase):
    def setUp(self):
        self.factory = TradeTooltipFactory(0, 100)

    def test_native_plotly_shape_generation_exception(self):
        """Test native exception handling when trace generation natively fails."""
        # Using string instead of float for profit calculation will cause an exception
        # actually, `profit` is only checked against 0 (`profit > 0`), which works for strings in py2 but raises TypeError in py3!
        # Wait, if `profit` is a string, `profit > 0` raises TypeError in Python 3!
        trade_bad_profit = {
            'entry_date': pd.Timestamp('2023-01-01'),
            'exit_date': pd.Timestamp('2023-01-02'),
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': "10.0" # This will trigger TypeError during `profit > 0`
        }
        trace = self.factory.create_trace(trade_bad_profit)
        self.assertIsNone(trace)

if __name__ == '__main__':
    unittest.main()
