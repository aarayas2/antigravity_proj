import os
import sys
import pandas as pd
import numpy as np
import pandas_ta as ta
from unittest.mock import MagicMock

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategy.MACD import apply_strategy, get_signals, needs_subplots, add_traces

def test_macd_apply_strategy():
    """Test apply_strategy with normal data to calculate MACD and signals."""
    np.random.seed(42)
    # MACD usually needs some data. fast=12, slow=26, signal=9.
    dates = pd.date_range(start="2023-01-01", periods=50)

    # Generate data with a crossover trend
    closes = np.full(50, 100.0)
    closes[20:35] = np.linspace(100, 110, 15)
    closes[35:] = np.linspace(110, 100, 15)

    df = pd.DataFrame({'Close': closes}, index=dates)

    result_df = apply_strategy(df)

    # Check that MACD and signal columns are added
    assert 'MACD_12_26_9' in result_df.columns
    assert 'MACDs_12_26_9' in result_df.columns
    assert 'MACDh_12_26_9' in result_df.columns
    assert 'Signal' in result_df.columns
    assert 'Position' in result_df.columns

    # Verify Signal logic: 1.0 if MACD > MACDs else 0.0
    valid_mask = result_df['MACD_12_26_9'].notna() & result_df['MACDs_12_26_9'].notna()
    expected_signal = (result_df.loc[valid_mask, 'MACD_12_26_9'] > result_df.loc[valid_mask, 'MACDs_12_26_9']).astype(float)
    pd.testing.assert_series_equal(result_df.loc[valid_mask, 'Signal'], expected_signal, check_names=False)

    # Verify Position logic: Signal.diff()
    expected_position = result_df['Signal'].diff()
    pd.testing.assert_series_equal(result_df['Position'], expected_position, check_names=False)

def test_macd_apply_strategy_insufficient_data():
    """Test apply_strategy with very little data where MACD cannot be calculated."""
    df = pd.DataFrame({'Close': [10.0, 11.0]})
    result_df = apply_strategy(df)

    # MACD columns should not be added
    assert 'MACD_12_26_9' not in result_df.columns
    assert 'Signal' not in result_df.columns

def test_macd_apply_strategy_empty_df():
    """Test apply_strategy with an empty DataFrame."""
    df = pd.DataFrame(columns=['Close'])
    result_df = apply_strategy(df)

    assert isinstance(result_df, pd.DataFrame)
    assert result_df.empty

def test_macd_get_signals():
    """Test get_signals correctly identifies buy and sell signals from Position."""
    dates = pd.date_range(start="2023-01-01", periods=5)
    df = pd.DataFrame({
        'Close': [100.0, 101.0, 102.0, 101.0, 100.0],
        'Position': [0.0, 1.0, 0.0, -1.0, 0.0]
    }, index=dates)

    buy_signals, sell_signals = get_signals(df)

    assert len(buy_signals) == 1
    assert buy_signals.index[0] == dates[1]

    assert len(sell_signals) == 1
    assert sell_signals.index[0] == dates[3]

def test_macd_get_signals_no_position_column():
    """Test get_signals handles missing Position column gracefully."""
    df = pd.DataFrame({'Close': [100.0, 101.0]})
    buy_signals, sell_signals = get_signals(df)

    assert buy_signals.empty
    assert sell_signals.empty

def test_macd_needs_subplots():
    """Test needs_subplots returns True as MACD uses a sub-panel."""
    assert needs_subplots() is True

from unittest.mock import patch

@patch('strategy.MACD.go.Scatter')
def test_macd_add_traces(mock_scatter):
    """Test add_traces adds MACD Line, Signal Line, and Histogram traces."""
    fig = MagicMock()
    df = pd.DataFrame({
        'MACD_12_26_9': [1.0, 1.1],
        'MACDs_12_26_9': [0.9, 1.0],
        'MACDh_12_26_9': [0.1, -0.1]
    }, index=pd.date_range(start="2023-01-01", periods=2))

    add_traces(fig, df, main_row=1, sub_row=2)

    # Should add 3 traces
    assert fig.add_trace.call_count == 3

    # Verify sub_row and col=1 were used in kwargs
    for call in fig.add_trace.call_args_list:
        _, kwargs = call
        assert kwargs.get('row') == 2
        assert kwargs.get('col') == 1

@patch('strategy.MACD.go.Scatter')
def test_macd_add_traces_no_columns(mock_scatter):
    """Test add_traces does nothing if MACD columns are missing."""
    fig = MagicMock()
    df = pd.DataFrame({'Close': [100.0, 101.0]})
    add_traces(fig, df, main_row=1, sub_row=2)

    fig.add_trace.assert_not_called()
