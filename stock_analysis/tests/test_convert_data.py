
"""
Unit tests for the convert_data module.
"""

import unittest
from unittest.mock import patch, mock_open

from convert_data import migrate

class TestConvertData(unittest.TestCase):
    """Test suite for the migrate function in convert_data.py."""

    @patch('os.path.exists')
    @patch('builtins.print')
    def test_migrate_file_not_found(self, mock_print, mock_exists):
        """Test migrate function when the file is not found."""
        mock_exists.return_value = False
        migrate('non_existent.json')
        mock_print.assert_called_with("Stats file not found at non_existent.json")

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='[]')
    @patch('json.dump')
    def test_migrate_empty_data(self, mock_json_dump, mock_file, mock_exists):
        """Test migrate function with empty data."""
        mock_exists.return_value = True
        migrate('stats.json')
        mock_json_dump.assert_called_once_with([], mock_file(), indent=2)

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('json.dump')
    def test_migrate_successful_conversion(
        self, mock_json_dump, mock_json_load, _mock_file, mock_exists
    ):
        """Test migrate function with successful conversion of various data scenarios."""
        mock_exists.return_value = True

        # Input data with various scenarios
        input_data = [
            {
                "AAPL": {
                    "date-begin": "2023-01-01",
                    "date-end": "2023-12-31",
                    "SMA": {
                        "Total Return": "15.5%",
                        "Average Return": "1.2%",
                        "Win Rate": "60.0%",
                        "Other Metric": "Value"
                    },
                    "RSI": {
                        "Total Return": 0.1234,  # Already float
                        "Average Return": "invalid", # Invalid string
                        "Win Rate": "50%"
                    }
                }
            }
        ]
        mock_json_load.return_value = input_data

        migrate('stats.json')

        # Capture the data passed to json.dump
        args, _ = mock_json_dump.call_args
        dumped_data = args[0]

        # Verify conversions
        aapl = dumped_data[0]["AAPL"]
        self.assertEqual(aapl["SMA"]["Total Return"], 0.155)
        self.assertEqual(aapl["SMA"]["Average Return"], 0.012)
        self.assertEqual(aapl["SMA"]["Win Rate"], 0.6)
        self.assertEqual(aapl["SMA"]["Other Metric"], "Value")

        self.assertEqual(aapl["RSI"]["Total Return"], 0.1234)
        self.assertEqual(aapl["RSI"]["Average Return"], 0.0)
        self.assertEqual(aapl["RSI"]["Win Rate"], 0.5)

        # Verify date keys were ignored
        self.assertEqual(aapl["date-begin"], "2023-01-01")

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_migrate_writes_to_file(self, mock_file, mock_exists):
        """Test migrate function properly writes converted data back to the file."""
        mock_exists.return_value = True

        # We need to mock json.load because mock_open's read_data doesn't automatically
        # feed json.load in some versions/setups if not careful. Actually, migrate calls
        # json.load(f). mock_open() returns a file handle.
        # Let's just use the real json.load and mock_open

        with patch('json.load') as mock_load:
            mock_load.return_value = [{"TICK": {"Strat": {"Total Return": "100%"}}}]
            with patch('json.dump') as mock_dump:
                migrate('stats.json')
                mock_dump.assert_called_once()
                # Check that it was opened for writing at the end
                mock_file.assert_any_call('stats.json', 'w', encoding='utf-8')

    def test_main_execution_coverage(self):
        """Test the main execution block coverage directly."""
        import runpy
        import convert_data
        
        script_path = convert_data.__file__
        
        # Test default arg
        with patch('sys.argv', ['convert_data.py']):
            with patch('os.path.exists', return_value=False):
                with patch('builtins.print') as mock_print:
                    runpy.run_path(script_path, run_name='__main__')
                    mock_print.assert_called_with("Stats file not found at stock_analysis/data/stats.json")
                    
        # Test custom arg
        with patch('sys.argv', ['convert_data.py', 'custom_stats.json']):
            with patch('os.path.exists', return_value=False):
                with patch('builtins.print') as mock_print:
                    runpy.run_path(script_path, run_name='__main__')
                    mock_print.assert_called_with("Stats file not found at custom_stats.json")


    @patch('os.path.exists')
    def test_migrate_integration_with_mock_open(self, mock_exists):
        """Test the full migrate function using mock_open with raw JSON strings."""
        import json
        mock_exists.return_value = True
        
        input_json = json.dumps([
            {
                "AAPL": {
                    "date-begin": "2023-01-01",
                    "date-end": "2023-12-31",
                    "SMA": {
                        "Total Return": "15.5%",
                        "Average Return": "1.2%",
                        "Win Rate": "60.0%",
                        "Other Metric": "Value"
                    },
                    "RSI": {
                        "Total Return": 0.1234,
                        "Average Return": "invalid",
                        "Win Rate": "50%"
                    }
                }
            }
        ])
        
        m = mock_open(read_data=input_json)
        with patch('builtins.open', m):
            migrate('stats.json')
            
        # Get all write calls
        handle = m()
        write_calls = handle.write.call_args_list
        written_content = "".join(call[0][0] for call in write_calls)
        
        # Parse the output
        output_data = json.loads(written_content)
        
        # Verify
        aapl = output_data[0]["AAPL"]
        self.assertEqual(aapl["SMA"]["Total Return"], 0.155)
        self.assertEqual(aapl["SMA"]["Average Return"], 0.012)
        self.assertEqual(aapl["SMA"]["Win Rate"], 0.6)
        self.assertEqual(aapl["SMA"]["Other Metric"], "Value")
        
        self.assertEqual(aapl["RSI"]["Total Return"], 0.1234)
        self.assertEqual(aapl["RSI"]["Average Return"], 0.0)
        self.assertEqual(aapl["RSI"]["Win Rate"], 0.5)
        
        self.assertEqual(aapl["date-begin"], "2023-01-01")

if __name__ == '__main__':
    unittest.main()
