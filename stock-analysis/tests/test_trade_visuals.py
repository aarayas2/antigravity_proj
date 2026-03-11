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

    def test_missing_essential_keys_combinations(self):
        """Test explicitly missing essential keys like entry_date to ensure None is returned."""
        # 1. Missing entry_date
        trade1 = {
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0
        }
        self.assertIsNone(self.factory.create_trace(trade1))

        # 2. Open trade missing fallback_exit_date
        trade2 = {
            'entry_date': self.dt_entry,
            'exit_date': pd.NaT,
            'entry_price': 100.0,
            'exit_price': 110.0
        }
        self.assertIsNone(self.factory.create_trace(trade2))

        # 3. Open trade with invalid fallback_exit_date (None)
        trade3 = {
            'entry_date': self.dt_entry,
            'exit_date': pd.NaT,
            'fallback_exit_date': None,
            'entry_price': 100.0,
            'exit_price': 110.0
        }
        self.assertIsNone(self.factory.create_trace(trade3))

        # 4. Open trade with invalid fallback_exit_date (pd.NaT)
        trade4 = {
            'entry_date': self.dt_entry,
            'exit_date': pd.NaT,
            'fallback_exit_date': pd.NaT,
            'entry_price': 100.0,
            'exit_price': 110.0
        }
        self.assertIsNone(self.factory.create_trace(trade4))

        # 5. Missing entry_date but has everything else
        trade5 = {
            'exit_date': self.dt_exit,
            'fallback_exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }
        self.assertIsNone(self.factory.create_trace(trade5))

    def test_missing_keys_exhaustively(self):
        """Test exhaustive combinations of missing key scenarios."""
        # Baseline valid trade
        valid_trade = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit,
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }

        # Test passing dictionaries with missing keys to assert None or valid fallback

        # Missing only entry_date - Should return None
        trade_no_entry_date = valid_trade.copy()
        del trade_no_entry_date['entry_date']
        self.assertIsNone(self.factory.create_trace(trade_no_entry_date))

        # Missing only exit_date (and no fallback) - Should return None because it's an open trade without a fallback
        trade_no_exit_date = valid_trade.copy()
        del trade_no_exit_date['exit_date']
        self.assertIsNone(self.factory.create_trace(trade_no_exit_date))

        # Missing exit_date but has fallback_exit_date - Should handle it as an open trade
        trade_no_exit_date_with_fallback = valid_trade.copy()
        del trade_no_exit_date_with_fallback['exit_date']
        trade_no_exit_date_with_fallback['fallback_exit_date'] = self.dt_exit
        trace_open = self.factory.create_trace(trade_no_exit_date_with_fallback)
        self.assertIsNotNone(trace_open)
        self.assertIn("End: Open", trace_open.text)

        # Missing entry_price - Should format as N/A
        trade_no_entry_price = valid_trade.copy()
        del trade_no_entry_price['entry_price']
        trace_no_entry_price = self.factory.create_trace(trade_no_entry_price)
        self.assertIsNotNone(trace_no_entry_price)
        self.assertIn("Entry Price: N/A", trace_no_entry_price.text)

        # Missing exit_price - Should format as N/A
        trade_no_exit_price = valid_trade.copy()
        del trade_no_exit_price['exit_price']
        trace_no_exit_price = self.factory.create_trace(trade_no_exit_price)
        self.assertIsNotNone(trace_no_exit_price)
        self.assertIn("Exit Price: N/A", trace_no_exit_price.text)

        # Missing all price keys and profit
        trade_only_dates = {
            'entry_date': self.dt_entry,
            'exit_date': self.dt_exit
        }
        trace_only_dates = self.factory.create_trace(trade_only_dates)
        self.assertIsNotNone(trace_only_dates)
        self.assertIn("Entry Price: N/A", trace_only_dates.text)
        self.assertIn("Exit Price: N/A", trace_only_dates.text)

    def test_missing_keys_return_none_cases(self):
        """Test completely missing keys that result in None trace."""
        self.assertIsNone(self.factory.create_trace({'exit_date': self.dt_exit}))
        self.assertIsNone(self.factory.create_trace({'entry_price': 100.0, 'exit_price': 110.0}))
        self.assertIsNone(self.factory.create_trace({'fallback_exit_date': self.dt_exit}))
        self.assertIsNone(self.factory.create_trace({}))

