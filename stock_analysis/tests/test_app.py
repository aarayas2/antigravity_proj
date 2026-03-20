"""
Tests for the main app module and batch processing.
"""
import sys
import os
import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import run_batch_mode, display_page  # pylint: disable=wrong-import-position


class TestApp:
    """Tests for run_batch_mode in the app module."""

    @patch('app.get_date_ranges')
    def test_run_batch_mode_no_valid_tickers(self, mock_get_date_ranges):
        """Test run_batch_mode with empty or invalid ticker strings."""
        result = run_batch_mode("")
        assert not result
        mock_get_date_ranges.assert_not_called()

        result2 = run_batch_mode("   ;  ")
        assert not result2
        mock_get_date_ranges.assert_not_called()

    @patch('app.stats_manager')
    @patch('app.run_analysis_for_ticker')
    @patch('app.get_date_ranges')
    def test_run_batch_mode_success(
        self, mock_get_date_ranges, mock_run_analysis, mock_stats_manager
    ):
        """Test successful run of batch mode on valid tickers."""
        min_date = datetime.datetime(2023, 1, 1)
        max_date = datetime.datetime(2023, 12, 31)
        mock_get_date_ranges.return_value = {
            "min_date": min_date,
            "max_date": max_date
        }

        # In thread pool, the order of calls is not guaranteed.
        # So we mock a side effect based on the ticker name instead of a list.
        def mock_run_analysis_side_effect(ticker, *args, **kwargs):
            if ticker == "AAPL":
                return {
                    "metrics": {"strat1": {"return": 10}},
                    "buy_signals": ["strat1", "strat2"]
                }
            if ticker == "MSFT":
                return {
                    "metrics": {"strat2": {"return": -5}},
                    "buy_signals": ["strat2"]
                }
            return None

        mock_run_analysis.side_effect = mock_run_analysis_side_effect

        result = run_batch_mode("AAPL;MSFT")

        # Due to thread pool execution, order in lists can vary, so we check sets.
        expected = {
            "strat1": {"AAPL"},
            "strat2": {"AAPL", "MSFT"}
        }
        result_sets = {k: set(v) for k, v in result.items()}
        assert result_sets == expected

        mock_run_analysis.assert_any_call("AAPL", min_date, max_date, is_batch_mode=True)
        mock_run_analysis.assert_any_call("MSFT", min_date, max_date, is_batch_mode=True)
        assert mock_run_analysis.call_count == 2

        mock_stats_manager.save_stats_batch.assert_called_once()
        saved_batch = mock_stats_manager.save_stats_batch.call_args[0][0]
        assert len(saved_batch) == 2

        # Sort saved_batch to ensure consistent order due to threading
        saved_batch_sorted = sorted(saved_batch, key=lambda x: x["ticker"])

        assert saved_batch_sorted[0]["ticker"] == "AAPL"
        assert saved_batch_sorted[0]["date_begin"] == "2023-01-01"
        assert saved_batch_sorted[0]["date_end"] == "2023-12-31"
        assert saved_batch_sorted[0]["strategies_metrics"] == {"strat1": {"return": 10}}

        assert saved_batch_sorted[1]["ticker"] == "MSFT"
        assert saved_batch_sorted[1]["date_begin"] == "2023-01-01"
        assert saved_batch_sorted[1]["date_end"] == "2023-12-31"
        assert saved_batch_sorted[1]["strategies_metrics"] == {"strat2": {"return": -5}}


    @patch('app.stats_manager')
    @patch('app.run_analysis_for_ticker')
    @patch('app.get_date_ranges')
    def test_run_batch_mode_partial_failure(
        self, mock_get_date_ranges, mock_run_analysis, mock_stats_manager
    ):
        """Test run of batch mode where one ticker succeeds and another fails."""
        min_date = datetime.datetime(2023, 1, 1)
        max_date = datetime.datetime(2023, 12, 31)
        mock_get_date_ranges.return_value = {
            "min_date": min_date,
            "max_date": max_date
        }

        # In thread pool, the order of calls is not guaranteed.
        # So we mock a side effect based on the ticker name instead of a list.
        def mock_run_analysis_side_effect(ticker, *args, **kwargs):
            if ticker == "AAPL":
                return {
                    "metrics": {"strat1": {"return": 10}},
                    "buy_signals": ["strat1"]
                }
            return None

        mock_run_analysis.side_effect = mock_run_analysis_side_effect

        result = run_batch_mode("AAPL;INVALID_TICKER")

        assert result == {
            "strat1": ["AAPL"]
        }

        assert mock_run_analysis.call_count == 2
        mock_stats_manager.save_stats_batch.assert_called_once()

        saved_batch = mock_stats_manager.save_stats_batch.call_args[0][0]
        assert len(saved_batch) == 1
        assert saved_batch[0]["ticker"] == "AAPL"


class TestAppMain:
    """Tests for the main execution block of the app module."""

    @patch('app.get_date_ranges')
    @patch('app.run_analysis_for_ticker')
    @patch('app.stats_manager')
    @patch('app.app.run')
    @patch('sys.argv', ['app.py', '--ticker', 'AAPL'])
    def test_main_batch_mode_execution(
        self, mock_app_run, mock_stats_manager, mock_run_analysis, mock_get_date_ranges
    ):
        """
        Tests that running `main()` with `--ticker AAPL` properly calls into
        `run_batch_mode` and executes its logic, without mocking `run_batch_mode` itself.
        """
        import app  # pylint: disable=import-outside-toplevel

        min_date = datetime.datetime(2023, 1, 1)
        max_date = datetime.datetime(2023, 12, 31)
        mock_get_date_ranges.return_value = {
            "min_date": min_date,
            "max_date": max_date
        }

        mock_run_analysis.return_value = {
            "metrics": {"strat1": {"return": 10}},
            "buy_signals": ["strat1"]
        }

        app.main()

        mock_run_analysis.assert_called_once_with("AAPL", min_date, max_date, is_batch_mode=True)
        mock_stats_manager.save_stats_batch.assert_called_once()
        mock_app_run.assert_not_called()

    @patch('app.app.run')
    @patch('sys.argv', ['app.py'])
    def test_main_server_mode(self, mock_app_run):
        """Test server mode execution of main."""
        import app  # pylint: disable=import-outside-toplevel
        app.main()

        mock_app_run.assert_called_once_with(debug=False, port=8050)


class TestAppRouting:
    """Tests for page routing and display."""

    @patch('app.strategy_statistics_layout')
    @patch('app.strategy_chart_layout')
    def test_display_page_stats(self, mock_chart_layout, mock_stats_layout):
        """Test displaying the statistics page layout."""
        mock_stats_layout.return_value = "Stats Layout"
        mock_chart_layout.return_value = "Chart Layout"

        # Test routing to /stats
        result = display_page('/stats')
        assert result == "Stats Layout"

    @patch('app.strategy_statistics_layout')
    @patch('app.strategy_chart_layout')
    def test_display_page_chart(self, mock_chart_layout, mock_stats_layout):
        """Test displaying the chart page layout as default."""
        mock_stats_layout.return_value = "Stats Layout"
        mock_chart_layout.return_value = "Chart Layout"

        # Test routing to / (or any other path)
        result = display_page('/')
        assert result == "Chart Layout"

        result = display_page('/unknown')
        assert result == "Chart Layout"


    @patch('app.stats_manager')
    @patch('app.run_analysis_for_ticker')
    @patch('app.get_date_ranges')
    def test_run_batch_mode_deduplication(
        self, mock_get_date_ranges, mock_run_analysis, mock_stats_manager
    ):
        """Test deduplication of tickers in batch mode."""
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
