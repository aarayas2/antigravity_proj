import sys
import os

sys.path.insert(0, os.path.abspath('stock-analysis'))
from trade_visuals import TradeTooltipFactory
import plotly.graph_objects as go
import pandas as pd

factory = TradeTooltipFactory(0, 100)

class ExplosiveDate:
    def strftime(self, format):
        return "2023-01-01"

    def __bool__(self):
        return True

    @property
    def __class__(self):
        # Maybe returning something that plotly tries to access and fails?
        pass

# Wait, Plotly does validation if we pass certain invalid data types or structures.
# Maybe we just need to test passing an object that plotly specifically rejects.
# Actually, plotly accepts almost anything in the `x` array by turning it into a tuple of objects.

# But what if `trade['profit']` is a string instead of a number, wait, the profit logic handles it?
# profit = trade.get('profit', 0) -> if profit > 0: ... if it's a string, `profit > 0` raises TypeError!
# Let's test this!

trade2 = {
    'entry_date': pd.Timestamp('2023-01-01'),
    'exit_date': pd.Timestamp('2023-01-02'),
    'entry_price': 100.0,
    'exit_price': 110.0,
    'profit': "10.0" # STRING!
}

try:
    trace = factory.create_trace(trade2)
    print("Trace generated:", type(trace))
except Exception as e:
    print("Exception thrown!", e)

# Wait, if `trace` returns None, it means the outer try-except caught it.
print("Is trace None?", trace is None)
