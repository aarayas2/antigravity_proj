import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import StockDataCache

class TestStockDataCacheCoverage(unittest.TestCase):
    def setUp(self):
        self.cache = StockDataCache(data_dir='test_data')
        self.ticker = "AAPL"

    def test_get_file_path_path_traversal(self):
        # Trigger path traversal exception by mocking os.path.abspath to return something outside
        # the expected data directory.
        # Since the _get_file_path uses real `os.path.abspath`, it's hard to trigger path traversal
        # using standard string manipulations since `os.path.basename` strips off the slashes.
        # So we mock os.path.basename to allow a traversal string like '../escaped' to pass.
        # Also mock re.sub to not strip the dots and slashes we just added
        with patch('os.path.basename') as mock_basename:
            with patch('re.sub') as mock_re_sub:
                mock_basename.return_value = '../escaped'
                mock_re_sub.return_value = '../escaped'
                with self.assertRaises(ValueError):
                    self.cache._get_file_path("dummy")

    @patch('os.path.exists')
    @patch('pandas.read_json')
    @patch('pandas.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_hit_all_data_available(self, mock_download, mock_to_json, mock_read_json, mock_exists):
        mock_exists.return_value = True

        # Setup cached data covering 2023-01-01 to 2023-01-10
        start_date = datetime.date(2023, 1, 1)
        end_date = datetime.date(2023, 1, 10)
        cached_index = pd.date_range(start_date, end_date)
        cached_df = pd.DataFrame({'Close': range(len(cached_index))}, index=cached_index)
        mock_read_json.return_value = cached_df

        # Request a sub-range (e.g. 2023-01-03 to 2023-01-05)
        req_start = datetime.date(2023, 1, 3)
        req_end = datetime.date(2023, 1, 5)
        result = self.cache.get_data(self.ticker, req_start, req_end)

        # Should not need to download or update cache
        mock_download.assert_not_called()
        mock_to_json.assert_not_called()
        self.assertEqual(len(result), 3)

    @patch('os.path.exists')
    @patch('pandas.read_json')
    @patch('pandas.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_hit_older_data_needed(self, mock_download, mock_to_json, mock_read_json, mock_exists):
        mock_exists.return_value = True

        # Setup cached data covering 2023-01-05 to 2023-01-10
        cached_start = datetime.date(2023, 1, 5)
        cached_end = datetime.date(2023, 1, 10)
        cached_index = pd.date_range(cached_start, cached_end)
        cached_df = pd.DataFrame({'Close': range(len(cached_index))}, index=cached_index)
        mock_read_json.return_value = cached_df

        # Setup downloaded older data (2023-01-01 to 2023-01-04)
        older_start = datetime.date(2023, 1, 1)
        older_end = datetime.date(2023, 1, 4)
        older_index = pd.date_range(older_start, older_end)
        older_df = pd.DataFrame({'Close': range(len(older_index))}, index=older_index)
        mock_download.return_value = older_df

        # Request data from 2023-01-01 to 2023-01-10
        req_start = datetime.date(2023, 1, 1)
        req_end = datetime.date(2023, 1, 10)

        result = self.cache.get_data(self.ticker, req_start, req_end)

        mock_download.assert_called_once()
        mock_to_json.assert_called_once()
        self.assertEqual(len(result), 10)

    @patch('os.path.exists')
    @patch('pandas.read_json')
    @patch('pandas.DataFrame.to_json')
    @patch('utils.StockDataCache._download_from_yf')
    def test_get_data_cache_hit_newer_data_needed(self, mock_download, mock_to_json, mock_read_json, mock_exists):
        mock_exists.return_value = True

        # Setup cached data covering 2023-01-01 to 2023-01-05
        cached_start = datetime.date(2023, 1, 1)
        cached_end = datetime.date(2023, 1, 5)
        cached_index = pd.date_range(cached_start, cached_end)
        cached_df = pd.DataFrame({'Close': range(len(cached_index))}, index=cached_index)
        mock_read_json.return_value = cached_df

        # Setup downloaded newer data (2023-01-06 to 2023-01-10)
        newer_start = datetime.date(2023, 1, 6)
        newer_end = datetime.date(2023, 1, 10)
        newer_index = pd.date_range(newer_start, newer_end)
        newer_df = pd.DataFrame({'Close': range(len(newer_index))}, index=newer_index)
        mock_download.return_value = newer_df

        # Request data from 2023-01-01 to 2023-01-10
        req_start = datetime.date(2023, 1, 1)
        req_end = datetime.date(2023, 1, 10)

        result = self.cache.get_data(self.ticker, req_start, req_end)

        mock_download.assert_called_once()
        mock_to_json.assert_called_once()
        self.assertEqual(len(result), 10)

    @patch('os.path.exists')
    @patch('pandas.read_json')
    @patch('utils.StockDataCache._download_and_save_full')
    def test_get_data_cache_hit_empty_cache(self, mock_download_full, mock_read_json, mock_exists):
        mock_exists.return_value = True

        # Cache file exists but is empty
        mock_read_json.return_value = pd.DataFrame()

        # Setup downloaded full data
        req_start = datetime.date(2023, 1, 1)
        req_end = datetime.date(2023, 1, 5)
        full_index = pd.date_range(req_start, req_end)
        full_df = pd.DataFrame({'Close': range(len(full_index))}, index=full_index)
        mock_download_full.return_value = full_df

        result = self.cache.get_data(self.ticker, req_start, req_end)

        mock_download_full.assert_called_once()
        self.assertEqual(len(result), 5)

    @patch('os.path.exists')
    @patch('pandas.read_json')
    @patch('utils.StockDataCache._download_and_save_full')
    def test_get_data_cache_exception_handling(self, mock_download_full, mock_read_json, mock_exists):
        mock_exists.return_value = True

        # Raise exception during read
        mock_read_json.side_effect = Exception("Corrupt cache")

        req_start = datetime.date(2023, 1, 1)
        req_end = datetime.date(2023, 1, 5)
        full_index = pd.date_range(req_start, req_end)
        full_df = pd.DataFrame({'Close': range(len(full_index))}, index=full_index)
        mock_download_full.return_value = full_df

        result = self.cache.get_data(self.ticker, req_start, req_end)

        mock_download_full.assert_called_once()
        self.assertEqual(len(result), 5)

if __name__ == '__main__':
    unittest.main()
