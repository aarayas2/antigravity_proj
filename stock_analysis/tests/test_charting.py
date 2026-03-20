"""Unit tests for the charting module."""
from unittest.mock import MagicMock, patch

import pandas as pd

from charting import (
    MockFig,
    _setup_figure,
    _add_trade_traces,
    _add_candlestick_trace,
    _add_strategy_traces,
    _add_signal_traces,
    _add_traces,
    _update_layout,
    create_strategy_chart
)

def test_mock_fig():
    """Test the MockFig wrapper around Plotly figures."""
    mock_internal_fig = MagicMock()
    mock_fig = MockFig(mock_internal_fig)

    mock_trace = MagicMock()
    mock_fig.add_trace(mock_trace, row=1, col=2)
    mock_internal_fig.add_trace.assert_called_once_with(mock_trace)

    mock_fig.update_layout(title="Test")
    mock_internal_fig.update_layout.assert_called_once_with(title="Test")

    mock_fig.add_vrect(x0=0, x1=1)
    mock_internal_fig.add_vrect.assert_called_once_with(x0=0, x1=1)

    mock_fig.add_hline(y=10)
    mock_internal_fig.add_hline.assert_called_once_with(y=10)

@patch('charting.make_subplots')
@patch('charting.go.Figure')
@patch('charting.STRATEGIES', {
    "WithSubplots": {"needs_subplots": lambda: True},
    "WithoutSubplots": {"needs_subplots": lambda: False}
})
def test_setup_figure(mock_go_figure, mock_make_subplots):
    """Test figure setup with and without subplots."""
    # Test strategy with subplots
    mock_make_subplots.return_value = "SubplotFig"
    fig, main_row, sub_row = _setup_figure("WithSubplots")

    assert fig == "SubplotFig"
    assert main_row == 1
    assert sub_row == 2
    mock_make_subplots.assert_called_once()

    mock_make_subplots.reset_mock()

    # Test strategy without subplots
    mock_go_figure.return_value = "GoFig"
    fig, main_row, sub_row = _setup_figure("WithoutSubplots")

    assert fig == "GoFig"
    assert main_row is None
    assert sub_row is None
    mock_go_figure.assert_called_once()

    mock_go_figure.reset_mock()

    # Test unknown strategy (defaults to without subplots)
    mock_go_figure.return_value = "GoFig2"
    fig, main_row, sub_row = _setup_figure("UnknownStrategy")

    assert fig == "GoFig2"
    assert main_row is None
    assert sub_row is None
    mock_go_figure.assert_called_once()

@patch('charting.TradeTooltipFactory')
def test_add_trade_traces(mock_tooltip_factory_class):
    """Test adding trade execution traces."""
    mock_fig = MagicMock()
    df_with_signals = pd.DataFrame({
        'Low': [100, 95, 105],
        'High': [110, 105, 115]
    })

    mock_factory_instance = MagicMock()
    mock_tooltip_factory_class.return_value = mock_factory_instance
    mock_factory_instance.create_trace.side_effect = ["trace1", None, "trace3"]

    metrics = {
        "Trades History": [
            {"trade": 1},
            {"trade": 2},
            {"trade": 3}
        ]
    }

    # Test with main_row
    _add_trade_traces(mock_fig, df_with_signals, metrics, main_row=1)

    # Expected min = 95 * 0.95 = 90.25
    # Expected max = 115 * 1.05 = 120.75
    mock_tooltip_factory_class.assert_called_once_with(y_min=90.25, y_max=120.75)

    assert mock_factory_instance.create_trace.call_count == 3

    assert mock_fig.add_trace.call_count == 2
    mock_fig.add_trace.assert_any_call("trace1", row=1, col=1)
    mock_fig.add_trace.assert_any_call("trace3", row=1, col=1)

    mock_fig.reset_mock()
    mock_factory_instance.create_trace.reset_mock()
    mock_tooltip_factory_class.reset_mock()
    mock_factory_instance.create_trace.side_effect = ["trace1"]

    metrics = {
        "Trades History": [{"trade": 1}]
    }

    # Test without main_row
    _add_trade_traces(mock_fig, df_with_signals, metrics, main_row=None)
    mock_tooltip_factory_class.assert_called_once_with(y_min=90.25, y_max=120.75)
    mock_fig.add_trace.assert_called_once_with("trace1")

