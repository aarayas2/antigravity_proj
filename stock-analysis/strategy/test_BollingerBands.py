import pytest
import pandas as pd
from strategy.BollingerBands import get_signals

def test_get_signals_no_signal_column():
    """Test get_signals when DataFrame does not have a 'Signal' column."""
    df = pd.DataFrame({'Close': [10, 20, 30]})
    buy_signals, sell_signals = get_signals(df)

    assert buy_signals.empty, "Buy signals should be empty if 'Signal' column is missing."
    assert sell_signals.empty, "Sell signals should be empty if 'Signal' column is missing."

def test_get_signals_with_signal_column():
    """Test get_signals when DataFrame has a 'Signal' column."""
    df = pd.DataFrame({
        'Close': [10, 20, 30, 40],
        'Signal': [0.0, 1.0, -1.0, 1.0]
    })
    buy_signals, sell_signals = get_signals(df)

    assert len(buy_signals) == 2, "Should find 2 buy signals (Signal == 1.0)."
    assert buy_signals.index.tolist() == [1, 3], "Buy signals should match indices 1 and 3."

    assert len(sell_signals) == 1, "Should find 1 sell signal (Signal == -1.0)."
    assert sell_signals.index.tolist() == [2], "Sell signal should match index 2."

def test_get_signals_empty_df():
    """Test get_signals with an empty DataFrame."""
    df = pd.DataFrame()
    buy_signals, sell_signals = get_signals(df)

    assert buy_signals.empty, "Buy signals should be empty for an empty DataFrame."
    assert sell_signals.empty, "Sell signals should be empty for an empty DataFrame."
