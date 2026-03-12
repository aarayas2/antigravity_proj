import os
import sys
import pandas as pd
import numpy as np
import pandas_ta as ta    # Required to inject .ta into pandas DataFrame
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
    '..')))
from strategy.BollingerBands import apply_strategy


def test_bollinger_bands_apply_strategy():
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=30)
    closes = np.full(30, 100.0)
    closes = closes + np.random.normal(0, 1, 30)
    closes[25] = 120.0
    closes[28] = 80.0
    df = pd.DataFrame({'Close': closes}, index=dates)
    result_df = apply_strategy(df)
    assert 'BBL_20_2.0_2.0' in result_df.columns
    assert 'BBU_20_2.0_2.0' in result_df.columns
    assert 'Signal' in result_df.columns
    assert 'Position' in result_df.columns
    assert result_df['Signal'].iloc[0] == 0.0
    assert result_df['Signal'].iloc[25] == -1.0
    assert result_df['Signal'].iloc[28] == 1.0


def test_bollinger_bands_not_enough_data():
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=10)
    closes = np.full(10, 100.0) + np.random.normal(0, 1, 10)
    df = pd.DataFrame({'Close': closes}, index=dates)
    result_df = apply_strategy(df)
    assert 'BBL_20_2.0_2.0' not in result_df.columns
    assert 'BBU_20_2.0_2.0' not in result_df.columns
    assert 'Signal' not in result_df.columns
    assert 'Position' not in result_df.columns


def test_bollinger_bands_empty_df():
    df = pd.DataFrame(columns=['Close'])
    result_df = apply_strategy(df)
    assert 'BBL_20_2.0_2.0' not in result_df.columns
    assert 'Signal' not in result_df.columns


from strategy.BollingerBands import get_signals


def test_bollinger_bands_get_signals_with_signals():
    dates = pd.date_range(start='2023-01-01', periods=5)
    df = pd.DataFrame({'Close': [100.0, 105.0, 95.0, 110.0, 90.0], 'Signal':
        [0.0, -1.0, 1.0, -1.0, 1.0]}, index=dates)
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
    dates = pd.date_range(start='2023-01-01', periods=3)
    df = pd.DataFrame({'Close': [100.0, 105.0, 95.0]}, index=dates)
    buy_signals, sell_signals = get_signals(df)
    assert isinstance(buy_signals, pd.DataFrame)
    assert isinstance(sell_signals, pd.DataFrame)
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame(), obj=
        "Buy signals should be empty if 'Signal' column is missing.")
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame(), obj=
        "Sell signals should be empty if 'Signal' column is missing.")


def test_bollinger_bands_get_signals_empty_df():
    df = pd.DataFrame()
    buy_signals, sell_signals = get_signals(df)
    assert isinstance(buy_signals, pd.DataFrame)
    assert isinstance(sell_signals, pd.DataFrame)
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame(), obj=
        'Buy signals should be empty for an empty DataFrame.')
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame(), obj=
        'Sell signals should be empty for an empty DataFrame.')


def test_bollinger_bands_get_signals_all_zero():
    dates = pd.date_range(start='2023-01-01', periods=3)
    df = pd.DataFrame({'Close': [100.0, 105.0, 95.0], 'Signal': [0.0, 0.0, 
        0.0]}, index=dates)
    buy_signals, sell_signals = get_signals(df)
    assert isinstance(buy_signals, pd.DataFrame)
    assert isinstance(sell_signals, pd.DataFrame)
    assert len(buy_signals
        ) == 0, 'Buy signals should be empty if there are no 1.0 signals.'
    assert len(sell_signals
        ) == 0, 'Sell signals should be empty if there are no -1.0 signals.'


from strategy.BollingerBands import needs_subplots, add_traces
from unittest.mock import MagicMock


def test_needs_subplots():
    assert needs_subplots() is False


from unittest.mock import patch


@patch('strategy.BollingerBands.go.Scatter')
def test_add_traces_with_subplots(mock_scatter):
    fig = MagicMock()
    df = pd.DataFrame({'BBU_20_2.0_2.0': [100.0, 105.0], 'BBL_20_2.0_2.0':
        [90.0, 95.0], 'BBM_20_2.0_2.0': [95.0, 100.0]}, index=pd.date_range
        (start='2023-01-01', periods=2))
    add_traces(fig, df, main_row=1, sub_row=None)
    assert fig.add_trace.call_count == 3
    for call in fig.add_trace.call_args_list:
        _, kwargs = call
        assert kwargs.get('row') == 1
        assert kwargs.get('col') == 1


@patch('strategy.BollingerBands.go.Scatter')
def test_add_traces_no_subplots(mock_scatter):
    fig = MagicMock()
    df = pd.DataFrame({'BBU_20_2.0_2.0': [100.0, 105.0], 'BBL_20_2.0_2.0':
        [90.0, 95.0], 'BBM_20_2.0_2.0': [95.0, 100.0]}, index=pd.date_range
        (start='2023-01-01', periods=2))
    add_traces(fig, df, main_row=None, sub_row=None)
    assert fig.add_trace.call_count == 3
    for call in fig.add_trace.call_args_list:
        _, kwargs = call
        assert kwargs.get('row') is None