def test_add_trade_traces_empty():
    """Test adding trade traces when data is empty."""
    mock_fig = MagicMock()
    df_with_signals = pd.DataFrame()
    metrics = {"Trades History": [{"trade": 1}]}

    # Empty DataFrame should do nothing
    _add_trade_traces(mock_fig, df_with_signals, metrics, main_row=1)
    mock_fig.add_trace.assert_not_called()

    mock_fig.reset_mock()
    df_with_signals = pd.DataFrame({'Low': [100], 'High': [110]})
    metrics = {"Trades History": []}

    # Empty trades history should do nothing
    _add_trade_traces(mock_fig, df_with_signals, metrics, main_row=1)
    mock_fig.add_trace.assert_not_called()

@patch('charting.go.Candlestick')
def test_add_candlestick_trace(mock_candlestick):
    """Test adding the main candlestick trace."""
    mock_fig = MagicMock()
    df = pd.DataFrame({
        'Open': [100],
        'High': [110],
        'Low': [90],
        'Close': [105]
    })

    mock_trace = MagicMock()
    mock_candlestick.return_value = mock_trace

    # Test with main_row
    _add_candlestick_trace(mock_fig, df, main_row=1)
    mock_candlestick.assert_called_once()
    mock_fig.add_trace.assert_called_once_with(mock_trace, row=1, col=1)

    mock_candlestick.reset_mock()
    mock_fig.reset_mock()

    # Test without main_row
    _add_candlestick_trace(mock_fig, df, main_row=None)
    mock_candlestick.assert_called_once()
    mock_fig.add_trace.assert_called_once_with(mock_trace)

def test_add_strategy_traces():
    """Test adding strategy-specific indicator traces."""
    mock_add_traces = MagicMock()

    with patch('charting.STRATEGIES', {
        "KnownStrategy": {"add_traces": mock_add_traces}
    }):
        mock_fig = MagicMock()
        df = pd.DataFrame()

        # Test known strategy
        _add_strategy_traces(mock_fig, df, "KnownStrategy", main_row=1, sub_row=2)
        mock_add_traces.assert_called_once_with(mock_fig, df, 1, 2)

        mock_add_traces.reset_mock()

        # Test unknown strategy
        _add_strategy_traces(mock_fig, df, "UnknownStrategy", main_row=1, sub_row=2)
        mock_add_traces.assert_not_called()

@patch('charting.go.Scatter')
def test_add_signal_traces(mock_scatter):
    """Test adding buy and sell signal traces."""
    buy_df = pd.DataFrame({'Low': [100]}, index=[1])
    sell_df = pd.DataFrame({'High': [110]}, index=[2])

    mock_get_signals = MagicMock(return_value=(buy_df, sell_df))

    with patch('charting.STRATEGIES', {
        "KnownStrategy": {"get_signals": mock_get_signals}
    }):
        mock_fig = MagicMock()
        df = pd.DataFrame()

        mock_buy_trace = MagicMock()
        mock_sell_trace = MagicMock()
        mock_scatter.side_effect = [mock_buy_trace, mock_sell_trace]

        # Test known strategy with main_row
        _add_signal_traces(mock_fig, df, "KnownStrategy", main_row=1)
        mock_get_signals.assert_called_once_with(df)

        assert mock_scatter.call_count == 2
        mock_fig.add_trace.assert_any_call(mock_buy_trace, row=1, col=1)
        mock_fig.add_trace.assert_any_call(mock_sell_trace, row=1, col=1)

        mock_scatter.reset_mock()
        mock_fig.reset_mock()
        mock_scatter.side_effect = [mock_buy_trace, mock_sell_trace]

        # Test known strategy without main_row
        _add_signal_traces(mock_fig, df, "KnownStrategy", main_row=None)

        assert mock_scatter.call_count == 2
        mock_fig.add_trace.assert_any_call(mock_buy_trace)
        mock_fig.add_trace.assert_any_call(mock_sell_trace)

        mock_scatter.reset_mock()
        mock_fig.reset_mock()

        # Test unknown strategy
        _add_signal_traces(mock_fig, df, "UnknownStrategy", main_row=1)
        mock_scatter.assert_not_called()
        mock_fig.add_trace.assert_not_called()

