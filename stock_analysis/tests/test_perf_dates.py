"""
Performance test for batch analysis.
"""
import contextlib
import io
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import app  # pylint: disable=wrong-import-position,import-error

# Mock to bypass actual downloading
@patch(
    'app.concurrent.futures.ProcessPoolExecutor',
    new=ThreadPoolExecutor
)
@patch('app.run_analysis_for_ticker')
@patch('app.stats_manager.save_stats_batch')
def test_perf(mock_save_batch, mock_run):  # pylint: disable=unused-argument
    """Test performance of batch mode analysis with mocks."""
    mock_run.return_value = {
        "metrics": {"Strategy1": {"Win Rate": "50%"}},
        "sections": [],
        "buy_signals": ["Strategy1"]
    }

    tickers = ";".join([f"TICK{i}" for i in range(100000)])

    start_time = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        app.run_batch_mode(tickers)  # pylint: disable=no-member
    end_time = time.time()

    print(f"Time taken: {end_time - start_time:.4f} seconds")

if __name__ == '__main__':
    test_perf()  # pylint: disable=no-value-for-parameter
