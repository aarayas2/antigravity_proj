import time
import sys
import contextlib
import io
import os
import datetime

sys.path.append(os.path.abspath('.'))
import app
from unittest.mock import patch

# Mock to bypass actual downloading
@patch('app.run_analysis_for_ticker')
@patch('app.stats_manager.save_stats_batch')
def test_perf(mock_save_batch, mock_run):
    mock_run.return_value = {
        "metrics": {"Strategy1": {"Win Rate": "50%"}},
        "sections": [],
        "buy_signals": ["Strategy1"]
    }

    tickers = ";".join([f"TICK{i}" for i in range(100000)])

    start_time = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        app.run_batch_mode(tickers)
    end_time = time.time()

    print(f"Time taken: {end_time - start_time:.4f} seconds")

if __name__ == '__main__':
    test_perf()
