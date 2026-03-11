import pytest
from unittest.mock import patch, MagicMock
import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import run_batch_mode

class TestApp:

    @patch('app.get_date_ranges')
    def test_run_batch_mode_no_valid_tickers(self, mock_get_date_ranges):
        result = run_batch_mode("")
        assert result is None
        mock_get_date_ranges.assert_not_called()

        result2 = run_batch_mode("   ;  ")
        assert result2 is None
        mock_get_date_ranges.assert_not_called()

    @patch('app.stats_manager')
    @patch('app.run_analysis_for_ticker')
    @patch('app.get_date_ranges')
    def test_run_batch_mode_success(self, mock_get_date_ranges, mock_run_analysis, mock_stats_manager):
        min_date = datetime.datetime(2023, 1, 1)
        max_date = datetime.datetime(2023, 12, 31)
        mock_get_date_ranges.return_value = {
            "min_date": min_date,
            "max_date": max_date
        }

        mock_run_analysis.side_effect = [
            {
                "metrics": {"strat1": {"return": 10}},
                "buy_signals": ["strat1", "strat2"]
            },
            {
                "metrics": {"strat2": {"return": -5}},
                "buy_signals": ["strat2"]
            }
        ]

        result = run_batch_mode("AAPL;MSFT")

        assert result == {
            "strat1": ["AAPL"],
            "strat2": ["AAPL", "MSFT"]
        }

        mock_run_analysis.assert_any_call("AAPL", min_date, max_date, is_batch_mode=True)
        mock_run_analysis.assert_any_call("MSFT", min_date, max_date, is_batch_mode=True)
        assert mock_run_analysis.call_count == 2

        mock_stats_manager.save_stats_batch.assert_called_once()
        saved_batch = mock_stats_manager.save_stats_batch.call_args[0][0]
        assert len(saved_batch) == 2
        assert saved_batch[0]["ticker"] == "AAPL"
        assert saved_batch[0]["date_begin"] == "2023-01-01"
        assert saved_batch[0]["date_end"] == "2023-12-31"
        assert saved_batch[0]["strategies_metrics"] == {"strat1": {"return": 10}}

        assert saved_batch[1]["ticker"] == "MSFT"
        assert saved_batch[1]["date_begin"] == "2023-01-01"
        assert saved_batch[1]["date_end"] == "2023-12-31"
        assert saved_batch[1]["strategies_metrics"] == {"strat2": {"return": -5}}


    @patch('app.stats_manager')
    @patch('app.run_analysis_for_ticker')
    @patch('app.get_date_ranges')
    def test_run_batch_mode_partial_failure(self, mock_get_date_ranges, mock_run_analysis, mock_stats_manager):
        min_date = datetime.datetime(2023, 1, 1)
        max_date = datetime.datetime(2023, 12, 31)
        mock_get_date_ranges.return_value = {
            "min_date": min_date,
            "max_date": max_date
        }

        # First succeeds, second fails (returns None)
        mock_run_analysis.side_effect = [
            {
                "metrics": {"strat1": {"return": 10}},
                "buy_signals": ["strat1"]
            },
            None
        ]

        result = run_batch_mode("AAPL;INVALID_TICKER")

        assert result == {
            "strat1": ["AAPL"]
        }

        assert mock_run_analysis.call_count == 2
        mock_stats_manager.save_stats_batch.assert_called_once()

        saved_batch = mock_stats_manager.save_stats_batch.call_args[0][0]
        assert len(saved_batch) == 1
        assert saved_batch[0]["ticker"] == "AAPL"


    @patch('app.stats_manager')
    @patch('app.run_analysis_for_ticker')
    @patch('app.get_date_ranges')
    def test_run_batch_mode_deduplication(self, mock_get_date_ranges, mock_run_analysis, mock_stats_manager):
        min_date = datetime.datetime(2023, 1, 1)
        max_date = datetime.datetime(2023, 12, 31)
        mock_get_date_ranges.return_value = {
            "min_date": min_date,
            "max_date": max_date
        }

        mock_run_analysis.side_effect = [
            {
                "metrics": {"strat1": {"return": 10}},
                "buy_signals": ["strat1"]
            }
        ]

        # Call with duplicates
        result = run_batch_mode("AAPL;AAPL")

        assert result == {
            "strat1": ["AAPL"]
        }

        assert mock_run_analysis.call_count == 1

        mock_stats_manager.save_stats_batch.assert_called_once()
        saved_batch = mock_stats_manager.save_stats_batch.call_args[0][0]
        assert len(saved_batch) == 1
        assert saved_batch[0]["ticker"] == "AAPL"