def test_add_traces_no_bbands():
    fig = MagicMock()
    df = pd.DataFrame({'Close': [100.0, 105.0]}, index=pd.date_range(start=
        '2023-01-01', periods=2))
    add_traces(fig, df, main_row=1, sub_row=None)
    assert fig.add_trace.call_count == 0


def test_apply_strategy_with_mock_df():
    """Apply pandas-ta indicators to a mock dataframe and assert output shape and signals."""
    df = pd.DataFrame({'Close': [10] * 19 + [5, 15]})
    result = apply_strategy(df)
    assert result.shape == (21, 8)
    assert result['Signal'].iloc[19] == 1.0
    assert result['Signal'].iloc[20] == -1.0


import pytest
import pandas as pd
import pandas_ta    # Required to inject .ta into pandas DataFrame
from unittest.mock import MagicMock
from strategy.BollingerBands import get_signals, apply_strategy, needs_subplots, add_traces
from unittest.mock import patch


def test_add_traces_no_bbu_column():
    """Test add_traces does nothing when BBU column is missing."""
    fig = MagicMock()
    df = pd.DataFrame({'Close': [10, 20]})
    add_traces(fig, df, main_row=1, sub_row=2)
    fig.add_trace.assert_not_called()


@patch('strategy.BollingerBands.go.Scatter')
def test_add_traces_with_bbu_column_main_row(mock_scatter):
    """Test add_traces adds 3 traces to main_row when BBU column is present."""
    fig = MagicMock()
    df = pd.DataFrame({'BBU_20_2.0_2.0': [12, 22], 'BBL_20_2.0_2.0': [8, 18
        ], 'BBM_20_2.0_2.0': [10, 20]})
    mock_scatter_instance = MagicMock()
    mock_scatter.return_value = mock_scatter_instance
    add_traces(fig, df, main_row=1, sub_row=None)
    assert fig.add_trace.call_count == 3
    for call in fig.add_trace.call_args_list:
        assert call[1]['row'] == 1
        assert call[1]['col'] == 1
        assert call[0][0] == mock_scatter_instance


@patch('strategy.BollingerBands.go.Scatter')
def test_add_traces_with_bbu_column_no_main_row(mock_scatter):
    """Test add_traces adds 3 traces without row/col kwargs when main_row is None."""
    fig = MagicMock()
    df = pd.DataFrame({'BBU_20_2.0_2.0': [12, 22], 'BBL_20_2.0_2.0': [8, 18
        ], 'BBM_20_2.0_2.0': [10, 20]})
    mock_scatter_instance = MagicMock()
    mock_scatter.return_value = mock_scatter_instance
    add_traces(fig, df, main_row=None, sub_row=None)
    assert fig.add_trace.call_count == 3
    for call in fig.add_trace.call_args_list:
        assert 'row' not in call[1]
        assert 'col' not in call[1]
        assert call[0][0] == mock_scatter_instance


def test_get_signals_no_signal_column():
    """Test get_signals when DataFrame does not have a 'Signal' column."""
    df = pd.DataFrame({'Close': [10, 20, 30]})
    buy_signals, sell_signals = get_signals(df)
    assert isinstance(buy_signals, pd.DataFrame
        ), 'Buy signals should be a DataFrame.'
    assert isinstance(sell_signals, pd.DataFrame
        ), 'Sell signals should be a DataFrame.'
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame(), obj=
        "Buy signals should be empty if 'Signal' column is missing.")
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame(), obj=
        "Sell signals should be empty if 'Signal' column is missing.")


def test_get_signals_with_signal_column():
    """Test get_signals when DataFrame has a 'Signal' column."""
    df = pd.DataFrame({'Close': [10, 20, 30, 40], 'Signal': [0.0, 1.0, -1.0,
        1.0]})
    df['Signal'] = df['Signal'].astype(float)
    df.index = pd.Index([0, 1, 2, 3])
    buy_signals, sell_signals = get_signals(df)
    assert len(buy_signals) == 2, 'Should find 2 buy signals (Signal == 1.0).'
    assert buy_signals.index.tolist() == [1, 3
        ], 'Buy signals should match indices 1 and 3.'
    assert len(sell_signals
        ) == 1, 'Should find 1 sell signal (Signal == -1.0).'
    assert sell_signals.index.tolist() == [2
        ], 'Sell signal should match index 2.'


def test_missing_signal_column_returns_empty_dataframes():
    """Passing a dataframe without the Signal column will return empty dataframes."""
    df = pd.DataFrame({'Close': [10.0, 20.0, 30.0]})
    buy_signals, sell_signals = get_signals(df)
    assert isinstance(buy_signals, pd.DataFrame
        ), 'Buy signals should be a DataFrame.'
    assert isinstance(sell_signals, pd.DataFrame
        ), 'Sell signals should be a DataFrame.'
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame(), obj=
        "Buy signals should be empty if 'Signal' column is missing.")
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame(), obj=
        "Sell signals should be empty if 'Signal' column is missing.")


