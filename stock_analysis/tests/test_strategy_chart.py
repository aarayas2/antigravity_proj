import pytest
import datetime
import pandas as pd
from unittest.mock import patch, MagicMock

from pages.strategy_chart import run_analysis_for_ticker

@pytest.fixture
def sample_metrics():
    return {
        "Total Return": 0.105,
        "Average Return": 0.012,
        "Number of Trades": 5,
        "Win Rate": 0.6
    }

@pytest.fixture
def sample_df():
    df = pd.DataFrame({
        'Close': [100, 101, 102],
        'Signal': [0.0, 0.0, 1.0]
    })
    return df

def test_run_analysis_load_data_none():
    start_date = datetime.date(2023, 1, 1)
    end_date = datetime.date(2023, 12, 31)

    with patch('pages.strategy_chart.load_data', return_value=None):
        result = run_analysis_for_ticker("AAPL", start_date, end_date)
        assert result is None

def test_run_analysis_load_data_empty():
    start_date = datetime.date(2023, 1, 1)
    end_date = datetime.date(2023, 12, 31)

    with patch('pages.strategy_chart.load_data', return_value=pd.DataFrame()):
        result = run_analysis_for_ticker("AAPL", start_date, end_date)
        assert result is None

@patch('pages.strategy_chart.STRATEGIES', {'MockStrategy': None})
@patch('pages.strategy_chart.load_data')
@patch('pages.strategy_chart.apply_strategy')
@patch('pages.strategy_chart.calculate_metrics')
@patch('pages.strategy_chart.create_strategy_chart')
def test_run_analysis_batch_mode(mock_create_chart, mock_calc_metrics, mock_apply_strategy, mock_load_data, sample_df, sample_metrics):
    mock_load_data.return_value = sample_df
    mock_apply_strategy.return_value = sample_df
    mock_calc_metrics.return_value = sample_metrics

    start_date = datetime.date(2023, 1, 1)
    end_date = datetime.date(2023, 12, 31)

    result = run_analysis_for_ticker("AAPL", start_date, end_date, is_batch_mode=True)

    assert result is not None
    assert "MockStrategy" in result["metrics"]
    assert result["metrics"]["MockStrategy"] == {
        "Total Return": 0.105,
        "Average Return": 0.012,
        "Number of Trades": 5,
        "Win Rate": 0.6
    }
    assert result["sections"] == []
    assert "MockStrategy" in result["buy_signals"]

    # Assert create_strategy_chart was not called since it's batch mode
    mock_create_chart.assert_not_called()

@patch('pages.strategy_chart.STRATEGIES', {'MockStrategy': None})
@patch('pages.strategy_chart.load_data')
@patch('pages.strategy_chart.apply_strategy')
@patch('pages.strategy_chart.calculate_metrics')
@patch('pages.strategy_chart.create_strategy_chart')
def test_run_analysis_interactive_mode(mock_create_chart, mock_calc_metrics, mock_apply_strategy, mock_load_data, sample_df, sample_metrics):
    mock_load_data.return_value = sample_df
    mock_apply_strategy.return_value = sample_df
    mock_calc_metrics.return_value = sample_metrics

    mock_fig = MagicMock()
    mock_create_chart.return_value = mock_fig

    start_date = datetime.date(2023, 1, 1)
    end_date = datetime.date(2023, 12, 31)

    result = run_analysis_for_ticker("AAPL", start_date, end_date, is_batch_mode=False)

    assert result is not None
    assert "MockStrategy" in result["metrics"]

    # Check that sections were populated
    assert len(result["sections"]) == 1

    # Check that create_strategy_chart was called
    mock_create_chart.assert_called_once()

    # In interactive mode, buy signals are not tracked in the same way (or rather, is_batch_mode check prevents it)
    assert result["buy_signals"] == []
