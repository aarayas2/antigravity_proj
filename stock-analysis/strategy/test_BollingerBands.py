import pytest
import pandas as pd
import pandas_ta
from unittest.mock import MagicMock
from strategy.BollingerBands import get_signals, apply_strategy, needs_subplots, add_traces

def test_needs_subplots():
    """Test needs_subplots returns False."""
    assert needs_subplots() is False

def test_add_traces_no_bbu_column():
    """Test add_traces does nothing when BBU column is missing."""
    fig = MagicMock()
    df = pd.DataFrame({'Close': [10, 20]})
    add_traces(fig, df, main_row=1, sub_row=2)
    fig.add_trace.assert_not_called()

def test_add_traces_with_bbu_column_main_row():
    """Test add_traces adds 3 traces to main_row when BBU column is present."""
    fig = MagicMock()
    df = pd.DataFrame({
        'BBU_20_2.0_2.0': [12, 22],
        'BBL_20_2.0_2.0': [8, 18],
        'BBM_20_2.0_2.0': [10, 20]
    })
    add_traces(fig, df, main_row=1, sub_row=None)
    assert fig.add_trace.call_count == 3
    # Check that row=1, col=1 was passed to add_trace
    for call in fig.add_trace.call_args_list:
        assert call[1]['row'] == 1
        assert call[1]['col'] == 1

def test_add_traces_with_bbu_column_no_main_row():
    """Test add_traces adds 3 traces without row/col kwargs when main_row is None."""
    fig = MagicMock()
    df = pd.DataFrame({
        'BBU_20_2.0_2.0': [12, 22],
        'BBL_20_2.0_2.0': [8, 18],
        'BBM_20_2.0_2.0': [10, 20]
    })
    add_traces(fig, df, main_row=None, sub_row=None)
    assert fig.add_trace.call_count == 3
    # Check that row/col weren't passed
    for call in fig.add_trace.call_args_list:
        assert 'row' not in call[1]
        assert 'col' not in call[1]

def test_get_signals_no_signal_column():
    """Test get_signals when DataFrame does not have a 'Signal' column."""
    df = pd.DataFrame({'Close': [10, 20, 30]})
    buy_signals, sell_signals = get_signals(df)

    assert isinstance(buy_signals, pd.DataFrame), "Buy signals should be a DataFrame."
    assert isinstance(sell_signals, pd.DataFrame), "Sell signals should be a DataFrame."
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame(), obj="Buy signals should be empty if 'Signal' column is missing.")
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame(), obj="Sell signals should be empty if 'Signal' column is missing.")

def test_get_signals_with_signal_column():
    """Test get_signals when DataFrame has a 'Signal' column."""
    df = pd.DataFrame({
        'Close': [10, 20, 30, 40],
        'Signal': [0.0, 1.0, -1.0, 1.0]
    })

    # Cast Signal to float to prevent numpy type issues during testing
    df['Signal'] = df['Signal'].astype(float)
    # Ensure compatible Index
    df.index = pd.Index([0, 1, 2, 3])

    buy_signals, sell_signals = get_signals(df)

    assert len(buy_signals) == 2, "Should find 2 buy signals (Signal == 1.0)."
    assert buy_signals.index.tolist() == [1, 3], "Buy signals should match indices 1 and 3."

    assert len(sell_signals) == 1, "Should find 1 sell signal (Signal == -1.0)."
    assert sell_signals.index.tolist() == [2], "Sell signal should match index 2."

def test_missing_signal_column_returns_empty_dataframes():
    """Passing a dataframe without the Signal column will return empty dataframes."""
    df = pd.DataFrame({'Close': [10.0, 20.0, 30.0]})
    buy_signals, sell_signals = get_signals(df)

    assert isinstance(buy_signals, pd.DataFrame), "Buy signals should be a DataFrame."
    assert isinstance(sell_signals, pd.DataFrame), "Sell signals should be a DataFrame."
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame(), obj="Buy signals should be empty if 'Signal' column is missing.")
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame(), obj="Sell signals should be empty if 'Signal' column is missing.")