def test_get_signals_empty_df():
    """Test get_signals with an empty DataFrame."""
    df = pd.DataFrame()
    buy_signals, sell_signals = get_signals(df)
    assert isinstance(buy_signals, pd.DataFrame
        ), 'Buy signals should be a DataFrame.'
    assert isinstance(sell_signals, pd.DataFrame
        ), 'Sell signals should be a DataFrame.'
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame(), obj=
        'Buy signals should be empty for an empty DataFrame.')
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame(), obj=
        'Sell signals should be empty for an empty DataFrame.')


def test_apply_strategy_normal():
    """Test apply_strategy with sufficient data to calculate Bollinger Bands."""
    df = pd.DataFrame({'Close': [10.0] * 19})
    df.loc[19, 'Close'] = 10.0
    df.loc[20, 'Close'] = 5.0
    df.loc[21, 'Close'] = 20.0
    df.loc[22, 'Close'] = 10.0
    result_df = apply_strategy(df)
    assert 'BBL_20_2.0_2.0' in result_df.columns, 'Lower band column missing.'
    assert 'BBU_20_2.0_2.0' in result_df.columns, 'Upper band column missing.'
    assert 'Signal' in result_df.columns, 'Signal column missing.'
    assert 'Position' in result_df.columns, 'Position column missing.'
    assert result_df['Signal'].iloc[19] == 0.0, 'Expected no signal on row 19.'
    assert result_df['Signal'].iloc[20
        ] == 1.0, 'Expected buy signal on row 20 (price dropped below lower band).'
    assert result_df['Signal'].iloc[21
        ] == -1.0, 'Expected sell signal on row 21 (price spiked above upper band).'
    assert result_df['Signal'].iloc[22
        ] == 0.0, 'Expected no signal on row 22 (price within bands).'


def test_apply_strategy_insufficient_data():
    """Test apply_strategy with insufficient data (less than 20 rows)."""
    df = pd.DataFrame({'Close': [10.0] * 10})
    result_df = apply_strategy(df)
    assert 'BBL_20_2.0_2.0' not in result_df.columns, 'Should not add BBL column with insufficient data.'
    assert 'Signal' not in result_df.columns, 'Should not add Signal column with insufficient data.'


def test_apply_strategy_empty_dataframe():
    """Test apply_strategy with an empty DataFrame."""
    df = pd.DataFrame()
    result_df = apply_strategy(df)
    assert isinstance(result_df, pd.DataFrame), 'Should return a DataFrame.'
    pd.testing.assert_frame_equal(result_df, pd.DataFrame()
        ), 'Should return an empty DataFrame.'


def test_get_signals_no_signals_in_column():
    """Test get_signals when DataFrame has a 'Signal' column but no 1.0 or -1.0 signals."""
    df = pd.DataFrame({'Close': [10.0, 20.0, 30.0], 'Signal': [0.0, 0.0, 0.0]})
    buy_signals, sell_signals = get_signals(df)
    assert isinstance(buy_signals, pd.DataFrame
        ), 'Buy signals should be a DataFrame.'
    assert isinstance(sell_signals, pd.DataFrame
        ), 'Sell signals should be a DataFrame.'
    expected_empty = pd.DataFrame(columns=['Close', 'Signal']).astype(float)
    pd.testing.assert_frame_equal(buy_signals, expected_empty,
        check_index_type=False)
    pd.testing.assert_frame_equal(sell_signals, expected_empty,
        check_index_type=False)


def test_get_signals_missing_signal_column():
    """
    Test explicitly the requirement:
    Passing a dataframe without the Signal column will return empty dataframes.
    The test requires asserting the returned dataframes are indeed empty.
    """
    df = pd.DataFrame({'Close': [10.0, 20.0, 30.0]})
    buy_signals, sell_signals = get_signals(df)
    assert isinstance(buy_signals, pd.DataFrame)
    assert isinstance(sell_signals, pd.DataFrame)
    pd.testing.assert_frame_equal(buy_signals, pd.DataFrame())
    pd.testing.assert_frame_equal(sell_signals, pd.DataFrame())


def test_apply_strategy_with_mock_df_15_lines():
    """Applying pandas-ta indicators to a mock dataframe and asserting the output shape and signals."""
    import pandas_ta
    df = pd.DataFrame({'Close': [10.0] * 19 + [5.0, 15.0]})
    result = apply_strategy(df)
    assert result.shape == (21, 8
        ), f'Expected shape (21, 8), got {result.shape}'
    assert result['Signal'].iloc[19
        ] == 1.0, 'Expected buy signal on price drop below lower band.'
    assert result['Signal'].iloc[20
        ] == -1.0, 'Expected sell signal on price spike above upper band.'