class TestTradeTooltipFactoryAdditionalEdgeCases(unittest.TestCase):
    """
    Additional tests for explicit edge cases regarding missing keys, pd.NaT,
    and np.nan, fulfilling specific strict review requirements without modifying
    existing test classes.
    """
    def setUp(self):
        self.factory = TradeTooltipFactory(y_min=0.0, y_max=100.0)

    def test_missing_keys_explicit_coverage(self):
        """Test missing keys to assert None is returned."""
        trade_missing_all = {}
        self.assertIsNone(self.factory.create_trace(trade_missing_all))

        trade_missing_entry_date = {'exit_date': datetime(2023, 1, 2)}
        self.assertIsNone(self.factory.create_trace(trade_missing_entry_date))

    def test_pd_nat_handling(self):
        """Test pd.NaT for dates explicitly."""
        trade_nat_entry = {
            'entry_date': pd.NaT,
            'exit_date': datetime(2023, 1, 2),
            'entry_price': 100.0,
            'exit_price': 110.0
        }
        self.assertIsNone(self.factory.create_trace(trade_nat_entry))

    def test_np_nan_handling(self):
        """Test np.nan for prices explicitly."""
        import numpy as np
        trade_nan_prices = {
            'entry_date': datetime(2023, 1, 1),
            'exit_date': datetime(2023, 1, 2),
            'entry_price': np.nan,
            'exit_price': np.nan
        }
        trace = self.factory.create_trace(trade_nan_prices)
        self.assertIsNotNone(trace)
        self.assertIn("Entry Price: N/A", trace.text)
        self.assertIn("Exit Price: N/A", trace.text)

    def test_plotly_shape_generation_exception(self):
        """Test exception handling during go.Scatter generation by providing invalid data."""
        from unittest.mock import patch

        trade = {
            'entry_date': datetime(2023, 1, 1),
            'exit_date': datetime(2023, 1, 10),
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }

        # By mocking go.Scatter to raise an Exception, we can cover the `except Exception as e:` block.
        with patch('trade_visuals.go.Scatter', side_effect=ValueError("Intentional error for testing Exception handling in Plotly trace generation")):
            trace = self.factory.create_trace(trade)
            self.assertIsNone(trace)

    def test_malformed_date_strings_exception(self):
        """Test passing malformed dates to trigger formatting exceptions."""
        class MalformedDate:
            def strftime(self, format):
                raise ValueError("Intentional formatting error")

            def __str__(self):
                raise ValueError("Intentional string cast error")

            # Make it behave nicely for the initial pandas check `pd.isna`
            def __bool__(self):
                return True

        # Plotly go.Scatter doesn't like generic objects for x coordinates and might raise an error
        # during trace instantiation, hiding the `str()` exception test.
        # We can either patch `go.Scatter` so it accepts anything or use `mock_date` logic
        # from earlier tests, but mock `__str__` to raise exception when `hasattr` is false.

        # Actually, let's use a mock that doesn't have `strftime` and raises an error on `__str__`.
        # MagicMock.__str__ handles things safely, so we need to set side_effect on a regular mock
        # or class. We can patch `go.Scatter` just to get the `hover_text` generated without error
        # and test it.

        from unittest.mock import patch

        # When TradeTooltipFactory.create_trace tries to format the dates, it should
        # fall back to "Unknown" because of the `try...except Exception:` blocks.

        # Test 1: Exception during `strftime` (covered by `test_entry_date_exception` in main suite)
        # Test 2: Exception during `str()` cast when `strftime` is not present


        class NoStrftimeDate:
            def __str__(self):
                raise Exception("Intentional string cast error")
            def __bool__(self):
                return True

        trade_no_strftime = {
            'entry_date': NoStrftimeDate(),
            'exit_date': NoStrftimeDate(),
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }

        # We'll patch go.Scatter to just return the kwargs it was called with
        # so we can inspect the `text` parameter.
        with patch('trade_visuals.go.Scatter', side_effect=lambda **kwargs: kwargs):
            trace = self.factory.create_trace(trade_no_strftime)
            self.assertIsNotNone(trace)
            self.assertIn("Start: Unknown", trace['text'])
            self.assertIn("End: Unknown", trace['text'])



    def test_plotly_shape_generation_native_exception(self):
        """Test native exception handling when trace generation natively fails."""
        class MalformedDateStrftime:
            def strftime(self, format):
                raise ValueError("Triggering exception on strftime conversion")
            def __bool__(self):
                return True
            def __str__(self):
                # When hasattr(..., 'strftime') returns True, strftime is called and raises ValueError.
                # Then it goes to except Exception and start_str becomes "Unknown"
                return "2023-01-01"

        class MalformedDateStr:
            def __str__(self):
                raise Exception("Triggering exception on string conversion")
            def __bool__(self):
                return True

        # Using mocked objects to trigger the formatting ValueError/Exception for both
        trade = {
            'entry_date': MalformedDateStrftime(),
            'exit_date': MalformedDateStr(),
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }

        # Do NOT patch go.Scatter. Let the exception bubble up inside the date formatting blocks.
        # This will explicitly cover lines 108-117.
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("Start: Unknown", trace.text)
        self.assertIn("End: Unknown", trace.text)


if __name__ == '__main__':
    unittest.main()

    def test_plotly_shape_generation_native_exception(self):
        """Test native exception handling when trace generation natively fails."""
        class MalformedDateStrftime:
            def strftime(self, format):
                raise ValueError("Triggering exception on strftime conversion")
            def __bool__(self):
                return True
            def __str__(self):
                return "2023-01-01"

        class MalformedDateStr:
            def __str__(self):
                raise Exception("Triggering exception on string conversion")
            def __bool__(self):
                return True

        # Using mocked objects to trigger the formatting ValueError/Exception for both
        trade = {
            'entry_date': MalformedDateStrftime(),
            'exit_date': MalformedDateStr(),
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': 10.0
        }

        # Do NOT patch go.Scatter. Let the exception bubble up inside the date formatting blocks.
        # This will explicitly cover lines 108-117.
        trace = self.factory.create_trace(trade)
        self.assertIsNotNone(trace)
        self.assertIn("Start: Unknown", trace.text)
        self.assertIn("End: Unknown", trace.text)

if __name__ == '__main__':
    unittest.main()