@patch('charting._add_trade_traces')
@patch('charting._add_candlestick_trace')
@patch('charting._add_strategy_traces')
@patch('charting._add_signal_traces')
def test_add_traces(mock_add_signals, mock_add_strategy, mock_add_candlestick, mock_add_trades):
    """Test the orchestrated addition of all chart traces."""
    mock_fig = MagicMock()
    df = pd.DataFrame()
    metrics = {"Total Return": 0.1}

    _add_traces(mock_fig, df, "Strategy", metrics, 1, 2)

    mock_add_trades.assert_called_once_with(mock_fig, df, metrics, 1)
    mock_add_candlestick.assert_called_once_with(mock_fig, df, 1)
    mock_add_strategy.assert_called_once_with(mock_fig, df, "Strategy", 1, 2)
    mock_add_signals.assert_called_once_with(mock_fig, df, "Strategy", 1)

def test_update_layout():
    """Test Plotly layout updates including range selector."""
    mock_fig = MagicMock()

    rangeselector = {
        "bgcolor": "#1f2937",
        "activecolor": "#374151",
        "buttons": [
            {"count": 1, "label": "1m", "step": "month", "stepmode": "backward"},
            {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
            {"count": 1, "label": "1y", "step": "year", "stepmode": "backward"},
            {"step": "all"}
        ]
    }

    # Test with main_row
    _update_layout(mock_fig, main_row=1)
    mock_fig.update_layout.assert_called_once_with(
        height=700, template="plotly_dark",
        margin={"l": 0, "r": 0, "t": 30, "b": 0}
    )
    assert mock_fig.update_xaxes.call_count == 2
    mock_fig.update_xaxes.assert_any_call(rangeslider_visible=False,
                                          rangeselector=rangeselector, row=1, col=1)
    mock_fig.update_xaxes.assert_any_call(rangeslider_visible=False, row=2, col=1)

    mock_fig.reset_mock()

    # Test without main_row
    _update_layout(mock_fig, main_row=None)
    mock_fig.update_layout.assert_called_once_with(
        height=700, template="plotly_dark",
        margin={"l": 0, "r": 0, "t": 30, "b": 0}
    )
    assert mock_fig.update_xaxes.call_count == 1
    mock_fig.update_xaxes.assert_any_call(rangeslider_visible=False, rangeselector=rangeselector)

@patch('charting._setup_figure')
@patch('charting._add_traces')
@patch('charting._update_layout')
def test_create_strategy_chart(mock_update_layout, mock_add_traces, mock_setup_figure):
    """Test the full strategy chart creation pipeline."""
    mock_fig = MagicMock()
    mock_setup_figure.return_value = (mock_fig, 1, 2)

    df = pd.DataFrame()
    metrics = {"Total Return": 0.1}

    fig = create_strategy_chart(df, "Strategy", metrics)

    assert fig == mock_fig
    mock_setup_figure.assert_called_once_with("Strategy")
    mock_add_traces.assert_called_once_with(mock_fig, df, "Strategy", metrics, 1, 2)
    mock_update_layout.assert_called_once_with(mock_fig, 1)