def test_get_signals_empty_df():
    """Test get_signals with an empty DataFrame."""
    df = pd.DataFrame()
    buy_signals, sell_signals = get_signals(df)

    assert isinstance(buy_signals, pd.DataFrame), "Buy signals should be a DataFrame."
    assert isinstance(sell_signals, pd.DataFrame), "Sell signals should be a DataFrame."
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame(), obj="Buy signals should be empty for an empty DataFrame.")
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame(), obj="Sell signals should be empty for an empty DataFrame.")

def test_apply_strategy_with_mock_df():
    """Apply pandas-ta indicators to a mock dataframe and assert output shape and signals."""
    # Create a mock dataframe with > 20 rows to allow pandas_ta to compute actual indicators
    df = pd.DataFrame({'Close': [10] * 19 + [5, 15]})
    result = apply_strategy(df)

    # Assert the output shape: 21 rows, 8 columns (Close, BBL, BBM, BBU, BBB, BBP, Signal, Position)
    assert result.shape == (21, 8)

    # Assert signals: row 19 (index 19) dropped to 5 -> Buy (1.0)
    # row 20 (index 20) spiked to 15 -> Sell (-1.0)
    assert result['Signal'].iloc[19] == 1.0
    assert result['Signal'].iloc[20] == -1.0

def test_apply_strategy_normal():
    """Test apply_strategy with sufficient data to calculate Bollinger Bands."""
    # Need at least 20 rows for length=20
    df = pd.DataFrame({'Close': [10.0] * 19})

    # Row 19: Close = 10.0. BBM=10.0, BBU=10.0, BBL=10.0. No signal.
    df.loc[19] = {'Close': 10.0}

    # Row 20: Close drops to 5.0. BBL will be higher than 5.0 -> Buy signal (1.0)
    df.loc[20] = {'Close': 5.0}

    # Row 21: Close spikes to 20.0. BBU will be lower than 20.0 -> Sell signal (-1.0)
    df.loc[21] = {'Close': 20.0}

    # Row 22: Close returns to 10.0. Within bands -> Hold signal (0.0)
    df.loc[22] = {'Close': 10.0}

    result_df = apply_strategy(df)

    # Check that new columns are added
    assert 'BBL_20_2.0_2.0' in result_df.columns, "Lower band column missing."
    assert 'BBU_20_2.0_2.0' in result_df.columns, "Upper band column missing."
    assert 'Signal' in result_df.columns, "Signal column missing."
    assert 'Position' in result_df.columns, "Position column missing."

    # Check signals
    assert result_df['Signal'].iloc[19] == 0.0, "Expected no signal on row 19."
    assert result_df['Signal'].iloc[20] == 1.0, "Expected buy signal on row 20 (price dropped below lower band)."
    assert result_df['Signal'].iloc[21] == -1.0, "Expected sell signal on row 21 (price spiked above upper band)."
    assert result_df['Signal'].iloc[22] == 0.0, "Expected no signal on row 22 (price within bands)."

def test_apply_strategy_insufficient_data():
    """Test apply_strategy with insufficient data (less than 20 rows)."""
    df = pd.DataFrame({'Close': [10.0] * 10})
    result_df = apply_strategy(df)

    # Should just return the original DataFrame shape since bands couldn't be calculated
    assert 'BBL_20_2.0_2.0' not in result_df.columns, "Should not add BBL column with insufficient data."
    assert 'Signal' not in result_df.columns, "Should not add Signal column with insufficient data."

def test_apply_strategy_empty_dataframe():
    """Test apply_strategy with an empty DataFrame."""
    df = pd.DataFrame()
    result_df = apply_strategy(df)

    assert isinstance(result_df, pd.DataFrame), "Should return a DataFrame."
    pd.testing.assert_frame_equal(result_df, pd.DataFrame()), "Should return an empty DataFrame."
