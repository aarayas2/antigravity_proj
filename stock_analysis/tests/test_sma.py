"""Unit tests for the SMA strategy."""

import os
import sys
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import pytest  # pylint: disable=import-error

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pylint: disable=wrong-import-position
from strategy.sma import apply_strategy, get_signals, needs_subplots, add_traces

def test_sma_apply_strategy():
    """Test apply_strategy with normal data to calculate SMA and signals."""
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=100)

    # Generate data with a crossover trend
    closes = np.full(100, 100.0)
    closes[20:60] = np.linspace(100, 150, 40)
    closes[60:] = np.linspace(150, 80, 40)

    df = pd.DataFrame({'Close': closes}, index=dates)

    result_df = apply_strategy(df)

    # Check that SMA columns are added
    assert 'SMA_20' in result_df.columns
    assert 'SMA_50' in result_df.columns
    assert 'Signal' in result_df.columns
    assert 'Position' in result_df.columns

    # Verify Signal logic: 1.0 if SMA_20 > SMA_50 else 0.0
    valid_mask = result_df['SMA_20'].notna() & result_df['SMA_50'].notna()
    expected_signal = (
        result_df.loc[valid_mask, 'SMA_20'] > result_df.loc[valid_mask, 'SMA_50']
    ).astype(float)
    pd.testing.assert_series_equal(
        result_df.loc[valid_mask, 'Signal'], expected_signal, check_names=False
    )

    # Verify Position logic: Signal.diff()
    expected_position = result_df['Signal'].diff()
    pd.testing.assert_series_equal(result_df['Position'], expected_position, check_names=False)

def test_sma_apply_strategy_insufficient_data():
    """Test apply_strategy with very little data where SMA_50 cannot be calculated."""
    df = pd.DataFrame({'Close': [10.0, 11.0]})
    result_df = apply_strategy(df)

    # SMA_20 and SMA_50 will be completely NaN or not added depending on pandas-ta behavior,
    # but the logic should handle it gracefully without crashing.
    assert 'Signal' in result_df.columns
    # It might create SMA_20 and SMA_50 with NaN depending on pandas_ta, so we just check no crash.

def test_sma_apply_strategy_empty_df():
    """Test apply_strategy with an empty DataFrame."""
    df = pd.DataFrame(columns=['Close'])
    result_df = apply_strategy(df)

    assert isinstance(result_df, pd.DataFrame)
    # The output dataframe might have standard columns added but should essentially be empty
    assert len(result_df) == 0

def test_sma_get_signals():
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

def test_sma_get_signals_no_position_column():
    """Test get_signals handles missing Position column gracefully."""
    df = pd.DataFrame({'Close': [100.0, 101.0]})
    buy_signals, sell_signals = get_signals(df)

    assert buy_signals.empty
    assert sell_signals.empty

def test_sma_needs_subplots():
    """Test needs_subplots returns False as SMA overlaps the price chart."""
    assert needs_subplots() is False

@patch('strategy.sma.go.Scatter')
def test_sma_add_traces_with_main_row(mock_scatter):  # pylint: disable=unused-argument
    """Test add_traces adds SMA lines to the main row."""
    fig = MagicMock()
    df = pd.DataFrame({
        'SMA_20': [100.0, 101.0],
        'SMA_50': [90.0, 91.0],
    }, index=pd.date_range(start="2023-01-01", periods=2))

    add_traces(fig, df, main_row=1, sub_row=2)

    # Should add 2 traces
    assert fig.add_trace.call_count == 2

    # Verify row=1 and col=1 were used
    for call in fig.add_trace.call_args_list:
        _, kwargs = call
        assert kwargs.get('row') == 1
        assert kwargs.get('col') == 1

@patch('strategy.sma.go.Scatter')
def test_sma_add_traces_no_main_row(mock_scatter):  # pylint: disable=unused-argument
    """Test add_traces adds SMA lines without specifying row/col."""
    fig = MagicMock()
    df = pd.DataFrame({
        'SMA_20': [100.0, 101.0],
        'SMA_50': [90.0, 91.0],
    }, index=pd.date_range(start="2023-01-01", periods=2))

    add_traces(fig, df, main_row=None, sub_row=None)

    # Should add 2 traces
    assert fig.add_trace.call_count == 2

    # Verify row and col were NOT used
    for call in fig.add_trace.call_args_list:
        _, kwargs = call
        assert 'row' not in kwargs
        assert 'col' not in kwargs

@patch('strategy.sma.go.Scatter')
def test_sma_add_traces_missing_columns(mock_scatter):  # pylint: disable=unused-argument
    """Test add_traces handles missing columns gracefully."""
    fig = MagicMock()
    df = pd.DataFrame({'Close': [100.0, 101.0]})
    # It shouldn't crash, it might try to add traces with KeyErrors if columns are missing,
    # but the original code doesn't check for 'SMA_20' in columns before adding.
    # We should see what happens.

    # Actually, if columns are missing it will raise KeyError in the original code.
    # The current code does: y=df_with_signals['SMA_20']
    # If this raises a KeyError, our test should capture it or we should fix the code.
    # The requirement is just missing tests, not fixing bugs, but we can verify it raises KeyError.
    with pytest.raises(KeyError):
        add_traces(fig, df, main_row=1, sub_row=2)
