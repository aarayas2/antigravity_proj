"""
Tests for path traversal vulnerabilities.
"""

import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import StockDataCache  # pylint: disable=import-error

def test_ticker_sanitization():
    """Test that tickers are properly sanitized to prevent path traversal."""
    cache = StockDataCache(data_dir="test_data")

    # Valid tickers
    # pylint: disable=protected-access
    assert "AAPL" in cache._get_file_path("AAPL")
    assert "BRK-B" in cache._get_file_path("BRK-B")
    assert "^GSPC" in cache._get_file_path("^GSPC")
    assert "TSLA=X" in cache._get_file_path("TSLA=X")
    assert "T.TO" in cache._get_file_path("T.TO")

    # Path traversal attempts
    path1 = os.path.basename(cache._get_file_path("../../../etc/passwd"))
    assert path1 == "passwd.json"

    path2 = os.path.basename(cache._get_file_path("..\\..\\windows\\system32"))
    assert path2 == "system32.json"

    print("All tests passed!")

if __name__ == "__main__":
    test_ticker_sanitization()
