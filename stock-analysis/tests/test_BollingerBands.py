import os
import sys
import pandas as pd
import numpy as np
import pandas_ta as ta  # Required to inject .ta into pandas DataFrame
import pytest

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategy.BollingerBands import apply_strategy

def test_bollinger_bands_apply_strategy():
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30)

    closes = np.full(30, 100.0)
    closes = closes + np.random.normal(0, 1, 30)

    # Force a sell signal (price > upper band) on day 25
    closes[25] = 120.0

    # Force a buy signal (price < lower band) on day 28
    closes[28] = 80.0

    df = pd.DataFrame({'Close': closes}, index=dates)

    result_df = apply_strategy(df)

    assert 'BBL_20_2.0_2.0' in result_df.columns
    assert 'BBU_20_2.0_2.0' in result_df.columns
    assert 'Signal' in result_df.columns
    assert 'Position' in result_df.columns

    # The first 19 days should have NaN for bbands, so Signal is 0.0
    assert result_df['Signal'].iloc[0] == 0.0

    # Check signals
    assert result_df['Signal'].iloc[25] == -1.0
    assert result_df['Signal'].iloc[28] == 1.0

def test_bollinger_bands_not_enough_data():
    np.random.seed(42)
    # The default period for BB is 20, so 10 periods will not generate bands
    dates = pd.date_range(start="2023-01-01", periods=10)
    closes = np.full(10, 100.0) + np.random.normal(0, 1, 10)

    df = pd.DataFrame({'Close': closes}, index=dates)

    result_df = apply_strategy(df)

    # Check if the output dataframe equals input since no bands are generated
    assert 'BBL_20_2.0_2.0' not in result_df.columns
    assert 'BBU_20_2.0_2.0' not in result_df.columns

    # Based on the strategy logic, if bbands is None, 'Signal' is not added
    assert 'Signal' not in result_df.columns
    assert 'Position' not in result_df.columns

def test_bollinger_bands_empty_df():
    df = pd.DataFrame(columns=['Close'])
    result_df = apply_strategy(df)

    assert 'BBL_20_2.0_2.0' not in result_df.columns
    assert 'Signal' not in result_df.columns

from strategy.BollingerBands import get_signals

def test_bollinger_bands_get_signals_with_signals():
    dates = pd.date_range(start="2023-01-01", periods=5)
    df = pd.DataFrame({
        'Close': [100.0, 105.0, 95.0, 110.0, 90.0],
        'Signal': [0.0, -1.0, 1.0, -1.0, 1.0]
    }, index=dates)

    buy_signals, sell_signals = get_signals(df)

    assert not buy_signals.empty
    assert len(buy_signals) == 2
    assert buy_signals.index[0] == dates[2]
    assert buy_signals.index[1] == dates[4]

    assert not sell_signals.empty
    assert len(sell_signals) == 2
    assert sell_signals.index[0] == dates[1]
    assert sell_signals.index[1] == dates[3]

def test_bollinger_bands_get_signals_no_signal_column():
    dates = pd.date_range(start="2023-01-01", periods=3)
    df = pd.DataFrame({
        'Close': [100.0, 105.0, 95.0]
    }, index=dates)

    buy_signals, sell_signals = get_signals(df)

    assert buy_signals.empty
    assert sell_signals.empty

def test_bollinger_bands_get_signals_empty_df():
    df = pd.DataFrame()

    buy_signals, sell_signals = get_signals(df)

    assert buy_signals.empty
    assert sell_signals.empty

def test_bollinger_bands_get_signals_assert_type():
    dates = pd.date_range(start="2023-01-01", periods=3)
    df = pd.DataFrame({
        'Close': [100.0, 105.0, 95.0]
    }, index=dates)

    buy_signals, sell_signals = get_signals(df)

    assert isinstance(buy_signals, pd.DataFrame)
    assert isinstance(sell_signals, pd.DataFrame)

    # Asserting the returned dataframes are indeed empty
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame())
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame())
from strategy.BollingerBands import needs_subplots, add_traces
from unittest.mock import MagicMock

def test_needs_subplots():
    assert needs_subplots() is False

def test_add_traces_with_subplots():
    fig = MagicMock()
    df = pd.DataFrame({
        'BBU_20_2.0_2.0': [100.0, 105.0],
        'BBL_20_2.0_2.0': [90.0, 95.0],
        'BBM_20_2.0_2.0': [95.0, 100.0]
    }, index=pd.date_range(start="2023-01-01", periods=2))

    add_traces(fig, df, main_row=1, sub_row=None)

    assert fig.add_trace.call_count == 3

    # Check that row=1, col=1 was passed in kwargs
    for call in fig.add_trace.call_args_list:
        _, kwargs = call
        assert kwargs.get('row') == 1
        assert kwargs.get('col') == 1

def test_add_traces_no_subplots():
    fig = MagicMock()
    df = pd.DataFrame({
        'BBU_20_2.0_2.0': [100.0, 105.0],
        'BBL_20_2.0_2.0': [90.0, 95.0],
        'BBM_20_2.0_2.0': [95.0, 100.0]
    }, index=pd.date_range(start="2023-01-01", periods=2))

    add_traces(fig, df, main_row=None, sub_row=None)

    assert fig.add_trace.call_count == 3

    # Check that row/col wasn't passed or is None
    for call in fig.add_trace.call_args_list:
        _, kwargs = call
        assert kwargs.get('row') is None

def test_add_traces_no_bbands():
    fig = MagicMock()
    df = pd.DataFrame({
        'Close': [100.0, 105.0]
    }, index=pd.date_range(start="2023-01-01", periods=2))

    add_traces(fig, df, main_row=1, sub_row=None)

    assert fig.add_trace.call_count == 0
