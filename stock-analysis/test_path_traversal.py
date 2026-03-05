from utils import StockDataCache
import os

def test_ticker_sanitization():
    cache = StockDataCache(data_dir="test_data")

    # Valid tickers
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
