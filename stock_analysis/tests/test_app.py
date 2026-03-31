"""
Unit tests for the main application module (app.py).
"""

import sys
import os
import datetime
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pylint: disable=wrong-import-position,import-error
from app import run_batch_mode

class TestApp:
    """Tests for the core application logic like batch mode."""

    executor_patcher = None

    def setup_method(self):
        """Setup method for tests."""
        # Patch ProcessPoolExecutor to use ThreadPoolExecutor so that MagicMock objects
        # can be passed as functions without pickle errors during tests.
        self.executor_patcher = patch(
            'app.concurrent.futures.ProcessPoolExecutor',
            new=__import__('concurrent.futures').futures.ThreadPoolExecutor
        )
        self.executor_patcher.start()

    def teardown_method(self):
        """Teardown method for tests."""
        self.executor_patcher.stop()

    @patch('app.get_date_ranges')
    def test_run_batch_mode_no_valid_tickers(self, mock_get_date_ranges):
        """Test batch mode when no valid tickers are provided."""
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
        """Test successful execution of batch mode for multiple valid tickers."""
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

        assert set(result["strat1"]) == {"AAPL"}
        assert set(result["strat2"]) == {"AAPL", "MSFT"}

        mock_run_analysis.assert_any_call("AAPL", min_date, max_date, is_batch_mode=True)
        mock_run_analysis.assert_any_call("MSFT", min_date, max_date, is_batch_mode=True)
        assert mock_run_analysis.call_count == 2

        mock_stats_manager.save_stats_batch.assert_called_once()
        saved_batch = mock_stats_manager.save_stats_batch.call_args[0][0]
        assert len(saved_batch) == 2
        # Sort saved_batch to ensure consistent order
        saved_batch = sorted(saved_batch, key=lambda x: x["ticker"])

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
    def test_run_batch_mode_partial_failure(
        self, mock_get_date_ranges, mock_run_analysis, mock_stats_manager
    ):
        """Test batch mode execution when analysis partially fails."""
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


class TestAppMain:
    """Tests for the main application entry point."""

    executor_patcher = None

    def setup_method(self):
        """Setup method for tests."""
        self.executor_patcher = patch(
            'app.concurrent.futures.ProcessPoolExecutor',
            new=__import__('concurrent.futures').futures.ThreadPoolExecutor
        )
        self.executor_patcher.start()

    def teardown_method(self):
        """Teardown method for tests."""
        self.executor_patcher.stop()

    @patch('app.get_date_ranges')
    @patch('app.run_analysis_for_ticker')
    @patch('app.stats_manager')
    @patch('app.app.run')
    @patch('sys.argv', ['app.py', '--ticker', 'AAPL'])
    def test_main_batch_mode_execution(
        self, mock_app_run, mock_stats_manager, mock_run_analysis, mock_get_date_ranges
    ):
        """Test that main executes batch mode correctly when args are provided."""
        # This tests that running `main()` with `--ticker AAPL` properly calls into `run_batch_mode`
        # and executes its logic, without mocking `run_batch_mode` itself.
        # pylint: disable=import-outside-toplevel
        import app

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
        """Test that main starts the server when no args are provided."""
        # pylint: disable=import-outside-toplevel
        import app
        app.main()

        mock_app_run.assert_called_once_with(debug=False, port=8050)


class TestAppRouting:
    """Tests for Dash routing logic."""

    executor_patcher = None

    def setup_method(self):
        """Setup method for tests."""
        self.executor_patcher = patch(
            'app.concurrent.futures.ProcessPoolExecutor',
            new=__import__('concurrent.futures').futures.ThreadPoolExecutor
        )
        self.executor_patcher.start()

    def teardown_method(self):
        """Teardown method for tests."""
        self.executor_patcher.stop()

    @patch('app.strategy_statistics_layout')
    @patch('app.strategy_chart_layout')
    def test_display_page_stats(self, mock_chart_layout, mock_stats_layout):
        """Test routing to the statistics page."""
        # pylint: disable=import-outside-toplevel
        from app import display_page

        mock_stats_layout.return_value = "Stats Layout"
        mock_chart_layout.return_value = "Chart Layout"

        # Test routing to /stats
        result = display_page('/stats')
        assert result == "Stats Layout"

    @patch('app.strategy_statistics_layout')
    @patch('app.strategy_chart_layout')
    def test_display_page_chart(self, mock_chart_layout, mock_stats_layout):
        """Test routing to the chart page or unknown paths."""
        # pylint: disable=import-outside-toplevel
        from app import display_page

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
        """Test that batch mode deduplicates duplicate tickers."""
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
