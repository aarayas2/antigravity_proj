

import sys
import types
from unittest.mock import MagicMock

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock dependencies

import importlib.util
# Need absolute path since tests are run from various locations
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'strategy', 'fifty_two_week.py'))
spec = importlib.util.spec_from_file_location("fifty_two_week", file_path)
fifty_two_week = importlib.util.module_from_spec(spec)
sys.modules["fifty_two_week"] = fifty_two_week
spec.loader.exec_module(fifty_two_week)

class TestFiftyTwoWeekStrategy(unittest.TestCase):
    def test_apply_strategy_empty(self):
        mock_df = MagicMock()
        mock_df.empty = True
        mock_df.copy.return_value = mock_df
        result = fifty_two_week.apply_strategy(mock_df)
        self.assertEqual(result, mock_df)

    def test_needs_subplots(self):
        self.assertFalse(fifty_two_week.needs_subplots())
        
    def test_get_signals(self):
        mock_df = MagicMock()
        mock_df.columns = ['Position']
        mock_buy = MagicMock()
        mock_sell = MagicMock()
        
        # When get_signals runs, it does df['Position'] twice, and df[...] twice.
        # So __getitem__ is called 4 times total:
        # 1. df['Position']
        # 2. df[df['Position'] == 1.0]
        # 3. df['Position']
        # 4. df[df['Position'] == -1.0]
        
        mock_pos_col = MagicMock()
        # Ensure __eq__ works safely for mocks when comparing to numbers
        mock_pos_col.__eq__.return_value = MagicMock()
        
        mock_df.__getitem__.side_effect = [mock_pos_col, mock_buy, mock_pos_col, mock_sell]
        
        buy, sell = fifty_two_week.get_signals(mock_df)
        self.assertEqual(buy, mock_buy)
        self.assertEqual(sell, mock_sell)

    @patch('strategy.fifty_two_week.go.Scatter')
    def test_add_traces(self, mock_scatter):
        mock_fig = MagicMock()
        mock_df = MagicMock()
        mock_df.index = [1, 2, 3]
        mock_df.columns = ['52W_High', '52W_Low']
        
        fifty_two_week.add_traces(mock_fig, mock_df, 1, 1)
        self.assertEqual(mock_fig.add_trace.call_count, 2)
        
        mock_fig.reset_mock()
        fifty_two_week.add_traces(mock_fig, mock_df, None, None)
        self.assertEqual(mock_fig.add_trace.call_count, 2)

if __name__ == '__main__':
    unittest.main()
